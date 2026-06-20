# main.py
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from splash import SplashScreen
from dashboard import MainWindow

class AppManager:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setStyle('Fusion')
        
        # Inicialização estruturada da SplashScreen Mockup
        self.splash = SplashScreen()
        self.splash.show()
        
        QTimer.singleShot(3500, self.start_main_window)

    def start_main_window(self):
        self.main_window = MainWindow()
        self.main_window.show()
        self.splash.close()

if __name__ == '__main__':
    manager = AppManager()
    sys.exit(manager.app.exec())