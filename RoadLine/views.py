# views.py
import random
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QGridLayout, QTextEdit, QPushButton)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QPixmap
from PyQt6.QtWebEngineWidgets import QWebEngineView

class BaseView(QWidget):
    def __init__(self, title):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(30, 30, 30, 30)
        self.title_label = QLabel(title)
        self.title_label.setProperty("class", "SectionTitle")
        self.layout.addWidget(self.title_label)

class MonitoringView(BaseView):
    def __init__(self):
        super().__init__("Monitoramento da Missão")
        
        grid = QGridLayout()
        grid.setSpacing(20)
        
        # Estado estrito de 'Sem Hardware Conectado' - Totalmente estático
        self.lbl_status = self.create_card(grid, 0, 0, "Status do Robô", "Não conectado")
        self.lbl_battery = self.create_card(grid, 0, 1, "Bateria", "--")
        self.lbl_speed = self.create_card(grid, 0, 2, "Velocidade", "--")
        self.lbl_ink = self.create_card(grid, 1, 0, "Nível de Tinta", "--")
        self.lbl_dist = self.create_card(grid, 1, 1, "Distância Percorrida", "--")
        self.lbl_time = self.create_card(grid, 1, 2, "Tempo de Operação", "--")
        
        self.layout.addLayout(grid)
        self.layout.addStretch()

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
        vbox.addWidget(lbl_val, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(frame, row, col)
        return lbl_val

class MappingView(BaseView):
    def __init__(self):
        super().__init__("Navegação e Rotas")
        
        # Inicializa o componente nativo do PyQt6 sem dependência de APIs complexas ou iframe
        self.browser = QWebEngineView()
        
        # URL direta e aberta do OpenStreetMap (Permite interação, zoom e movimentação livre)
        # Nota de arquitetura: Preparado para fácil substituição por rotas locais do GPS do robô
        self.browser.setUrl(QUrl("https://www.openstreetmap.org/#map=13/-23.5505/-46.6333"))
        
        frame = QFrame()
        frame.setProperty("class", "Card")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(5, 5, 5, 5)
        frame_layout.addWidget(self.browser)
        
        self.layout.addWidget(frame)

class LogsView(BaseView):
    def __init__(self):
        super().__init__("Logs do Sistema")
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("background-color: #1E1E1E; color: #00FF66; font-family: 'Consolas', monospace; border-radius: 10px; padding: 10px;")
        self.layout.addWidget(self.log_box)
        self.log_box.append("[SISTEMA] Aguardando inicialização do barramento serial com o hardware...")

class SettingsView(BaseView):
    def __init__(self, toggle_theme_callback, current_theme_state):
        super().__init__("Configurações Gerais")
        
        lbl_info = QLabel("Defina as diretrizes visuais do painel operativo e calibração de malha fechada.")
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
        
        self.layout.addStretch()
        
        lbl_version = QLabel("v26.5.0-B")
        lbl_version.setProperty("class", "VersionText")
        self.layout.addWidget(lbl_version, alignment=Qt.AlignmentFlag.AlignLeft)

    def update_button_text(self, new_theme):
        if new_theme == "DARK":
            self.btn_theme.setText("Tema: Escuro")
        else:
            self.btn_theme.setText("Tema: Claro")

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

class CoffeeView(BaseView):
    def __init__(self):
        super().__init__("Buy us a Coffee")
        self.qr_label = QLabel()
        pixmap = QPixmap("assets/qr_code.png")
        if not pixmap.isNull():
            self.qr_label.setPixmap(pixmap.scaled(250, 250, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
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