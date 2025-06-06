#!/usr/bin/env python3
import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from glados_widget import GLaDOSWidget

def main():
    # Set Wayland-specific environment variables
    os.environ["QT_QPA_PLATFORM"] = "wayland"
    
    try:
        print("Starting application...")
        app = QApplication(sys.argv)
        print("Creating main window...")
        window = MainWindow()
        print("Showing window...")
        window.show()
        print("Entering main loop...")
        sys.exit(app.exec())
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GLaDOS Chatbot")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create GLaDOS 3D widget
        print("Creating GLaDOS widget...")
        self.glados_widget = GLaDOSWidget()
        self.glados_widget.setFixedSize(300, 300)
        
        # Add GLaDOS widget to the top right
        layout.addWidget(self.glados_widget, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        
        # Add some spacing
        layout.addStretch()

if __name__ == '__main__':
    main() 