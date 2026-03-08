import sys, uvcham
from PyQt5.QtCore import pyqtSignal, pyqtSlot, QTimer, QSignalBlocker, Qt
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import QLabel, QApplication, QWidget, QCheckBox, QMessageBox, QPushButton, QComboBox, QSlider, QGroupBox, QGridLayout, QBoxLayout, QHBoxLayout, QVBoxLayout, QMenu, QAction

class MainWidget(QWidget):
    evtCallback = pyqtSignal(int)

    @staticmethod
    def makeLayout(lbl1, sli1, val1, lbl2, sli2, val2):
        hlyt1 = QHBoxLayout()
        hlyt1.addWidget(lbl1)
        hlyt1.addStretch()
        hlyt1.addWidget(val1)
        hlyt2 = QHBoxLayout()
        hlyt2.addWidget(lbl2)
        hlyt2.addStretch()
        hlyt2.addWidget(val2)
        vlyt = QVBoxLayout()
        vlyt.addLayout(hlyt1)
        vlyt.addWidget(sli1)
        vlyt.addLayout(hlyt2)
        vlyt.addWidget(sli2)
        return vlyt

    def __init__(self):
        super().__init__()
        self.setMinimumSize(1024, 768)
        self.hcam = None
        self.imgWidth = 0
        self.imgHeight = 0
        self.pData = None
        self.frame = 0
        self.count = 0
        self.timer = QTimer(self)

        gboxexp = QGroupBox("Exposure")
        self.cbox_auto = QCheckBox("Auto exposure")
        self.cbox_auto.setEnabled(False)
        self.lbl_expoTime = QLabel("0")
        self.lbl_expoGain = QLabel("0")
        self.slider_expoTime = QSlider(Qt.Horizontal)
        self.slider_expoGain = QSlider(Qt.Horizontal)
        self.slider_expoTime.setEnabled(False)
        self.slider_expoGain.setEnabled(False)
        self.cbox_auto.stateChanged.connect(self.onAutoExpo)
        self.slider_expoTime.valueChanged.connect(self.onExpoTime)
        self.slider_expoGain.valueChanged.connect(self.onExpoGain)
        vlytexp = QVBoxLayout()
        vlytexp.addWidget(self.cbox_auto)
        vlytexp.addLayout(self.makeLayout(QLabel("Time:"), self.slider_expoTime, self.lbl_expoTime, QLabel("Gain:"), self.slider_expoGain, self.lbl_expoGain))
        gboxexp.setLayout(vlytexp)

        self.btn_autoWB = QPushButton("White balance")
        self.btn_autoWB.setEnabled(False)
        self.btn_autoWB.clicked.connect(self.onWB)
        self.btn_open = QPushButton("Open")
        self.btn_open.clicked.connect(self.onBtnOpen)
        self.btn_snap = QPushButton("Snap")
        self.btn_snap.setEnabled(False)
        self.btn_snap.clicked.connect(self.onBtnSnap)

        vlytctrl = QVBoxLayout()
        vlytctrl.addWidget(gboxexp)
        vlytctrl.addWidget(self.btn_autoWB)
        vlytctrl.addWidget(self.btn_open)
        vlytctrl.addWidget(self.btn_snap)
        vlytctrl.addStretch()
        wgctrl = QWidget()
        wgctrl.setLayout(vlytctrl)

        self.lbl_frame = QLabel()
        self.lbl_video = QLabel()
        vlytshow = QVBoxLayout()
        vlytshow.addWidget(self.lbl_video, 1)
        vlytshow.addWidget(self.lbl_frame)
        wgshow = QWidget()
        wgshow.setLayout(vlytshow)

        gmain = QGridLayout()
        gmain.setColumnStretch(0, 1)
        gmain.setColumnStretch(1, 4)
        gmain.addWidget(wgctrl)
        gmain.addWidget(wgshow)
        self.setLayout(gmain)

        self.evtCallback.connect(self.onevtCallback)
        self.timer.timeout.connect(self.onTimer)

    @staticmethod
    def eventCallBack(nEvent, self):
        '''callbacks come from uvcham.dll internal threads, so we use qt signal to post this event to the UI thread'''
        self.evtCallback.emit(nEvent)

    def onevtCallback(self, nEvent):
        '''this run in the UI thread'''
        if self.hcam is not None:
            if uvcham.UVCHAM_EVENT_IMAGE & nEvent != 0:
                self.onImageEvent()
            elif uvcham.UVCHAM_EVENT_ERROR & nEvent != 0:
                self.closeCamera()
                QMessageBox.warning(self, "Warning", "Generic error.")
            elif uvcham.UVCHAM_EVENT_DISCONNECT & nEvent != 0:
                self.closeCamera()
                QMessageBox.warning(self, "Warning", "Camera disconnect.")

    def onAutoExpo(self, state):
        if self.hcam is not None:
            self.hcam.put(uvcham.UVCHAM_AEXPO, 1 if state else 0)
            self.slider_expoTime.setEnabled(not state)
            self.slider_expoGain.setEnabled(not state)

    def onWB(self):
        if self.hcam is not None:
            self.hcam.put(uvcham.UVCHAM_WBMODE, 3)

    def onExpoTime(self, value):
        if self.hcam is not None:
            self.lbl_expoTime.setText(str(value))
            if not self.cbox_auto.isChecked():
               self.hcam.put(uvcham.UVCHAM_EXPOTIME, value)

    def onExpoGain(self, value):
        if self.hcam is not None:
            self.lbl_expoGain.setText(str(value))
            if not self.cbox_auto.isChecked():
               self.hcam.put(uvcham.UVCHAM_AGAIN, value)

    def updateExpoTime(self):
        val = self.hcam.get(uvcham.UVCHAM_EXPOTIME)
        with QSignalBlocker(self.slider_expoTime):
            self.slider_expoTime.setValue(val)
        self.lbl_expoTime.setText(str(val))

    def updateGain(self):
        val = self.hcam.get(uvcham.UVCHAM_AGAIN)
        with QSignalBlocker(self.slider_expoGain):
            self.slider_expoGain.setValue(val)

    def onTimer(self):
        if self.hcam is not None:
            self.lbl_frame.setText(str(self.frame))

            if self.cbox_auto.isChecked():
                self.updateExpoTime()
                self.updateGain()

    def openCamera(self, id):
        self.hcam = uvcham.Uvcham.open(id)
        if self.hcam:
            self.frame = 0
            self.hcam.put(uvcham.UVCHAM_FORMAT, 2) #Qimage use RGB byte order

            res = self.hcam.get(uvcham.UVCHAM_RES)
            self.imgWidth = self.hcam.get(uvcham.UVCHAM_WIDTH | res)
            self.imgHeight = self.hcam.get(uvcham.UVCHAM_HEIGHT | res)
            self.pData = bytes(uvcham.TDIBWIDTHBYTES(self.imgWidth * 24) * self.imgHeight)
            try:
                self.hcam.start(None, self.eventCallBack, self) # Pull Mode
            except uvcham.HRESULTException:
                self.closeCamera()
                QMessageBox.warning(self, "Warning", "Failed to start camera.")
            else:
                self.cbox_auto.setEnabled(True)
                self.btn_autoWB.setEnabled(True)
                self.btn_open.setText("Close")
                self.btn_snap.setEnabled(True)

                nmin, nmax, ndef = self.hcam.range(uvcham.UVCHAM_EXPOTIME)
                self.slider_expoTime.setRange(nmin, nmax)
                nmin, nmax, ndef = self.hcam.range(uvcham.UVCHAM_AGAIN)
                self.slider_expoGain.setRange(nmin, nmax)
                bAuto = self.hcam.get(uvcham.UVCHAM_AEXPO)
                self.cbox_auto.setChecked(1 == bAuto)
                self.slider_expoTime.setEnabled(1 != bAuto)
                self.slider_expoGain.setEnabled(1 != bAuto)
                self.updateExpoTime()
                self.updateGain()

                self.timer.start(1000)

    def onBtnOpen(self):
        if self.hcam is not None:
            self.closeCamera()
        else:
            arr = uvcham.Uvcham.enum()
            if len(arr) == 0:
                QMessageBox.warning(self, "Warning", "No camera found.")
            elif 1 == len(arr):
                self.openCamera(arr[0].id)
            else:
                menu = QMenu()
                for i in range(0, len(arr)):
                    action = QAction(arr[i].displayname, self)
                    action.setData(i)
                    menu.addAction(action)
                action = menu.exec(self.mapToGlobal(self.btn_open.pos()))
                if action:
                    self.openCamera(arr[action.data()].id)

    def onBtnSnap(self):
        if self.hcam is not None and self.pData is not None:
            image = QImage(self.pData, self.imgWidth, self.imgHeight, QImage.Format_RGB888)
            self.count += 1
            image.save("pyqt{}.jpg".format(self.count))

    def onImageEvent(self):
        self.hcam.pull(self.pData) # Pull Mode
        self.frame += 1
        image = QImage(self.pData, self.imgWidth, self.imgHeight, QImage.Format_RGB888)
        newimage = image.scaled(self.lbl_video.width(), self.lbl_video.height(), Qt.KeepAspectRatio, Qt.FastTransformation)
        self.lbl_video.setPixmap(QPixmap.fromImage(newimage))

    def closeCamera(self):
        if self.hcam:
            self.hcam.close()
        self.hcam = None
        self.pData = None

        self.btn_open.setText("Open")
        self.timer.stop()
        self.lbl_frame.clear()
        self.cbox_auto.setEnabled(False)
        self.slider_expoGain.setEnabled(False)
        self.slider_expoTime.setEnabled(False)
        self.btn_autoWB.setEnabled(False)
        self.btn_snap.setEnabled(False)

    def closeEvent(self, event):
        if self.hcam is not None:
            self.hcam.close()
            self.hcam = None

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mw = MainWidget()
    mw.show()
    sys.exit(app.exec_())