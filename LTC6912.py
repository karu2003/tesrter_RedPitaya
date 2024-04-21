#!/usr/bin/python3

import sys
import time
import numpy as np
import signal_helper as sh


class LTC6912:
    def __init__(self, bus):
        self.bus = bus
        self.GAIN_dB = ["-120", "0", "6", "12", "18.1", "24.1", "30.1", "36.1", "-12x"]
        self.GAIN_HEX = [0x00, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88]
        self.GAIN_dB1 = ["0", "6", "12", "18.1", "24.1", "30.1", "36.1"]
        self.GAIN_HEX1 = [0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07]
        # self.bus.spi_mode("HIST")
        # # self.GAIN = {self.GAIN_dB[i]: self.GAIN_HEX[i] for i in range(len(self.GAIN_dB))}
        self.GAIN = dict(map(lambda i, j: (i, j), self.GAIN_dB, self.GAIN_HEX))
        self.GAIN1 = dict(map(lambda i, j: (i, j), self.GAIN_dB1, self.GAIN_HEX1))
        self.F = [26000.0, 60000.0, 150000.0]
        self.brd = ["18", "40", "HS"]
        self.brd_dict = dict(map(lambda i, j: (i, j), self.brd, self.F))

    def send_8bit_int(self, i):
        self.bus.send_spi_msc1(msg=str(i))
        time.sleep(0.2)
        self.bus.send_spi_msc1(msg=str(i))
        time.sleep(0.2)
        return

    def test_db(self, vin):
        result_dict = {}
        for k, v in self.GAIN.items():
            if k in ("0", "6", "12", "18.1", "24.1", "30.1"):
                print("Gain db", k)
                print("gain V ", v)
                self.send_8bit_int(v)
                data = self.read_same_level()
                result = sh.rms(data)
                print("RMS", result)
                result = sh.ratio_db(result, vin)
                print("Ratio", result)
                if k in ("0", "6", "12", "18.1", "24.1", "30.1"):
                    result_dict[k] = round(sh.rms(data), 3)
        return result_dict

    def find_gain(self, vin, width, pattern):
        result_dict = {}
        for k, v in self.GAIN1.items():
            for m, n in self.GAIN1.items():
                self.send_8bit_int(v << 4 | n)
                data = self.read_same_level()
                rms = sh.rms(data)
                result = round(sh.ratio_db(rms, vin), 3)
                result_dict[k, m] = result, 3
                error = sh.checking_width(width, pattern, abs(result))
                if not error:
                    print(
                        f'{format(v<<4|n, "#04x"):5}',
                        f"{result:<10}",
                        f"{round(rms,3):<10}",
                    )

        return result_dict

    def brd_id(self, ampl):
        for i in self.F:
            rp_c.set_gen(wave_form="sine", freq=i, ampl=ampl)
            data = AMP.read_same_level(thresh=0.1)
            brd_rms.append(round(sh.rms(data), 3))
        return self.brd[np.argmax(brd_rms)]

    def read_same_level(self, thresh=0.01, slice=100):
        sub = 1
        cnt = 0
        while sub >= thresh:
            data = []
            data = self.bus.read_now()
            # data = self.bus.read_oneL0()
            data = sh.voltage_divider_pre(data[0])
            # max_start = np.max(data[0:slice])
            # max_ende = np.max(data[-slice:-1])
            max_start = sh.rms(data[0:slice])
            max_ende = sh.rms(data[-slice:-1])
            sub = round(abs(max_start - max_ende), 3)
            cnt += 1
            if cnt == 10:
                return -1
        return data


if __name__ == "__main__":
    import redpctl as redpctl
    import time, sys
    from LTC1380 import LTC1380
    from DAT31R5A import Attenuator
    import signal_helper as sh

    dec = 32
    rp_c = redpctl.RedCtl(dec=dec, trig=0.005)
    MUX = LTC1380(rp_c)
    ATT = Attenuator(rp_c)
    AMP = LTC6912(rp_c)
    att_loss = 5.0
    ATT.set_loss(int(att_loss))
    brd_ch = ["ES_LIM", "ES_MAIN"]
    lowcut = 3e5

    brd_dict = dict(map(lambda i, j: (i, j), AMP.brd, AMP.F))

    ampl = 0.1
    vin = ((ampl / np.sqrt(2)) / sh.db_ratio(40)) / sh.db_ratio(att_loss)
    brd_rms = []

    MUX.set_ch("ES_MAIN")
    time.sleep(0.1)
    rp_c.gen_on(1)
    rp_c.adc1_2(1)
    rp_c.ss_gl(0)
    rp_c.pre_on(1)

    AMP.send_8bit_int(38)
    current_brd = AMP.brd_id(ampl)

    print(current_brd, "F = ", AMP.brd_dict[current_brd])

    rp_c.set_gen(wave_form="sine", freq=AMP.brd_dict[current_brd], ampl=ampl)
    # db_s = AMP.find_gain(vin, 2 ,60)

    BRD_setting = {
        #    main -6db -6db lim -3bd -3db
        "18": [10000.0, 51000.0, 10000.0, 56000.0],
        "40": [26000.0, 100000.0, 21000.0, 115000.0],
        "HS": [55000.0, 207000.0, 55000.0, 270000.0],
    }

    if 0:  # search for F-low and F-high main band-pass filter.
        data = AMP.read_same_level(thresh=0.01, slice=100)
        rms60 = sh.rms(data)
        ratio60 = sh.ratio_db(rms60, vin)
        print("Ratio 60", ratio60)

        for i in (0, 1):
            start_F = BRD_setting[current_brd][i]
            while 1:
                print(".", end="", flush=True)
                rp_c.set_gen(wave_form="sine", freq=start_F, ampl=ampl)
                time.sleep(0.5)
                data = AMP.read_same_level(thresh=0.05, slice=100)
                rms = sh.rms(data)
                ratio = sh.ratio_db(rms, vin)
                sub = ratio60 - ratio
                # print(start_F,"ratio",ratio, sub)
                error = sh.checking_width(0.1, 6, abs(sub))
                if not error:
                    print("")
                    print("frequency", start_F, "ratio", ratio, sub)
                    break
                start_F += 100

    if 1:  # search for F-low and F-high amplifier limiter
        MUX.set_ch("ES_LIM")
        time.sleep(0.1)
        ATT.set_loss(int(30))
        rp_c.ss_gl(1)
        vin = (
            ((ampl / np.sqrt(2)) / sh.db_ratio(40)) / sh.db_ratio(30) / sh.db_ratio(20)
        )
        print("Vin", vin)

        data = AMP.read_same_level(thresh=0.01, slice=100)
        rmsLIM = sh.rms(data)
        ratioLIM = sh.ratio_db(rmsLIM, vin)

        print(f'{format(rmsLIM, ".3f"):5}', "Ratio LIM", ratioLIM)

        for i in (2, 3):
            start_F = BRD_setting[current_brd][i]
            while 1:
                print(".", end="", flush=True)
                rp_c.set_gen(wave_form="sine", freq=start_F, ampl=ampl)
                time.sleep(0.2)
                data = AMP.read_same_level(thresh=0.05, slice=100)
                rms = sh.rms(data)
                ratio = sh.ratio_db(rms, vin)
                sub = ratioLIM - ratio
                # print(start_F,"ratio",f'{ratio:.3f}', f'{sub:.3f}')
                error = sh.checking_width(0.5, 6, abs(sub))
                if not error:
                    print("")
                    print("frequency", start_F, "ratio", f"{ratio:.3f}", f"{sub:.3f}")
                    break
                start_F += 50.0

    rp_c.pre_on(0)
