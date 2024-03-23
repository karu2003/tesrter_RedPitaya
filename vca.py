#!/usr/bin/python3

import sys
import time
import numpy as np
import signal_helper as sh


class VCA:
    def __init__(self, DAC):
        self.DAC = DAC
        self.max_gain = 90
        self.mincode = 150
        self.maxcode = 16383
        self.DAC_coeff = float(16383.0 * (1.568 + 1.18) / 1.18 / 2.5)
        self.GainShift = {
            "ES": 1.3767967,  #
            "SS": 2.9319898,  #
        }

    def vgain(self, gain=3.0, brd="ES"):
        v = (gain - self.GainShift[brd]) / 80.0
        v = self.DAC_coeff * v
        if int(v) > self.maxcode:
            v = self.maxcode
        return int(v) << 2

    def input_test(self, brd, gain):
        signal = {}
        data = []
        for k in brd:
            data = []
            MUX.set_ch(k)
            for i in gain:
                self.DAC.send_data(k[:2], "DAC_DATA", self.vgain(i, k[:2]))
                data.append(sh.voltage_divider_pre(rp_c.read_oneL0()[0]))
                time.sleep(0.1)
            signal[k] = data
        return signal

    def signal_db(self, brd, signal, vin):
        for i in brd:
            signal_max = []
            for count, value in enumerate(signal[i]):
                # signal_max.append(np.max(value))
                signal_max.append(sh.rms(value))
            signal[i] = signal_max

        for i in brd:
            ratio_db = []
            count = len(signal[i])
            for k in range(count):
                ratio_db.append(sh.ratio_db(signal[i][k], vin))
            signal[i] = ratio_db
        return signal

    def subtract_arr(self, dic, arr):
        brd = {}
        a = np.array(arr, dtype=float) * -1
        for i in dic.keys():
            sub_db = []
            sub_db.append(a - dic[i])
            brd[i] = sub_db
        return brd

    # for i in brd:
    #     ratio_db = []
    #     count = len(signal[i])-1
    #     for k in range(count):
    #         ratio_db.append(sh.ratio_db(signal[i][k+1],signal[i][k]))
    #     signal[i] = ratio_db


if __name__ == "__main__":
    import time, sys
    import redpctl as redpctl
    import signal_helper as sh
    from LTC1380 import LTC1380
    from DAC70501 import DAC70501
    from DAT31R5A import Attenuator

    duration = 0.00025
    dec = 1
    rp_c = redpctl.RedCtl(dec=dec)
    MUX = LTC1380(rp_c)
    DAC = DAC70501(rp_c)
    ATT = Attenuator(rp_c)
    VGA = VCA(DAC)

    f_min = 110000
    f_max = 380000
    f_mid = 250000

    vin = 0.07 / sh.db_ratio(40)
    ATT.set_loss(7)
    gain = [40, 60]
    rp_c.gen_on(1)

    brd = ["ES_MAIN"]
    # rp_c.chirp(f_min=110000, f_max=380000, duration=duration, ampl=0.307)
    rp_c.set_gen(wave_form="sine", freq=f_mid, ampl=0.1)
    signal = VGA.input_test(brd, gain)
    db_dic = VGA.signal_db(brd, signal, vin)
    # print(db_dic)
    # print(VGA.subtract_arr(db_dic, gain))

    f_min = 175000
    f_max = 1100000
    f_mid = 500000

    brd = ["SS_AOUT1", "SS_AOUT2"]
    # rp_c.chirp(f_min=175000, f_max=1100000, duration=duration, ampl=0.307)
    rp_c.set_gen(wave_form="sine", freq=f_mid, ampl=0.1)
    signal = VGA.input_test(brd, gain)
    db_dic = VGA.signal_db(brd, signal, vin)
    # print(db_dic)
    # print(VGA.subtract_arr(db_dic, gain))

    rp_c.gen_on(0)
    gain = [80]
    brd = ["ES_MAIN"]
    signal = VGA.input_test(brd, gain)
    print(signal)
    # print(np.max(signal))

    # rp_c.pre_on(0)
