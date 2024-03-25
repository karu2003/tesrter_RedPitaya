import redpctl as redpctl
import time

Red = "\033[1;31;40m"
Green = "\033[1;32;40m"
White = "\033[1;37;40m"
# Black = "\033[1;37;40m \033[2;37:40m"

from LTC1380 import LTC1380
from DAC70501 import DAC70501
from DAT31R5A import Attenuator
from vca import VCA
from ADC import ADC

import signal_helper as sh
import pandas as pd

pd.options.display.max_columns = None


class TESTs:
    def __init__(self, bus, brd=None):
        self.bus = bus
        self.MUX = LTC1380(self.bus)
        self.DAC = DAC70501(self.bus)
        self.ATT = Attenuator(self.bus)
        self.VCA = VCA(self.DAC)
        self.adc = ADC(self.bus)
        self.bus.pre_on(0)
        self.current = None
        self.counter = None
        self.last = None
        self.error = 0
        self.result = ""
        self.s = "_"
        self.data = []

        self.F = {
            "ES": [110000, 380000, 250000],
            "SS": [175000, 1100000, 500000],
        }

        self.vin = 0.07 / sh.db_ratio(40)
        self.ATT.set_loss(8)

        self.TEST_result = {
            "ES_MAIN_NOISE": ["+-", 0.04, 0.14],  # 0.110
            "ES_MAIN_GAIN_40": ["+-", 1.75, 40],
            "ES_MAIN_GAIN_60": ["+-", 1.75, 60],
            "ES_MAIN_GAIN_LOW": ["<", 50],
            "ES_MAIN_BW": ["+-", 1.75, 54, 54, 60],
            "SS_AOUT1_NOISE": ["+-", 0.04, 0.14],  # 0.140
            "SS_AOUT1_GAIN_40": ["+-", 1.75, 40],
            "SS_AOUT1_GAIN_60": ["+-", 1.75, 60],
            "SS_AOUT1_GAIN_LOW": ["<", 50],
            "SS_AOUT1_BW": ["+-", 1.75, 54, 54, 60],
            "SS_ADC1": ["%", 4, 1.5],
            "SS_AOUT2_NOISE": ["+-", 0.04, 0.14],  # 0.140
            "SS_AOUT2_GAIN_40": ["+-", 1.75, 40],
            "SS_AOUT2_GAIN_60": ["+-", 1.75, 60],
            "SS_AOUT2_GAIN_LOW": ["<", 50],
            "SS_AOUT2_BW": ["+-", 1.75, 54, 54, 60],
            "SS_ADC2": ["%", 4, 1.5],
        }

        self.TEST_all = [
            "ES_MAIN_NOISE",
            "ES_MAIN_GAIN_40",
            "ES_MAIN_GAIN_60",
            "ES_MAIN_GAIN_LOW",
            "ES_MAIN_BW",
            "SS_AOUT1_NOISE",
            "SS_AOUT1_GAIN_40",
            "SS_AOUT1_GAIN_60",
            "SS_AOUT1_GAIN_LOW",
            "SS_AOUT1_BW",
            "SS_ADC1",
            "SS_AOUT2_NOISE",
            "SS_AOUT2_GAIN_40",
            "SS_AOUT2_GAIN_60",
            "SS_AOUT2_GAIN_LOW",
            "SS_AOUT2_BW",
            "SS_ADC2",
        ]
        self.TEST_name = []

        self.df = pd.DataFrame(columns=self.TEST_all)

        if brd == None:
            self.TEST_name = self.TEST_all

        for i, text in enumerate(self.TEST_all):
            if text.split("_")[0] == brd:
                self.TEST_name.append(text)

    def print_tests(self, i=180.0):
        colors = {
            "cR": "\033[91m",
            "cG": "\033[92m",
            "cB": "\33[94m",
            "END": "\033[0m",
            "cX": 0,
        }
        result_str = ""
        colors["cX"] = colors["cR"] if self.error else colors["cG"]
        good = ("{cX}" + ("BAD" if self.error else "OK") + "{END}").format(**colors)

        if type(i) == list:
            result_str = " ".join(str(format(x, ".3f")) for x in i)
        else:
            result_str = str(format(i, ".3f"))
        print(f"{self.current:<18}", f"{result_str:<24}", f"{good}")
        return result_str

    def test(self, brd=None):
        if self.current == None:
            self.counter = 0
            self.current = self.TEST_name[self.counter]
        else:
            self.counter = (self.counter + 1) % len(self.TEST_name)
            self.current = self.TEST_name[self.counter]

        if self.counter == len(self.TEST_name) - 1:
            self.last = 1

        if self.current == "ES_MAIN_NOISE":
            self.bus.gen_on(0)
            self.bus.pre_on(1)
            self.bus.es_gl(0)
            self.bus.ss_gl(0)
            time.sleep(0.5)
            self.result = self.brd_noise()

        elif self.current == "ES_MAIN_GAIN_40":
            self.result = self.brd_gain()

        elif self.current == "ES_MAIN_GAIN_60":
            self.result = self.brd_gain()

        elif self.current == "ES_MAIN_GAIN_LOW":
            self.result = self.brd_gl()

        elif self.current == "ES_MAIN_BW":
            self.result = self.brd_bw()

        elif self.current == "SS_AOUT1_NOISE":
            self.result = self.brd_noise()

        elif self.current == "SS_AOUT1_GAIN_40":
            self.result = self.brd_gain()

        elif self.current == "SS_AOUT1_GAIN_60":
            self.result = self.brd_gain()

        elif self.current == "SS_AOUT1_GAIN_LOW":
            self.result = self.brd_gl()

        elif self.current == "SS_AOUT1_BW":
            self.result = self.brd_bw()

        elif self.current == "SS_ADC1":
            self.result = self.brd_adc()

        elif self.current == "SS_AOUT2_NOISE":
            self.result = self.brd_noise()

        elif self.current == "SS_AOUT2_GAIN_40":
            self.result = self.brd_gain()

        elif self.current == "SS_AOUT2_GAIN_60":
            self.result = self.brd_gain()

        elif self.current == "SS_AOUT2_GAIN_LOW":
            self.result = self.brd_gl()

        elif self.current == "SS_AOUT2_BW":
            self.result = self.brd_bw()

        elif self.current == "SS_ADC2":
            self.result = self.brd_adc()

        return self.result

    def brd_noise(self):
        self.data = []
        self.bus.gen_on(0)
        brd = self.current.split("_")
        self.MUX.set_ch(self.s.join(brd[:2]))
        time.sleep(0.1)
        self.DAC.init(brd[0])
        self.DAC.send_data(brd[0], "DAC_DATA", int(self.DAC.width) << 2)
        self.data = self.bus.read_oneL0()
        self.data = sh.voltage_divider_pre(self.data[0])
        result = sh.rms(self.data)
        self.error = self.check_result(result)
        self.df.loc[0, [self.current]] = [result]
        return self.print_tests(result)

    def brd_gain(self):
        self.data = []
        brd = self.current.split("_")
        self.MUX.set_ch(self.s.join(brd[:2]))
        time.sleep(0.1)
        self.bus.gen_on(1)
        self.DAC.init(brd[0])
        self.bus.set_gen(wave_form="sine", freq=self.F[brd[0]][-1], ampl=0.1)
        self.DAC.send_data(brd[0], "DAC_DATA", self.VCA.vgain(int(brd[-1]), brd[0]))
        self.data = self.bus.read_oneL0()
        self.data = sh.voltage_divider_pre(self.data[0])
        result = sh.rms(self.data)
        result = sh.ratio_db(result, self.vin)
        self.error = self.check_result(result)
        self.df.loc[0, [self.current]] = [result]
        return self.print_tests(result)

    def brd_gl(self):
        self.data = []
        brd = self.current.split("_")
        self.set_gl(brd[0], 1)
        time.sleep(0.2)
        self.data = self.bus.read_oneL0()
        self.data = sh.voltage_divider_pre(self.data[0])
        result = sh.rms(self.data)
        result = sh.ratio_db(result, self.vin)
        self.error = self.check_result(result)
        self.set_gl(brd[0], 0)
        time.sleep(0.2)
        self.df.loc[0, [self.current]] = [result]
        return self.print_tests(result)

    def brd_bw(self):
        self.data = []
        result = []
        brd = self.current.split("_")
        self.MUX.set_ch(self.s.join(brd[:2]))
        time.sleep(0.1)
        self.bus.gen_on(1)
        self.DAC.init(brd[0])
        self.DAC.send_data(brd[0], "DAC_DATA", self.VCA.vgain(60))
        for i, value in enumerate(self.F[brd[0]]):
            self.bus.set_gen(wave_form="sine", freq=value, ampl=0.1)
            time.sleep(0.1)
            self.data = self.bus.read_oneL0()
            self.data = sh.voltage_divider_pre(self.data[0])
            result.append(sh.rms(self.data))
            result[i] = sh.ratio_db(result[i], self.vin)
        self.error = self.check_result(result)
        self.df.loc[0, [self.current]] = [result]
        return self.print_tests(result)

    def brd_adc(self):
        brd = self.current.split("_")
        self.bus.gen_on(0)
        self.DAC.init(brd[0])
        self.DAC.send_data(brd[0], "DAC_DATA", 0x0000)
        time.sleep(0.1)
        for i in range(10):
            result = self.adc.read_data(self.s.join(brd[:2]))
        result = self.adc.code_volt(result)
        self.error = self.check_result(result)
        self.df.loc[0, [self.current]] = [result]
        return self.print_tests(result)

    def check_result(self, result):
        self.error = False
        if self.TEST_result[self.current][0] == ">":
            if abs(result) > self.TEST_result[self.current][1]:
                self.error = True

        if self.TEST_result[self.current][0] == "<":
            if abs(result) < self.TEST_result[self.current][1]:
                self.error = True

        if self.TEST_result[self.current][0] == "%":
            if len(self.TEST_result[self.current]) == 3:
                if (
                    sh.percentage_change(abs(result), self.TEST_result[self.current][2])
                    > self.TEST_result[self.current][1]
                ):
                    self.error = True
            if len(self.TEST_result[self.current]) == 5:
                for count, value in enumerate(result):
                    if (
                        sh.percentage_change(
                            abs(value), self.TEST_result[self.current][count + 2]
                        )
                        > self.TEST_result[self.current][1]
                    ):
                        self.error = True

        if self.TEST_result[self.current][0] == "+-":
            if len(self.TEST_result[self.current]) == 3:
                self.error = sh.checking_width(
                    self.TEST_result[self.current][1],
                    self.TEST_result[self.current][2],
                    abs(result),
                )
            if len(self.TEST_result[self.current]) == 5:
                for count, value in enumerate(result):
                    self.error = sh.checking_width(
                        self.TEST_result[self.current][1],
                        self.TEST_result[self.current][count + 2],
                        abs(value),
                    )

        return self.error

    def set_gl(self, brd, set=0):
        if brd == "ES":
            self.bus.es_gl(set)
        elif brd == "SS":
            self.bus.ss_gl(set)
        return

    def save_log(self):
        self.df.to_csv(
            "dataset/preamp.csv", mode="a", header=False, encoding="utf-8", index=False
        )


if __name__ == "__main__":
    import redpctl as redpctl
    import time, sys

    dec = 1
    rp_c = redpctl.RedCtl(dec=dec)
    # rp_c = redpctl.RedCtl()
    T = TESTs(rp_c,"SS")

    for i in range(32):
        result = T.test()
        if T.error:
            print("error")
            break
        if T.last:
            break

    rp_c.pre_on(0)
    T.save_log()
