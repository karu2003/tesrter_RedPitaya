#!/usr/bin/python3

import sys
import time
import numpy as np
import signal_helper as sh

class LTC6912:
    def __init__(self, bus):
        self.bus = bus
        self.GAIN_dB =  ["-120",  "0",  "6", "12", "18.1", "24.1", "30.1", "36.1", "-12x"]
        self.GAIN_HEX = [  0x00, 0x11, 0x22, 0x33,   0x44,   0x55,   0x66,   0x77,   0x88]
        self.bus.spi_mode("HIST")
        # self.GAIN = {self.GAIN_dB[i]: self.GAIN_HEX[i] for i in range(len(self.GAIN_dB))}
        self.GAIN = dict(map(lambda i,j : (i,j) , self.GAIN_dB,self.GAIN_HEX))

    def send_8bit_int(self, i):
        self.bus.send_spi_msc1(msg=str(i))
        time.sleep(0.2)
        self.bus.send_spi_msc1(msg=str(i))
        time.sleep(0.2)
        return
    
    def test_db(self,vin):
        result_dict = {}
        for k, v in self.GAIN.items():
            if k in ("0","6", "12", "18.1", "24.1", "30.1"):
                print("Gain db",k)
                self.send_8bit_int(v)
                data = self.read_same_level()
                result = sh.rms(data)
                result = sh.ratio_db(result, vin)
                if k in ("6", "12", "18.1", "24.1", "30.1"):
                    result_dict[k] = round(sh.rms(data), 3)
        return result_dict
    
    def read_same_level(self, thresh = 0.01, slice = 100):
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
            sub = round(abs(max_start-max_ende),3)
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
    att_loss = 30.
    ATT.set_loss(int(att_loss))
    brd_ch = ["ES_LIM", "ES_MAIN"]
    lowcut = 3e5

    F = [26000., 60000., 150000.]
    brd = ["18", "40", "HS"]

    ampl = 0.07
    vin = ((ampl / np.sqrt(2))/ sh.db_ratio(40))/sh.db_ratio(att_loss)

    MUX.set_ch("ES_LIM")
    time.sleep(0.1) 
    rp_c.gen_on(1)
    rp_c.adc1_2(1)
    rp_c.ss_gl(0)
    rp_c.pre_on(1)


    rp_c.set_gen(wave_form="sine", freq=F[2], ampl=ampl)
    time.sleep(0.5)

    data = AMP.read_same_level(thresh = 0.05, slice = 100)
    rms90 = sh.rms(data)
    ratio90= sh.ratio_db(rms90,vin)
    print(ratio90)
    fw = 56000.0

    while 1:
        print(fw)
        rp_c.set_gen(wave_form="sine", freq=fw, ampl=ampl)
        time.sleep(0.5)
        data = AMP.read_same_level(thresh = 0.05, slice = 100)
        rms = sh.rms(data)
        ratio = sh.ratio_db(rms,vin)
        print("ratio",ratio)
        sub = ratio90 - ratio
        print(sub)
        error = sh.checking_width(0.1, 3, abs(sub))
        if not error:
            break
        print(error)
        fw += 100



    # rp_c.pre_on(0)
