# dashboard.py
from PyQt6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QPushButton, QStackedWidget, QLabel, QFrame,
                             QButtonGroup, QDialog)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QIcon
from views import (MonitoringView, MappingView, LogsView,
                   SettingsView, SupportView, CoffeeView, BluetoothPairDialog)
import styles


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ROADLINE - Dashboard Operacional")
        self.resize(1150, 750)

        self.current_theme = "DARK"
        self.setStyleSheet(styles.DARK_THEME)

        self.is_connected = False
        self.connected_device_name = ""

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ================= SIDEBAR =================
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 30, 10, 30)
        sidebar_layout.setSpacing(5)

        logo_container = QWidget()
        logo_container.setStyleSheet("background: transparent; margin-bottom: 20px;")
        logo_layout = QHBoxLayout(logo_container)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(0)
        logo_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_road = QLabel("ROAD")
        lbl_road.setStyleSheet(
            "color: #F85A5A; font-size: 24px; font-weight: 900; font-style: italic; margin: 0; padding: 0;"
        )

        lbl_line = QLabel("LINE")
        lbl_line.setProperty("class", "LogoLine")
        lbl_line.setStyleSheet(
            "font-size: 24px; font-weight: 900; font-style: italic; margin: 0; padding: 0;"
        )

        logo_layout.addWidget(lbl_road)
        logo_layout.addWidget(lbl_line)
        sidebar_layout.addWidget(logo_container)

        self.menu_group = QButtonGroup(self)
        self.menu_group.setExclusive(True)

        sidebar_layout.addStretch()

        menus = [
            ("Monitoramento",   0, "monitor.png"),
            ("Mapeamento",      1, "map.png"),
            ("Logs",            2, "logs.png"),
            ("Configurações",   3, "settings.png"),
            ("Suporte",         4, "support.png"),
            ("Buy us a Coffee", 5, "coffee.png"),
        ]

        self.buttons = []
        for text, index, icon_name in menus:
            btn = QPushButton(f"  {text}")
            btn.setProperty("class", "MenuButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

            icon_pixmap = QPixmap(f"assets/{icon_name}")
            if not icon_pixmap.isNull():
                btn.setIcon(QIcon(icon_pixmap))
                btn.setIconSize(QSize(18, 18))

            btn.clicked.connect(lambda checked, idx=index: self.switch_page(idx))
            self.menu_group.addButton(btn)
            sidebar_layout.addWidget(btn)
            self.buttons.append(btn)

        self.buttons[0].setChecked(True)

        sidebar_layout.addStretch()

        user_container = QFrame()
        user_container.setStyleSheet("background: transparent; margin-left: 10px;")
        user_layout = QHBoxLayout(user_container)
        user_layout.setContentsMargins(0, 0, 0, 0)
        user_layout.setSpacing(10)

        avatar_lbl = QLabel()
        avatar_pix = QPixmap("assets/user_avatar.png")
        if not avatar_pix.isNull():
            avatar_lbl.setPixmap(
                avatar_pix.scaled(35, 35,
                                  Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
            )
        else:
            avatar_lbl.setStyleSheet(
                "background-color: #444; border-radius: 17px; "
                "min-width: 35px; max-width: 35px; min-height: 35px; max-height: 35px;"
            )

        user_info_lbl = QLabel("Zyte60\nAdministrador")
        user_info_lbl.setStyleSheet("font-size: 12px; font-weight: bold; line-height: 120%;")
        user_info_lbl.setProperty("class", "NormalText")

        user_layout.addWidget(avatar_lbl)
        user_layout.addWidget(user_info_lbl)
        user_layout.addStretch()

        sidebar_layout.addWidget(user_container)
        main_layout.addWidget(self.sidebar)

        # ================= ÁREA DE CONTEÚDO DINÂMICA =================
        self.content_area = QWidget()
        self.content_area.setObjectName("MainContent")
        content_layout = QVBoxLayout(self.content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.monitoring_view = MonitoringView()
        self.logs_view       = LogsView()
        self.settings_view   = SettingsView(
            self.toggle_theme,
            self.current_theme,
            self.handle_pairing_toggle_action,
        )

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.monitoring_view)
        self.stacked_widget.addWidget(MappingView())
        self.stacked_widget.addWidget(self.logs_view)
        self.stacked_widget.addWidget(self.settings_view)
        self.stacked_widget.addWidget(SupportView())
        self.stacked_widget.addWidget(CoffeeView())

        content_layout.addWidget(self.stacked_widget)

        # Painel de Comando Rápido Inferior
        bottom_actions = QHBoxLayout()
        bottom_actions.setContentsMargins(30, 0, 30, 30)
        bottom_actions.setSpacing(20)

        self.btn_quick_pair = QPushButton("+ Parear novo dispositivo")
        self.btn_quick_pair.setFixedHeight(50)
        self.btn_quick_pair.setProperty("class", "BottomActionBtn")
        self.btn_quick_pair.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_quick_pair.clicked.connect(self.handle_pairing_toggle_action)
        bottom_actions.addWidget(self.btn_quick_pair)

        for _ in range(2):
            empty_btn = QPushButton("")
            empty_btn.setFixedHeight(50)
            empty_btn.setProperty("class", "BottomActionBtn")
            bottom_actions.addWidget(empty_btn)

        content_layout.addLayout(bottom_actions)
        main_layout.addWidget(self.content_area)

        # Conecta o sinal de status de conexão do monitoring_view ao log
        self.monitoring_view._active_worker  # referência lazy; usamos sinal diferente
        # Escuta atualizações de status via slot dedicado
        self._wire_monitoring_log()

    # ------------------------------------------------------------------
    # Navegação
    # ------------------------------------------------------------------

    def switch_page(self, index: int):
        self.stacked_widget.setCurrentIndex(index)

    # ------------------------------------------------------------------
    # Tema
    # ------------------------------------------------------------------

    def toggle_theme(self):
        if self.current_theme == "DARK":
            self.setStyleSheet(styles.LIGHT_THEME)
            self.current_theme = "LIGHT"
        else:
            self.setStyleSheet(styles.DARK_THEME)
            self.current_theme = "DARK"
        self.settings_view.update_button_text(self.current_theme)

    # ------------------------------------------------------------------
    # Fluxo de pareamento / desconexão
    # ------------------------------------------------------------------

    def handle_pairing_toggle_action(self):
        """
        Gerencia o ciclo completo: abrir dialog → conectar → desconectar.
        """
        if self.is_connected:
            # --- DESCONECTAR ---
            self.is_connected = False
            self.connected_device_name = ""

            self.btn_quick_pair.setText("+ Parear novo dispositivo")
            self.settings_view.btn_pair.setText("+ Parear novo dispositivo")

            # Solicita desconexão thread-safe via MonitoringView
            self.monitoring_view.disconnect_device()
            self.logs_view.log_box.append(
                "[SISTEMA] Dispositivo desconectado. Memória de telemetria redefinida."
            )

        else:
            # --- PAREAR / CONECTAR ---
            dialog = BluetoothPairDialog(self)

            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Dialog retorna apenas nome e device_id — sem worker
                name, device_id = dialog.get_selected_device()

                if name and device_id:
                    self.is_connected = True
                    self.connected_device_name = name

                    self.btn_quick_pair.setText("Desparear dispositivo")
                    self.settings_view.btn_pair.setText("Desparear dispositivo")

                    # MonitoringView cria o ConnectWorker e inicia conexão real
                    self.monitoring_view.connect_device(name, device_id)

                    self.logs_view.log_box.append(
                        f"[SISTEMA] Iniciando conexão WinRT com: {name} (ID: {device_id})"
                    )

    def _wire_monitoring_log(self):
        """
        Conecta o sinal connection_status do futuro worker ao log.
        Como o worker é criado dinamicamente, usamos um slot no monitoring_view
        que re-emite eventos de conexão para podermos logar aqui.
        """
        # Aproveitamos o _on_connection_status já existente na MonitoringView;
        # para logar, interceptamos via monkey-patch mínimo sem alterar a view.
        original_status_handler = self.monitoring_view._on_connection_status

        def patched_status(connected: bool, message: str):
            original_status_handler(connected, message)
            if connected:
                self.logs_view.log_box.append(
                    f"[BT] Conectado com sucesso: {self.connected_device_name}"
                )
                # Atualiza o card de status com o nome real após confirmação
                self.monitoring_view.lbl_status.setText(self.connected_device_name)
            else:
                self.logs_view.log_box.append(f"[BT] Status: {message}")
                if not self.is_connected:
                    pass  # já foi tratado acima no disconnect
                else:
                    # Conexão falhou após tentativa
                    self.is_connected = False
                    self.connected_device_name = ""
                    self.btn_quick_pair.setText("+ Parear novo dispositivo")
                    self.settings_view.btn_pair.setText("+ Parear novo dispositivo")

        self.monitoring_view._on_connection_status = patched_status
