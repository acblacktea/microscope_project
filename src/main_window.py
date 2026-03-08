import sys
import os

# Add uvcham SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'uvchamsdk.20250428', 'python'))
import uvcham

from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QPixmap, QImage, QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QTextEdit, QMessageBox, QMenu,
    QSplitter, QFrame, QSizePolicy
)


class CameraWidget(QWidget):
    """Left panel: live microscope video feed."""
    evtCallback = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hcam = None
        self.imgWidth = 0
        self.imgHeight = 0
        self.pData = None
        self.frame = 0
        self.timer = QTimer(self)

        # Video display
        self.lbl_video = QLabel("No camera connected")
        self.lbl_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_video.setStyleSheet(
            "QLabel { background-color: #1a1a2e; color: #888; "
            "font-size: 16px; border: 1px solid #333; border-radius: 4px; }"
        )
        self.lbl_video.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Camera controls bar
        self.btn_open = QPushButton("Open Camera")
        self.btn_open.setFixedHeight(36)
        self.btn_open.clicked.connect(self.onBtnOpen)

        self.lbl_status = QLabel("Status: Disconnected")
        self.lbl_status.setStyleSheet("color: #888; font-size: 12px;")

        ctrl_layout = QHBoxLayout()
        ctrl_layout.addWidget(self.btn_open)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.lbl_status)

        layout = QVBoxLayout()
        layout.addWidget(self.lbl_video, 1)
        layout.addLayout(ctrl_layout)
        self.setLayout(layout)

        self.evtCallback.connect(self.onEvtCallback)
        self.timer.timeout.connect(self.onTimer)

    @staticmethod
    def cameraCallback(nEvent, ctx):
        """Callback from uvcham.dll internal thread, post to UI thread via signal."""
        ctx.evtCallback.emit(nEvent)

    def onEvtCallback(self, nEvent):
        if self.hcam is not None:
            if uvcham.UVCHAM_EVENT_IMAGE & nEvent != 0:
                self.onImageEvent()
            elif uvcham.UVCHAM_EVENT_ERROR & nEvent != 0:
                self.closeCamera()
                QMessageBox.warning(self, "Warning", "Camera error.")
            elif uvcham.UVCHAM_EVENT_DISCONNECT & nEvent != 0:
                self.closeCamera()
                QMessageBox.warning(self, "Warning", "Camera disconnected.")

    def onImageEvent(self):
        self.hcam.pull(self.pData)
        self.frame += 1
        image = QImage(self.pData, self.imgWidth, self.imgHeight, QImage.Format.Format_RGB888)
        scaled = image.scaled(
            self.lbl_video.width(), self.lbl_video.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation
        )
        self.lbl_video.setPixmap(QPixmap.fromImage(scaled))

    def onTimer(self):
        if self.hcam is not None:
            self.lbl_status.setText(f"Status: Running | Frames: {self.frame}")

    def openCamera(self, cam_id):
        self.hcam = uvcham.Uvcham.open(cam_id)
        if self.hcam:
            self.frame = 0
            self.hcam.put(uvcham.UVCHAM_FORMAT, 2)  # RGB888 for QImage

            res = self.hcam.get(uvcham.UVCHAM_RES)
            self.imgWidth = self.hcam.get(uvcham.UVCHAM_WIDTH | res)
            self.imgHeight = self.hcam.get(uvcham.UVCHAM_HEIGHT | res)
            self.pData = bytes(uvcham.TDIBWIDTHBYTES(self.imgWidth * 24) * self.imgHeight)

            try:
                self.hcam.start(None, self.cameraCallback, self)  # Pull Mode
            except uvcham.HRESULTException:
                self.closeCamera()
                QMessageBox.warning(self, "Warning", "Failed to start camera.")
            else:
                self.btn_open.setText("Close Camera")
                self.lbl_status.setText("Status: Running | Frames: 0")
                self.timer.start(1000)

    def onBtnOpen(self):
        if self.hcam is not None:
            self.closeCamera()
        else:
            arr = uvcham.Uvcham.enum()
            if len(arr) == 0:
                QMessageBox.warning(self, "Warning", "No camera found.")
            elif len(arr) == 1:
                self.openCamera(arr[0].id)
            else:
                menu = QMenu(self)
                for i, dev in enumerate(arr):
                    action = menu.addAction(dev.displayname)
                    action.setData(i)
                action = menu.exec(self.mapToGlobal(self.btn_open.pos()))
                if action:
                    self.openCamera(arr[action.data()].id)

    def closeCamera(self):
        if self.hcam:
            self.hcam.close()
        self.hcam = None
        self.pData = None
        self.btn_open.setText("Open Camera")
        self.lbl_status.setText("Status: Disconnected")
        self.lbl_video.clear()
        self.lbl_video.setText("No camera connected")
        self.timer.stop()

    def getCurrentFrame(self):
        """Return current frame as QImage, or None if no camera."""
        if self.hcam is not None and self.pData is not None:
            return QImage(self.pData, self.imgWidth, self.imgHeight, QImage.Format.Format_RGB888)
        return None


class AnalysisPanel(QWidget):
    """Right panel: AI analysis controls and results."""

    def __init__(self, camera_widget: CameraWidget, parent=None):
        super().__init__(parent)
        self.camera_widget = camera_widget

        # Title
        title = QLabel("AI Analysis")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #e0e0e0; padding: 8px 0;")

        # AI Analyze button
        self.btn_analyze = QPushButton("Analyze Current Frame")
        self.btn_analyze.setFixedHeight(44)
        self.btn_analyze.setStyleSheet("""
            QPushButton {
                background-color: #4a9eff;
                color: white;
                font-size: 15px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #3a8eef;
            }
            QPushButton:pressed {
                background-color: #2a7edf;
            }
        """)
        self.btn_analyze.clicked.connect(self.onAnalyze)

        # Results display
        self.txt_results = QTextEdit()
        self.txt_results.setReadOnly(True)
        self.txt_results.setPlaceholderText("Analysis results will appear here...")
        self.txt_results.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a2e;
                color: #d0d0d0;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 8px;
                font-size: 13px;
            }
        """)

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addWidget(self.btn_analyze)
        layout.addWidget(self.txt_results, 1)
        self.setLayout(layout)

    def onAnalyze(self):
        """Placeholder for AI analysis logic."""
        frame = self.camera_widget.getCurrentFrame()
        if frame is None:
            self.txt_results.setPlainText("Please open camera first.")
            return

        # TODO: Implement actual AI analysis logic
        # For now, show placeholder results
        self.txt_results.setHtml(
            "<h3>Analysis Results</h3>"
            "<p><b>Algae Concentration:</b></p>"
            "<ul>"
            "<li>Green algae: -- cells/mL</li>"
            "<li>Blue-green algae: -- cells/mL</li>"
            "<li>Diatoms: -- cells/mL</li>"
            "</ul>"
            "<p><b>Health Assessment:</b></p>"
            "<ul>"
            "<li>Overall health: --</li>"
            "<li>Water quality index: --</li>"
            "</ul>"
            "<p><b>Recommendations:</b></p>"
            "<ul>"
            "<li>TODO: AI analysis not yet implemented</li>"
            "</ul>"
        )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Microscope Algae Analyzer")
        self.setMinimumSize(1200, 750)

        # Central widget with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: camera view
        self.camera_widget = CameraWidget()

        # Right: analysis panel
        self.analysis_panel = AnalysisPanel(self.camera_widget)

        splitter.addWidget(self.camera_widget)
        splitter.addWidget(self.analysis_panel)
        splitter.setStretchFactor(0, 3)  # Left takes more space
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)

        # Global stylesheet
        self.setStyleSheet("""
            QMainWindow { background-color: #0f0f1a; }
            QWidget { background-color: #16213e; color: #e0e0e0; }
            QPushButton {
                background-color: #2a2a4a;
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #3a3a5a; }
        """)

    def closeEvent(self, event):
        self.camera_widget.closeCamera()
        event.accept()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
