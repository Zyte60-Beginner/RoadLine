# splash.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QPropertyAnimation
from PyQt6.QtGui import QPixmap

class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.resize(1024, 576) 
        self.center_on_screen()
        
        # Efeito original de Fade-In progressivo
        self.setWindowOpacity(0.0)
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(1200)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

        # Layout estruturado focado no alinhamento central geométrico
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.bg_label = QLabel(self)
        
        # Garante o alinhamento da imagem estritamente centralizado nos eixos X e Y
        self.bg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        pixmap = QPixmap("assets/splash_bg.jpg")
        if not pixmap.isNull():
            # Redimensiona a imagem preservando a proporção de forma suave dentro do contêiner centralizado
            self.bg_label.setPixmap(pixmap.scaled(
                self.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self.bg_label.setStyleSheet("background-color: #1a1a1a; color: white; font-size: 16px;")
            self.bg_label.setText("ROADLINE \n[Certifique-se de que splash_bg.jpg está na pasta assets]")
            self.bg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
        layout.addWidget(self.bg_label)

    def center_on_screen(self):
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())