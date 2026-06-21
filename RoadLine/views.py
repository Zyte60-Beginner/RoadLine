# views.py
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QFrame, QGridLayout, QTextEdit, QPushButton,
                             QDialog, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, QUrl, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWebEngineWidgets import QWebEngineView
import bluetooth


# ---------------------------------------------------------------------------
# BaseView
# ---------------------------------------------------------------------------

class BaseView(QWidget):
    def __init__(self, title):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.title_label = QLabel(title)
        self.title_label.setProperty("class", "SectionTitle")
        self.layout.addWidget(self.title_label)


# ---------------------------------------------------------------------------
# MonitoringView
# ---------------------------------------------------------------------------

class MonitoringView(BaseView):
    # Sinal emitido pela view para pedir desconexão ao worker (thread-safe)
    _disconnect_signal = pyqtSignal()

    def __init__(self):
        super().__init__("Monitoramento da Missão")

        grid = QGridLayout()
        grid.setSpacing(20)

        self.lbl_status  = self.create_card(grid, 0, 0, "Dispositivo",          "Não conectado")
        self.lbl_battery = self.create_card(grid, 0, 1, "Bateria",               "--")
        self.lbl_speed   = self.create_card(grid, 0, 2, "Velocidade",            "--")
        self.lbl_ink     = self.create_card(grid, 1, 0, "Nível de Tinta",        "--")
        self.lbl_dist    = self.create_card(grid, 1, 1, "Distância Percorrida",  "--")
        self.lbl_time    = self.create_card(grid, 1, 2, "Tempo de Operação",     "--")

        self.layout.addLayout(grid)
        self.layout.addStretch()

        # Estado interno
        self._active_worker: bluetooth.ConnectWorker | None = None
        self._connect_thread: QThread | None = None
        self._elapsed_seconds = 0

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_timer_tick)

    # ------------------------------------------------------------------
    # Criação dos cards de monitoramento
    # ------------------------------------------------------------------

    def create_card(self, layout, row, col, title, initial_value):
        frame = QFrame()
        frame.setProperty("class", "Card")
        frame.setMinimumSize(200, 130)
        vbox = QVBoxLayout(frame)

        lbl_title = QLabel(title)
        lbl_title.setProperty("class", "MonitorLabel")
        lbl_val = QLabel(initial_value)
        lbl_val.setProperty("class", "MonitorValue")
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)

        vbox.addWidget(lbl_title, alignment=Qt.AlignmentFlag.AlignTop)
        vbox.addWidget(lbl_val,   alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(frame, row, col)
        return lbl_val

    # ------------------------------------------------------------------
    # API pública chamada pelo dashboard
    # ------------------------------------------------------------------

    def connect_device(self, device_name: str, device_id: str):
        """
        Recebe o nome e o ID do dispositivo selecionado.
        Cria o ConnectWorker e a QThread, move o worker para a thread,
        e dispara a conexão real via sinal.

        IMPORTANTE: O worker é criado AQUI (não no dialog), garantindo
        que seu ciclo de vida seja controlado pela MonitoringView,
        que tem lifetime igual ao da janela principal.
        """
        # Garante limpeza de sessão anterior
        self._cleanup_thread()

        self._active_worker = bluetooth.ConnectWorker()
        self._connect_thread = QThread(self)

        self._active_worker.moveToThread(self._connect_thread)

        # Conecta sinais de saída do worker → slots da UI
        self._active_worker.connection_status.connect(self._on_connection_status)
        self._active_worker.battery_updated.connect(self.lbl_battery.setText)
        self._active_worker.rssi_updated.connect(self._on_rssi_updated)

        # Conecta sinal interno de disconnect → slot do worker
        self._disconnect_signal.connect(self._active_worker.disconnect_requested)

        # Quando a thread iniciar, dispara o loop asyncio do worker
        self._connect_thread.started.connect(self._active_worker.run)

        # Inicia thread → run() bloqueia a thread com loop.run_forever()
        self._connect_thread.start()

        # Atualiza UI com nome pendente
        self.lbl_status.setText(f"Conectando a {device_name}…")
        self.lbl_status.setStyleSheet("color: #F0A500; font-size: 18px; font-weight: bold;")

        # Agenda a conexão real assim que o loop estiver rodando
        # Pequeno delay para garantir que run_forever() já iniciou
        QTimer.singleShot(200, lambda: self._active_worker.request_connect(device_id))

    def disconnect_device(self):
        """
        Solicita desconexão de forma thread-safe via sinal Qt.
        NUNCA chama run_disconnect() diretamente da UI thread.
        """
        self._clock_timer.stop()

        if self._active_worker:
            # Emite sinal → recebido pelo worker na sua própria thread
            self._disconnect_signal.emit()
            # Aguarda o worker confirmar via connection_status(False, ...)
            # A limpeza visual é feita em _on_connection_status

    # ------------------------------------------------------------------
    # Slots internos
    # ------------------------------------------------------------------

    def _on_connection_status(self, connected: bool, message: str):
        if connected:
            # Extrai o nome do dispositivo da mensagem de status se disponível
            self.lbl_status.setStyleSheet(
                "color: #4DB6AC; font-size: 24px; font-weight: bold;"
            )
            self._elapsed_seconds = 0
            self._clock_timer.start(1000)
        else:
            # Desconectado ou erro
            display_text = "Não conectado" if message == "Desconectado" else f"Erro: {message}"
            self.lbl_status.setText(display_text)
            self.lbl_status.setStyleSheet("font-size: 24px; font-weight: bold;")
            self.lbl_battery.setText("--")
            self.lbl_time.setText("--")
            self._clock_timer.stop()

            if message == "Desconectado":
                self._cleanup_thread()

    def _on_rssi_updated(self, rssi: str):
        # RSSI pode ser exibido em um card futuro; por ora sem campo dedicado
        pass

    def _update_timer_tick(self):
        self._elapsed_seconds += 1
        h = self._elapsed_seconds // 3600
        m = (self._elapsed_seconds % 3600) // 60
        s = self._elapsed_seconds % 60
        self.lbl_time.setText(f"{h:02d}:{m:02d}:{s:02d}")

    def _cleanup_thread(self):
        """Encerra o loop asyncio e a QThread de forma limpa."""
        if self._active_worker:
            self._active_worker.stop_loop()
            self._active_worker = None

        if self._connect_thread:
            self._connect_thread.quit()
            self._connect_thread.wait(3000)  # aguarda até 3s
            self._connect_thread = None

    # Garante limpeza ao fechar a janela
    def closeEvent(self, event):
        self._cleanup_thread()
        super().closeEvent(event)


# ---------------------------------------------------------------------------
# MappingView
# ---------------------------------------------------------------------------

class MappingView(BaseView):
    def __init__(self):
        super().__init__("Navegação e Rotas")
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl("https://www.openstreetmap.org/#map=13/-23.5505/-46.6333"))

        frame = QFrame()
        frame.setProperty("class", "Card")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(5, 5, 5, 5)
        frame_layout.addWidget(self.browser)
        self.layout.addWidget(frame)


# ---------------------------------------------------------------------------
# LogsView
# ---------------------------------------------------------------------------

class LogsView(BaseView):
    def __init__(self):
        super().__init__("Logs do Sistema")
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet(
            "background-color: #1E1E1E; color: #00FF66; "
            "font-family: 'Consolas', monospace; border-radius: 10px; padding: 10px;"
        )
        self.layout.addWidget(self.log_box)
        self.log_box.append("[SISTEMA] Subsistema de barramento Bluetooth operacional.")


# ---------------------------------------------------------------------------
# SettingsView
# ---------------------------------------------------------------------------

class SettingsView(BaseView):
    def __init__(self, toggle_theme_callback, current_theme_state, pair_callback):
        super().__init__("Configurações Gerais")

        lbl_info = QLabel(
            "Defina as diretrizes visuais do painel operativo e calibração de malha fechada."
        )
        lbl_info.setProperty("class", "NormalText")
        self.layout.addWidget(lbl_info)

        initial_text = "Tema: Escuro" if current_theme_state == "DARK" else "Tema: Claro"
        self.btn_theme = QPushButton(initial_text)
        self.btn_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme.setStyleSheet(
            "background-color: #333333; color: white; border: 1px solid #555;"
            "padding: 10px 20px; border-radius: 6px; font-weight: bold; margin-top: 20px;"
        )
        self.btn_theme.clicked.connect(toggle_theme_callback)
        self.layout.addWidget(self.btn_theme, alignment=Qt.AlignmentFlag.AlignLeft)

        self.btn_pair = QPushButton("+ Parear novo dispositivo")
        self.btn_pair.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pair.setStyleSheet(
            "background-color: #4DB6AC; color: white; border: none;"
            "padding: 10px 20px; border-radius: 6px; font-weight: bold; margin-top: 12px;"
        )
        self.btn_pair.clicked.connect(pair_callback)
        self.layout.addWidget(self.btn_pair, alignment=Qt.AlignmentFlag.AlignLeft)

        self.layout.addStretch()

        lbl_version = QLabel("v26.6.0-B     © 2026 Todos os direitos reservados")
        lbl_version.setProperty("class", "VersionText")
        self.layout.addWidget(lbl_version, alignment=Qt.AlignmentFlag.AlignLeft)

    def update_button_text(self, new_theme: str):
        self.btn_theme.setText("Tema: Escuro" if new_theme == "DARK" else "Tema: Claro")


# ---------------------------------------------------------------------------
# SupportView
# ---------------------------------------------------------------------------

class SupportView(BaseView):
    def __init__(self):
        super().__init__("Suporte e Documentação")
        info = QLabel(
            "<b>Canais de Comunicação e Suporte Técnico:</b><br><br>"
            "• joao.antonio.defranca.garcia@gmail.com<br>"
            "• g.sulacov@aluno.ifsp.edu.br"
        )
        info.setProperty("class", "NormalText")
        info.setStyleSheet("line-height: 150%; font-size: 15px;")
        self.layout.addWidget(info)
        self.layout.addStretch()


# ---------------------------------------------------------------------------
# CoffeeView
# ---------------------------------------------------------------------------

class CoffeeView(BaseView):
    def __init__(self):
        super().__init__("Buy us a Coffee")
        self.qr_label = QLabel()
        pixmap = QPixmap("assets/qr_code.png")
        if not pixmap.isNull():
            self.qr_label.setPixmap(
                pixmap.scaled(250, 250,
                              Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
            )
        else:
            self.qr_label.setText("[ QR Code Operativo Interno ]")
            self.qr_label.setProperty("class", "NormalText")
            self.qr_label.setStyleSheet("border: 2px dashed #555; padding: 60px;")
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_pix = QLabel("<b>Chave PIX:</b> 54382927870")
        lbl_pix.setProperty("class", "NormalText")
        lbl_pix.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.layout.addWidget(self.qr_label)
        self.layout.addWidget(lbl_pix)
        self.layout.addStretch()


# ---------------------------------------------------------------------------
# BluetoothPairDialog
# ---------------------------------------------------------------------------

class BluetoothPairDialog(QDialog):
    """
    Diálogo de descoberta e seleção de dispositivos Bluetooth.

    Responsabilidade: apenas SCAN e SELEÇÃO.
    A conexão real é iniciada pelo MonitoringView após o dialog fechar.

    Retorna via get_selected_device(): (nome: str, device_id: str)
    O ConnectWorker é criado pelo MonitoringView, não aqui.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Procurar Dispositivos Bluetooth")
        self.resize(400, 340)

        if parent:
            self.setStyleSheet(parent.styleSheet())

        dialog_layout = QVBoxLayout(self)

        self.lbl_status = QLabel("Consultando dispositivos pareados no Windows…")
        self.lbl_status.setProperty("class", "NormalText")
        dialog_layout.addWidget(self.lbl_status)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(
            "background-color: #1E1E1E; color: #FFFFFF; border-radius: 8px; padding: 5px;"
        )
        dialog_layout.addWidget(self.list_widget)

        # Botão de re-scan
        self.btn_rescan = QPushButton("↺  Buscar novamente")
        self.btn_rescan.setStyleSheet(
            "background-color: #555; color: white; padding: 6px; border-radius: 5px;"
        )
        self.btn_rescan.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_rescan.clicked.connect(self._start_scan)
        dialog_layout.addWidget(self.btn_rescan)

        action_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setStyleSheet(
            "background-color: #555; color: white; padding: 8px; border-radius: 5px;"
        )
        self.btn_cancel.clicked.connect(self._cancel)

        self.btn_confirm = QPushButton("Conectar")
        self.btn_confirm.setStyleSheet(
            "background-color: #4DB6AC; color: white; padding: 8px; "
            "border-radius: 5px; font-weight: bold;"
        )
        self.btn_confirm.setEnabled(False)
        self.btn_confirm.clicked.connect(self._confirm_selection)

        action_layout.addWidget(self.btn_cancel)
        action_layout.addWidget(self.btn_confirm)
        dialog_layout.addLayout(action_layout)

        # Mapa: nome → device_id
        self._device_map: dict[str, str] = {}

        # Thread e worker de scan
        self._scan_thread: QThread | None = None
        self._scan_worker: bluetooth.ScanWorker | None = None

        # Resultado selecionado
        self._selected_name: str | None = None
        self._selected_id: str | None = None

        # Habilita botão Conectar quando há seleção
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)

        self._start_scan()

    # ------------------------------------------------------------------
    # Scan
    # ------------------------------------------------------------------

    def _start_scan(self):
        # Limpa resultado anterior
        self.list_widget.clear()
        self._device_map.clear()
        self.btn_confirm.setEnabled(False)
        self.btn_rescan.setEnabled(False)
        self.lbl_status.setText("Consultando dispositivos pareados no Windows…")

        # Encerra thread anterior se ainda rodando
        if self._scan_thread and self._scan_thread.isRunning():
            self._scan_thread.quit()
            self._scan_thread.wait(2000)

        self._scan_worker = bluetooth.ScanWorker()
        self._scan_thread = QThread(self)

        self._scan_worker.moveToThread(self._scan_thread)

        self._scan_thread.started.connect(self._scan_worker.run_scan)
        self._scan_worker.device_discovered.connect(self._add_device)
        self._scan_worker.scan_finished.connect(self._on_scan_finished)
        self._scan_worker.scan_error.connect(self._on_scan_error)

        # Quando o worker terminar, encerra a thread automaticamente
        self._scan_worker.scan_finished.connect(self._scan_thread.quit)

        self._scan_thread.start()

    def _add_device(self, name: str, device_id: str):
        if device_id not in self._device_map.values():
            # Evita nomes duplicados adicionando sufixo se necessário
            display_name = name
            counter = 1
            while display_name in self._device_map:
                display_name = f"{name} ({counter})"
                counter += 1
            self._device_map[display_name] = device_id
            self.list_widget.addItem(QListWidgetItem(display_name))

    def _on_scan_finished(self):
        count = self.list_widget.count()
        if count == 0:
            self.lbl_status.setText(
                "Nenhum dispositivo pareado encontrado. "
                "Certifique-se de que o dispositivo está pareado no Windows."
            )
        else:
            self.lbl_status.setText(
                f"{count} dispositivo(s) encontrado(s). Selecione e clique em Conectar."
            )
        self.btn_rescan.setEnabled(True)

    def _on_scan_error(self, message: str):
        self.lbl_status.setText(f"Erro: {message}")
        self.btn_rescan.setEnabled(True)

    # ------------------------------------------------------------------
    # Seleção e confirmação
    # ------------------------------------------------------------------

    def _on_selection_changed(self):
        self.btn_confirm.setEnabled(self.list_widget.currentItem() is not None)

    def _confirm_selection(self):
        item = self.list_widget.currentItem()
        if item:
            self._selected_name = item.text()
            self._selected_id = self._device_map.get(self._selected_name)
            self.accept()

    def _cancel(self):
        if self._scan_thread and self._scan_thread.isRunning():
            self._scan_thread.quit()
            self._scan_thread.wait(1000)
        self.reject()

    def get_selected_device(self) -> tuple[str | None, str | None]:
        """
        Retorna (nome, device_id) do dispositivo selecionado.
        O ConnectWorker é criado pelo MonitoringView após receber esses valores.
        """
        return self._selected_name, self._selected_id
