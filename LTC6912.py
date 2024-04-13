#!/usr/bin/python3

import sys
import time
import numpy as np


class LTC6912:
    def __init__(self, bus):
        self.num_bytes = 1
        self.bus = bus
        self.GAIN_dB = ["-120", "0", "6", "12", "18.1", "24.1", "30.1", "36.1", "-12x"]
        self.GAIN_HEX = [0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88]

    def send_8bit_int(self, msg):
        bytes = msg.to_bytes(self.num_bytes, byteorder="big")  # 'little'
        msg = ""
        for i in bytes:
            msg = msg + str(i) + ","
        msg = msg[:-1]
        # print(msg)
        self.bus.send_spi_msc1(msg=msg)
        time.sleep(0.1)
        return


if __name__ == "__main__":
    import redpctl as redpctl
    import time, sys
    from LTC1380 import LTC1380
    from DAT31R5A import Attenuator
    import signal_helper as sh

    rp_c = redpctl.RedCtl()
    MUX = LTC1380(rp_c)
    AMP = LTC6912(rp_c)
    ATT = Attenuator(rp_c)
    ATT.set_loss(30)
    brd = ["ES_LIM", "ES_MAIN"]
    msg = AMP.GAIN_HEX

    # rp_c.gen_on(0)
    rp_c.ss_gl(0)
    rp_c.pre_on(1)
    rp_c.adc1_2(0)
    MUX.set_ch("ES_LIM") # "ES_LIM" "ES_MAIN"
    AMP.send_8bit_int(msg[-1])

    # for k in brd:
    #     MUX.set_ch(k)
    #     time.sleep(0.1)
    #     print(k[:2])
    #     for i in msg:
    #         DAC.send_data(k[:2], "DAC_DATA", int(i) << 2)
    #         data = rp_c.read_oneL0()
    #         data = sh.voltage_divider_pre(data[0])
    #         print("DAC value {:f} {:s}".format((int(i) * 2.5 / DAC.width), hex(i)))
    #         print(sh.rms(data))
    #         time.sleep(0.2)
    # rp_c.adc1_2(0)
    # rp_c.pre_on(0)
