import uvcham, pythoncom

class App:
    def __init__(self):
        self.hcam = None
        self.buf = None
        self.total = 0

    @staticmethod
    def cameraCallback(nEvent, ctx):
        ctx.CameraCallback(nEvent)

    def CameraCallback(self, nEvent):
        if nEvent == uvcham.UVCHAM_EVENT_IMAGE:
            self.hcam.pull(self.buf) # Pull Mode
            self.total += 1
            print('image ok, total = {}'.format(self.total))
        else:
            print('event callback: {}'.format(nEvent))

    def run(self):
        a = uvcham.Uvcham.enum()
        if len(a) > 0:
            print('name = {} id = {}'.format(a[0].displayname, a[0].id))
            self.hcam = uvcham.Uvcham.open(a[0].id)
            if self.hcam:
                try:
                    res = self.hcam.get(uvcham.UVCHAM_RES)
                    width = self.hcam.get(uvcham.UVCHAM_WIDTH | res)
                    height = self.hcam.get(uvcham.UVCHAM_HEIGHT | res)
                    bufsize = uvcham.TDIBWIDTHBYTES(width * 24) * height
                    print('image size: {} x {}, bufsize = {}'.format(width, height, bufsize))
                    self.buf = bytes(bufsize)
                    if self.buf:
                        try:
                            self.hcam.start(None, self.cameraCallback, self) # Pull Mode
                        except uvcham.HRESULTException as ex:
                            print('failed to start camera, hr=0x{:x}'.format(ex.hr))
                    input('press ENTER to exit')
                finally:
                    self.hcam.close()
                    self.hcam = None
                    self.buf = None
            else:
                print('failed to open camera')
        else:
            print('no camera found')

if __name__ == '__main__':
    pythoncom.CoInitialize()    # ATTENTION: initialize COM
    app = App()
    app.run()