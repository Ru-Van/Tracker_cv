# -*- coding: utf-8 -*-
# ! /usr/bin/env python

import sys
from PyQt5 import uic
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import QPoint, QTimer
from PyQt5.QtGui import QPolygonF, QPainter, QImage
import numpy as np
import cv2 as cv
import threading
import datetime

WIDTH = 640
HEIGHT = 480

#Frame per second
class FPS:
    def __init__(self):
        self._start = None
        self._end = None
        self._numFrames = 0

    def start(self):
        # start the timer
        self._start = datetime.datetime.now()
        self._numFrames = 0
        return self

    def stop(self):
        # stop the timer
        self._end = datetime.datetime.now()

    def update(self):
        # increment the total number of frames examined during the
        # start and end intervals
        self._numFrames += 1

    def elapsed(self):
        return (self._end - self._start).total_seconds()

    def fps(self):
        # compute the (approximate) frames per second
        return self._numFrames / self.elapsed()

# Paint image
class OwnImageWidget(QWidget):
    def __init__(self, parent=None):
        super(OwnImageWidget, self).__init__(parent)
        self.image = None

    def setImage(self, image):
        self.image = image
        self.pol = QPolygonF()
        sz = image.size()
        self.setMinimumSize(sz)
        self.update()

    def paintEvent(self, event):
        qp = QPainter()
        qp.begin(self)
        if self.image:
            qp.drawImage(QPoint(0, 0), self.image)
        qp.end()


class Rectangle:
    def __init__(self, color=(0, 0, 255), thickness=1):
        self.x1 = 0
        self.x2 = 0
        self.y1 = 0
        self.y2 = 0
        self.color = color
        self.thickness = thickness

    @property
    def p1(self):
        return (min(self.x1, self.x2), min(self.y1, self.y2))

    @property
    def p2(self):
        return (max(self.x1, self.x2), max(self.y1, self.y2))

    @property
    def xywh(self):
        x, y = self.p1
        w = abs(self.x2 - self.x1)
        h = abs(self.y2 - self.y1)
        if w == 0 and h == 0:
            return x, y, 2, 2
        else:
            return x, y, w, h

    def draw(self, canvas):
        cv.rectangle(canvas, self.p1, self.p2, self.color, self.thickness)
        return canvas

# Tracker
class Tracker:
    def __init__(self):
        self.tracker = None
        self._active = False

    @property
    def active(self):
        return hasattr(self, '_active') and self._active

    @active.setter
    def active(self, value):
        self._active = value
        if value == True:
            self.tracker = cv.TrackerCSRT_create()
        elif value == False:
            del self.tracker

# Main window
class MainWindow(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

        uic.loadUi(r'designer.ui', self)
        # Web Cum
        self.cam_width = WIDTH
        self.cam_height = HEIGHT
        self.cap = cv.VideoCapture(0)

        self.cap.set(cv.CAP_PROP_FRAME_WIDTH, WIDTH)
        self.cap.set(cv.CAP_PROP_FRAME_HEIGHT, HEIGHT)

        self.flagVideo = True
        self.thrVIDEO = threading.Thread(target=self.videoData)
        self.thrVIDEO.start()

        self.ImgWidget = OwnImageWidget(self.widget)
        self.timer = QTimer()
        self.timer.timeout.connect(self.Start_acq)
        self.timer.start(33)

        # self.drawing = False
        # self.rectangle = None
        self.data = None
        self.rc = Rectangle()
        self.tracker = Tracker()
        self.fps_time = FPS().start()

        self.mean_fps = []

        self.xywh = np.zeros(4, dtype=np.int16)

        self.widget.mousePressEvent = self.press
        self.widget.mouseReleaseEvent = self.release
        self.widget.keyPressEvent = self.keyPressEvent_new
        self.widget.setFocus()

    # Mouse press
    def press(self, event):
        pos = event.pos()
        self.rc.x1 = event.pos().x()
        self.rc.y1 = event.pos().y()
        #self.drawing = True

    # Mouse release
    def release(self, event):
        self.rc.x2 = event.pos().x()
        self.rc.y2 = event.pos().y()
        self.tracker.active = True
        self.tracker.tracker = cv.TrackerCSRT_create()
        self.tracker.tracker.init(self.data, self.rc.xywh)
        self.x,self.y,self.w,self.h = self.rc.xywh
        #self.drawing = False
        #self.rectangle = None

    def videoData(self):
        while self.flagVideo:
            ret, self.data = self.cap.read()
            self.data = self.convert_BGB_to_RGB(self.data)

    def convert_BGB_to_RGB(self, data):
        return cv.cvtColor(data, cv.COLOR_BGR2RGB)

    # keyboard handler
    def keyPressEvent_new(self, e):
        if e.key() == 16777216: #Esc
            self.close()
        elif e.key() == 32: #Пробел
            self.tracker.active = False

    def Start_acq(self):

        if self.tracker.active:
            ret, box = self.tracker.tracker.update(self.data)

            if ret and box is not None:
                self.xywh[:] = box
                (x, y, w, h) = map(int, box)

                cv.rectangle(self.data, (int(x), int(y)), (int(x) + int(w), int(y) + int(h)), (255,0,0), 2)
                cv.putText(self.data, str(w) + 'x' + str(h), (self.xywh[0] + 5, self.xywh[1] - 5),
                            cv.FONT_HERSHEY_SIMPLEX, 0.5, (255,0,0), 1)

                image = QImage(self.data, self.cam_width,
                                     self.cam_height,
                                     QImage.Format_RGB888)

                self.ImgWidget.setImage(image)

                self.fps_time.update()
                self.mean_fps.append(1)
                if len(self.mean_fps) == 10:
                    self.mean_fps = []
                    self.fps_time.stop()
                    self.FPS.setText("  FPS: {:.2f}".format(self.fps_time.fps()))
                    self.fps_time.start()
            else:
                image = QImage(self.data, self.cam_width,
                               self.cam_height,
                               QImage.Format_RGB888)
                self.ImgWidget.setImage(image)

                self.fps_time.update()
                self.mean_fps.append(1)
                if len(self.mean_fps) == 10:
                    self.mean_fps = []
                    self.fps_time.stop()
                    self.FPS.setText("  FPS: {:.2f}".format(self.fps_time.fps()))
                    self.fps_time.start()
        else:
            image = QImage(self.data, self.cam_width,
                           self.cam_height,
                           QImage.Format_RGB888)
            self.ImgWidget.setImage(image)

            self.fps_time.update()
            self.mean_fps.append(1)
            if len(self.mean_fps) == 10:
                self.mean_fps = []
                self.fps_time.stop()
                self.FPS.setText("  FPS: {:.2f}".format(self.fps_time.fps()))
                self.fps_time.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    myapp = MainWindow()
    myapp.show()
    app.installEventFilter(myapp)
    while app.exec_(): pass
    myapp.flagVideo = False
    myapp.thrVIDEO.join()