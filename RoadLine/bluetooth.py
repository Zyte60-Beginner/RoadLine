# bluetooth.py
"""
Módulo de integração Bluetooth via WinRT.

Arquitetura de threads:
  - ScanWorker  → roda em QThread dedicada para descoberta, encerra sozinha ao terminar
  - ConnectWorker → roda em QThread dedicada, mantida viva durante toda a sessão
                    O loop asyncio interno é mantido girando via run_forever(),
                    permitindo que coroutines de monitoramento sejam agendadas com
                    asyncio.run_coroutine_threadsafe() de forma segura.

Todos os métodos que tocam hardware rodam DENTRO da thread dedicada via sinais Qt.
A UI NUNCA chama métodos do worker diretamente — apenas emite sinais.
"""

import re
import asyncio
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

import winrt.windows.devices.enumeration as devices_enum
import winrt.windows.devices.bluetooth as win_bt


def _extract_mac(device_id: str) -> str | None:
    """
    Extrai o endereço MAC do device_id WinRT.

    O Windows embute o MAC no ID em dois formatos:
      Clássico: "Bluetooth#Bluetooth00:00:00:00:00:00-AA:BB:CC:DD:EE:FF"
      BLE:      "BluetoothLE#BluetoothLE00:00:00:00:00:00-AA:BB:CC:DD:EE:FF"

    O MAC do dispositivo remoto é sempre a parte APÓS o hífen.
    Retorna o MAC em maiúsculas sem separadores: "AABBCCDDEEFF".
    Retorna None se nenhum padrão de MAC for encontrado.
    """
    # MAC do dispositivo remoto: após o hífen
    match = re.search(r'-([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})', device_id)
    if match:
        return match.group(1).upper().replace(":", "")
    # Fallback: qualquer MAC no ID
    match = re.search(r'([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})', device_id)
    if match:
        return match.group(1).upper().replace(":", "")
    return None


# ---------------------------------------------------------------------------
# Worker de Scan — descobre dispositivos BT pareados no Windows
# ---------------------------------------------------------------------------

class ScanWorker(QObject):
    """
    Responsabilidade única: varrer dispositivos e emitir sinais.
    Ciclo de vida curto: inicia, varre, emite scan_finished, para.
    """
    device_discovered = pyqtSignal(str, str)   # (nome, device_id)
    scan_finished     = pyqtSignal()
    scan_error        = pyqtSignal(str)

    @pyqtSlot()
    def run_scan(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_scan())
        except Exception as exc:
            self.scan_error.emit(f"Erro no scan: {exc}")
        finally:
            loop.close()
            self.scan_finished.emit()

    async def _async_scan(self):
        """
        Estratégia de três consultas ao barramento WinRT para cobrir todos os
        estados possíveis de dispositivos Bluetooth no Windows.

        DEDUPLICAÇÃO POR MAC:
        O mesmo dispositivo físico aparece com múltiplos IDs no Windows —
        um por perfil de serviço registrado (A2DP, HFP, AVRCP, BLE, etc.).
        Usar o ID completo como chave permite duplicatas. O endereço MAC é o
        único identificador estável e único por hardware: extraímos ele do ID
        via regex e usamos como chave de deduplicação primária.
        Fallback: se o ID não contiver MAC, usamos "NOME|ID_UPPER" como chave.
        """
        # Chave de deduplicação: MAC extraído do ID (único por hardware físico)
        seen_macs: set[str] = set()

        def should_emit(device_id: str, name: str) -> bool:
            """Retorna True se o dispositivo ainda não foi emitido."""
            mac = _extract_mac(device_id)
            key = mac if mac else f"{name.upper()}|{device_id.upper()}"
            if key in seen_macs:
                return False
            seen_macs.add(key)
            return True

        # --- Consulta 1: barramento completo do Windows (mais abrangente) ---
        # find_all_async() sem seletor lê o mesmo banco que as Configurações do
        # Windows usam. Filtramos manualmente por "BTH"/"BLUETOOTH" no ID.
        try:
            all_devices = await devices_enum.DeviceInformation.find_all_async()
            for device in all_devices:
                if not device.name:
                    continue
                dev_id = str(device.id)
                if "BTH" not in dev_id.upper() and "BLUETOOTH" not in dev_id.upper():
                    continue
                if should_emit(dev_id, device.name):
                    self.device_discovered.emit(device.name, dev_id)
        except Exception as exc:
            self.scan_error.emit(f"Erro na varredura geral: {exc}")

        # --- Consulta 2: BT Clássico pareado via seletor AQS correto ---
        # get_device_selector_from_pairing_state(True) consulta o registro de
        # pareamento, diferente de get_device_selector() que exige driver ativo.
        try:
            selector_classic = win_bt.BluetoothDevice.get_device_selector_from_pairing_state(True)
            classic_devices = await devices_enum.DeviceInformation.find_all_async(selector_classic)
            for device in classic_devices:
                dev_id = str(device.id)
                name = device.name or "Dispositivo desconhecido"
                if should_emit(dev_id, name):
                    self.device_discovered.emit(name, dev_id)
        except Exception as exc:
            self.scan_error.emit(f"Erro no scan BT clássico: {exc}")

        # --- Consulta 3: BLE pareado via seletor AQS correto ---
        try:
            selector_ble = win_bt.BluetoothLEDevice.get_device_selector_from_pairing_state(True)
            ble_devices = await devices_enum.DeviceInformation.find_all_async(selector_ble)
            for device in ble_devices:
                dev_id = str(device.id)
                name = device.name or "Dispositivo BLE desconhecido"
                if should_emit(dev_id, name):
                    self.device_discovered.emit(name, dev_id)
        except Exception as exc:
            self.scan_error.emit(f"Erro no scan BLE: {exc}")


# ---------------------------------------------------------------------------
# Worker de Conexão — mantido vivo durante toda a sessão conectada
# ---------------------------------------------------------------------------

class ConnectWorker(QObject):
    """
    Responsabilidade: conectar, monitorar e desconectar.
    Ciclo de vida longo: vive enquanto há uma sessão ativa.

    O loop asyncio interno roda em run_forever() dentro da QThread.
    Isso permite agendar novas coroutines (monitoramento) sem criar
    novos loops, resolvendo o problema do ensure_future com run_until_complete.

    Sinais de entrada (a UI emite → worker executa na thread correta):
      - disconnect_requested  → agenda desconexão segura

    Sinais de saída (worker emite → UI atualiza):
      - connection_status(bool, str)
      - battery_updated(str)
      - rssi_updated(str)
    """

    # Sinais de saída
    connection_status = pyqtSignal(bool, str)   # (conectado, mensagem)
    battery_updated   = pyqtSignal(str)
    rssi_updated      = pyqtSignal(str)

    # Sinal de entrada (UI → worker, thread-safe via Qt)
    disconnect_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._device_id: str | None = None
        self._keep_monitoring = False
        self._device_ref = None       # BluetoothDevice WinRT handle
        self._monitor_task = None

        # Conecta o sinal de disconnect ao slot interno
        self.disconnect_requested.connect(self._on_disconnect_requested)

    # ------------------------------------------------------------------
    # Método chamado pela QThread ao iniciar (via thread.started)
    # ------------------------------------------------------------------

    @pyqtSlot()
    def run(self):
        """
        Cria e inicia o loop asyncio em run_forever().
        A thread fica bloqueada aqui até loop.stop() ser chamado.
        """
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_forever()
        finally:
            self._loop.close()
            self._loop = None

    # ------------------------------------------------------------------
    # API pública — chamada da UI thread via pyqtSlot (thread-safe)
    # ------------------------------------------------------------------

    @pyqtSlot(str)
    def request_connect(self, device_id: str):
        """
        Agenda a coroutine de conexão no loop interno da thread.
        Chamado via signal da UI: connect_requested.emit(device_id)
        """
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._async_connect(device_id), self._loop
            )

    @pyqtSlot()
    def _on_disconnect_requested(self):
        """
        Slot que recebe o sinal disconnect_requested.
        Roda na thread do worker (graças ao moveToThread feito antes).
        Agenda a coroutine de desconexão no loop asyncio.
        """
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._async_disconnect(), self._loop
            )

    def stop_loop(self):
        """Encerra o loop asyncio e, consequentemente, a QThread."""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

    # ------------------------------------------------------------------
    # Coroutines internas — rodam dentro do loop da thread dedicada
    # ------------------------------------------------------------------

    async def _async_connect(self, device_id: str):
        self._device_id = device_id
        self._keep_monitoring = False

        try:
            # 1. Tenta instanciar como BT Clássico
            self._device_ref = await win_bt.BluetoothDevice.from_id_async(device_id)

            if self._device_ref:
                # 2. Tenta forçar canal RFCOMM para acordar o rádio.
                #    RFCOMM pode não estar disponível em todas as instalações
                #    do pacote winrt — isolamos em try/except para não crashar.
                try:
                    await self._device_ref.get_rfcomm_services_async()
                except Exception:
                    # RFCOMM indisponível neste ambiente: prossegue sem ele.
                    # O Windows pode já ter registrado a conexão só com from_id_async.
                    pass

                connected = (
                    self._device_ref.connection_status
                    == win_bt.BluetoothConnectionStatus.CONNECTED
                )

                if connected:
                    self.connection_status.emit(True, "Conectado")
                    self._keep_monitoring = True
                    self._monitor_task = asyncio.ensure_future(
                        self._monitor_loop(), loop=self._loop
                    )
                    return

            # 3. Tenta BLE como fallback (cobre fones modernos, controles, etc.)
            try:
                ble_ref = await win_bt.BluetoothLEDevice.from_id_async(device_id)
                if ble_ref:
                    try:
                        await ble_ref.get_gatt_services_async()
                    except Exception:
                        pass  # GATT pode falhar; verifica status mesmo assim

                    connected = (
                        ble_ref.connection_status
                        == win_bt.BluetoothConnectionStatus.CONNECTED
                    )
                    if connected:
                        self._device_ref = ble_ref
                        self.connection_status.emit(True, "Conectado")
                        self._keep_monitoring = True
                        self._monitor_task = asyncio.ensure_future(
                            self._monitor_loop(), loop=self._loop
                        )
                        return
            except Exception:
                pass

            # 4. Nenhuma tentativa resultou em conexão ativa
            self.connection_status.emit(
                False,
                "Dispositivo pareado, mas está desligado ou fora de alcance."
            )

        except Exception as exc:
            self.connection_status.emit(False, f"Erro de conexão: {exc}")

    async def _async_disconnect(self):
        self._keep_monitoring = False

        # Cancela a task de monitoramento se existir
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        self._monitor_task = None

        # Libera referência de hardware
        if self._device_ref:
            try:
                self._device_ref.close()
            except Exception:
                pass
            self._device_ref = None

        self._device_id = None
        self.connection_status.emit(False, "Desconectado")

    async def _monitor_loop(self):
        """
        Loop de monitoramento contínuo.
        Atualiza bateria e RSSI a cada 3 segundos.
        Encerra sozinho quando _keep_monitoring = False.
        """
        battery_key = "{78c34fc8-104a-4aca-9ea3-43c50f527435} 7"

        while self._keep_monitoring and self._device_id:
            # --- Bateria ---
            try:
                device_info = await devices_enum.DeviceInformation.create_from_id_async(
                    self._device_id,
                    [battery_key]
                )
                props = device_info.properties
                if props.has_key(battery_key):
                    val = props.lookup(battery_key)
                    self.battery_updated.emit(f"{int(val)}%" if val is not None else "--")
                else:
                    self.battery_updated.emit("--")
            except asyncio.CancelledError:
                raise  # deixa o cancel propagar
            except Exception:
                self.battery_updated.emit("--")

            # --- RSSI ---
            # O WinRT clássico não expõe RSSI diretamente via BluetoothDevice.
            # Emitimos "--" para manter o campo visível sem crash.
            # Futura integração com ESP32 pode enviar RSSI via canal de dados.
            self.rssi_updated.emit("--")

            await asyncio.sleep(3.0)