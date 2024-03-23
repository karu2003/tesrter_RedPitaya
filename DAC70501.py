#!/usr/bin/python3

import sys
import time
import numpy as np

GAIN1 = 0x00
GAIN2 = 0x01
DIV1 = 0x00
DIV2 = 0x01
sRESET = 0x0A


class DAC70501:
    def __init__(self, bus, dev=DIV2, gain=GAIN2, mux=None):
        self.width = 0x3FFF
        self.num_bytes = 3
        self.bus = bus
        self.dev = dev
        self.gain = gain
        self.brd = None
        self.mux = mux
        self.Register = {
            "DEVID": 1 << 16,
            "SYNC": 2 << 16,
            "CONFIG": 3 << 16,
            "GAIN": 4 << 16,
            "TRIGGER": 5 << 16,
            "STATUS": 7 << 16,
            "DAC_DATA": 8 << 16,
        }
        self.init("ES")
        self.init("SS")

    def byte_length(self, i):
        return (i.bit_length() + 7) // 8

    def send_24bit_int(self, msg):
        bytes = msg.to_bytes(self.num_bytes, byteorder="big")  # 'little'
        msg = ""
        for i in bytes:
            msg = msg + str(i) + ","
        msg = msg[:-1]
        # print(msg)
        self.bus.send_spi_msc(msg=msg)
        time.sleep(0.1)
        return

    def send_data(self, brd, reg, msg):
        if brd == "ES":
            self.bus.select_spi("ES_DAC")
            time.sleep(0.01)
            msg = msg | self.Register[reg]
            self.send_24bit_int(msg)
        elif brd == "SS":
            self.bus.select_spi("SS_DAC")
            time.sleep(0.01)
            msg = msg | self.Register[reg]
            self.send_24bit_int(msg)
        return

    def init(self, brd):
        self.bus.pre_on(1)
        time.sleep(0.5)
        self.soft_reset(brd)
        self.div_gain(brd, self.dev, self.gain)
        # self.send_data(brd, "SYNC", 0x00)
        # self.send_data(brd, "CONFIG", 0x0100)
        return

    def soft_reset(self, brd):
        self.send_data(brd, "TRIGGER", sRESET)
        return

    def div_gain(self, brd, div, gain):
        s = div << 8 | gain
        self.send_data(brd, "GAIN", int(s))
        return


if __name__ == "__main__":
    import redpctl as redpctl
    import time, sys
    from LTC1380 import LTC1380
    import signal_helper as sh

    rp_c = redpctl.RedCtl()
    MUX = LTC1380(rp_c)
    DAC = DAC70501(rp_c)
    brd = ["ES_VGAIN", "SS_VGAIN"]
    # brd = ["ES_MAIN", "SS_AOUT1", "SS_AOUT2"]
    msg = np.linspace(0, DAC.width, 10, dtype=int)
    # for i in msg:
    #     print(hex(int(i)))

    rp_c.gen_on(0)
    rp_c.ss_gl(0)
    rp_c.es_gl(0)

    for k in brd:
        MUX.set_ch(k)
        time.sleep(0.1)
        print(k[:2])
        for i in msg:
            DAC.send_data(k[:2], "DAC_DATA", int(i) << 2)
            data = rp_c.read_oneL0()
            data = sh.voltage_divider_pre(data[0])
            print("DAC value {:f} {:s}".format((int(i) * 2.5 / DAC.width), hex(i)))
            print(sh.rms(data))
            time.sleep(0.2)

    # MUX.set_ch("ES_VGAIN")
    # DAC.send_data("ES", "DAC_DATA", 0x7fff<<1)
    # data = rp_c.read_oneL0()
    # data = sh.voltage_divider_pre(data[0])
    # print(np.max(data))
    # rp_c.pre_on(0)
    # rp_c.spi_release()
