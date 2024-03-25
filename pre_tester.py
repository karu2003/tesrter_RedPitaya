#!/usr/bin/python3
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt

import matplotlib.pyplot as plt
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui
import sys
import time

# import os
import numpy as np
import redpctl as redpctl
import ping3
import signal_helper as sh
from tests import TESTs


ping3.EXCEPTIONS = True

uiclass, baseclass = pg.Qt.loadUiType("ui_pre.ui")


class MainWindow(uiclass, baseclass, object):
    def __init__(self):
        self.app = QtWidgets.QApplication(sys.argv)

        super().__init__()
        self.IP = "192.168.0.15"
        self.setupUi(self)
        try:
            ping3.ping(self.IP, ttl=1)
        except ping3.errors.TimeToLiveExpired as err:
            print(err.ip_header[self.IP])

        self.rx_buffer_size = 16384

        self.dec = 1
        self.rp_c = redpctl.RedCtl(dec=self.dec)

        self.ALL = TESTs(self.rp_c)
        self.ES = TESTs(self.rp_c, "ES")
        self.SS = TESTs(self.rp_c, "SS")
        self.Tests = self.ALL

        self.CH = ["ALL", "ES", "SS"]
        self.count_CH = 0
        self.table_added = 1
        self.Begin = False
        self.error = 0
        self.result = ""

        # self.showMaximized()
        # self.showFullScreen()

        self.RED = (255, 0, 0)
        self.GREEN = (0, 255, 0)
        self.GREY = (200, 200, 200)
        font = QtGui.QFont("Courier")
        font.setPixelSize(30)
        font.setBold(True)
        self.text = pg.TextItem()
        self.text.setFont(font)

        self.measurements = self.win.addPlot(title="Measurements", row=2, col=1)
        self.measurements.hideAxis("left")
        self.measurements.hideAxis("bottom")

        self.vb_w = self.measurements.getViewBox()

        self.btn_ch.setText(self.CH[0])
        self.btn_start.setText("START")
        self.btn_training.setText("off")

        self.btn_save.clicked.connect(self.ButtonSave)
        self.btn_training.clicked.connect(self.ButtonTraining)
        self.btn_ch.clicked.connect(self.ButtonCh)
        self.btn_start.clicked.connect(self.ButtonStart)

        text_items = ["Test", "Results"]
        self.custom_table = {}
        self.table_x = 100
        self.table_y = 100
        scaler = 80
        for i, text in enumerate(text_items):
            self.custom_table[text] = pg.TextItem(text=text)
            self.custom_table[text].setParentItem(parent=self.measurements)
            self.custom_table[text].setFont(font)
            self.custom_table[text].setPos(self.table_x, self.table_y + scaler * i)

    def ButtonSave(self):
        self.save = True
        print("Clicked Save")

    def ButtonTraining(self):
        text = self.btn_training.text()
        if text == "off":
            self.btn_training.setText("on")
            self.rp_c.pre_on(1)
        else:
            self.btn_training.setText("off")
            self.rp_c.pre_on(0)

    def ButtonCh(self):
        self.count_CH = (self.count_CH + 1) % 3
        self.btn_ch.setText(self.CH[self.count_CH])
        text = self.btn_ch.text()
        if text == "ALL":
            self.Tests = self.ALL
        if text == "ES":
            self.Tests = self.ES
        if text == "SS":
            self.Tests = self.SS

    def ButtonStart(self):
        text = self.btn_start.text()
        if text == "START":
            self.btn_start.setText("STOP")
            self.Begin = True
            self.error = False
            self.vb_w.setBackgroundColor("black")
            self.custom_table["Test"].setText("Wait", self.GREY)
            self.custom_table["Results"].setText("", self.GREY)
        else:
            self.btn_start.setText("START")
            self.Begin = False
            self.Tests.last = True

    def update(self):
        if self.Begin and not self.error:
            self.result = self.Tests.test()

            self.custom_table["Test"].setText(
                "{:d}  {:s}".format(self.Tests.counter, self.Tests.current),
                self.GREY,
            )
            self.custom_table["Results"].setText(
                self.result,
                self.GREY,
            )
            if self.Tests.error:
                self.btn_start.setText("START")
                self.Tests.error = False
                self.Begin = False
                self.Tests.counter = -1
                self.rp_c.pre_on(0)
                self.vb_w.setBackgroundColor("red")
                self.error = True
                print("error")
                self.custom_table["Results"].setText(
                    "Test Error",
                    self.RED,
                )
            if self.Tests.last:
                if not self.error:
                    self.btn_start.setText("START")
                    self.Tests.last = False
                    self.Begin = False
                    self.rp_c.pre_on(0)
                    self.vb_w.setBackgroundColor("green")
                    print("test passed")
                    self.custom_table["Test"].setText(
                        "All",
                        self.GREEN,
                    )
                    self.custom_table["Results"].setText(
                        "Test Passed",
                        self.GREEN,
                    )
                    self.Tests.save_log()

    def start(self):
        self.app.exec_()

    def animation(self):
        timer = QtCore.QTimer()
        timer.setInterval(30)
        timer.timeout.connect(self.update)
        timer.start()  # 1
        self.start()


if __name__ == "__main__":
    main = MainWindow()
    main.show()
    main.animation()
    print("Exiting...")
