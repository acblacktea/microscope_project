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
    """左侧面板：显微镜实时视频画面"""
    evtCallback = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hcam = None
        self.imgWidth = 0
        self.imgHeight = 0
        self.pData = None
        self.frame = 0
        self.timer = QTimer(self)

        # 视频显示区域
        self.lbl_video = QLabel("未连接相机")
        self.lbl_video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_video.setStyleSheet(
            "QLabel { background-color: #1a1a2e; color: #888; "
            "font-size: 16px; border: 1px solid #333; border-radius: 4px; }"
        )
        self.lbl_video.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # 相机控制栏
        self.btn_open = QPushButton("打开相机")
        self.btn_open.setFixedHeight(36)
        self.btn_open.clicked.connect(self.onBtnOpen)

        self.lbl_status = QLabel("状态：未连接")
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
        ctx.evtCallback.emit(nEvent)

    def onEvtCallback(self, nEvent):
        if self.hcam is not None:
            if uvcham.UVCHAM_EVENT_IMAGE & nEvent != 0:
                self.onImageEvent()
            elif uvcham.UVCHAM_EVENT_ERROR & nEvent != 0:
                self.closeCamera()
                QMessageBox.warning(self, "警告", "相机发生错误。")
            elif uvcham.UVCHAM_EVENT_DISCONNECT & nEvent != 0:
                self.closeCamera()
                QMessageBox.warning(self, "警告", "相机已断开连接。")

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
            self.lbl_status.setText(f"状态：运行中 | 帧数：{self.frame}")

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
                QMessageBox.warning(self, "警告", "启动相机失败。")
            else:
                self.btn_open.setText("关闭相机")
                self.lbl_status.setText("状态：运行中 | 帧数：0")
                self.timer.start(1000)

    def onBtnOpen(self):
        if self.hcam is not None:
            self.closeCamera()
        else:
            arr = uvcham.Uvcham.enum()
            if len(arr) == 0:
                QMessageBox.warning(self, "警告", "未找到相机。")
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
        self.btn_open.setText("打开相机")
        self.lbl_status.setText("状态：未连接")
        self.lbl_video.clear()
        self.lbl_video.setText("未连接相机")
        self.timer.stop()

    def getCurrentFrame(self):
        """返回当前帧的 QImage，无相机时返回 None。"""
        if self.hcam is not None and self.pData is not None:
            return QImage(self.pData, self.imgWidth, self.imgHeight, QImage.Format.Format_RGB888)
        return None


class AnalysisPanel(QWidget):
    """右侧面板：AI 分析控制与结果展示"""

    def __init__(self, camera_widget: CameraWidget, parent=None):
        super().__init__(parent)
        self.camera_widget = camera_widget

        # 标题
        title = QLabel("AI 智能分析")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #e0e0e0; padding: 8px 0;")

        # AI 分析按钮
        self.btn_analyze = QPushButton("分析当前画面")
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

        # 结果显示区域
        self.txt_results = QTextEdit()
        self.txt_results.setReadOnly(True)
        self.txt_results.setPlaceholderText("分析结果将在此处显示...")
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
        """AI 分析逻辑占位"""
        frame = self.camera_widget.getCurrentFrame()
        if frame is None:
            self.txt_results.setPlainText("请先打开相机。")
            return

        # TODO: 接入实际的 AI 分析逻辑
        self.txt_results.setHtml(
            "<h3>分析报告</h3>"
            "<p><b>藻类浓度：</b></p>"
            "<ul>"
            "<li>绿藻：-- cells/mL</li>"
            "<li>蓝绿藻：-- cells/mL</li>"
            "<li>硅藻：-- cells/mL</li>"
            "</ul>"
            "<p><b>健康度评估：</b></p>"
            "<ul>"
            "<li>整体健康度：--</li>"
            "<li>水质指数：--</li>"
            "</ul>"
            "<p><b>养殖建议：</b></p>"
            "<ul>"
            "<li>待接入 AI 分析模块</li>"
            "</ul>"
        )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("微生物智能分析系统")
        self.setMinimumSize(1200, 750)

        # 中央容器
        central = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(8)

        # 顶部标题栏
        header = QHBoxLayout()
        lbl_title = QLabel("微生物智能分析系统")
        lbl_title.setFont(QFont("Microsoft YaHei", 18, QFont.Weight.Bold))
        lbl_title.setStyleSheet("color: #4a9eff; background: transparent; padding: 4px 0;")
        header.addWidget(lbl_title)
        header.addStretch()
        main_layout.addLayout(header)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #333; max-height: 1px;")
        main_layout.addWidget(line)

        # 左右分栏（可拖拽）
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(6)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #333;
                border-radius: 2px;
            }
            QSplitter::handle:hover {
                background-color: #4a9eff;
            }
        """)

        # 左侧：相机画面
        self.camera_widget = CameraWidget()
        self.camera_widget.setMinimumWidth(400)

        # 右侧：分析面板
        self.analysis_panel = AnalysisPanel(self.camera_widget)
        self.analysis_panel.setMinimumWidth(280)

        self.splitter.addWidget(self.camera_widget)
        self.splitter.addWidget(self.analysis_panel)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([900, 300])

        main_layout.addWidget(self.splitter, 1)
        central.setLayout(main_layout)
        self.setCentralWidget(central)

        # 全局样式
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
