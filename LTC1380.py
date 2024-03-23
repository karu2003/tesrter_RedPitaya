# control digital step Attenuator DAT-31R5A+ over i2C MCP23008

import redpctl as redpctl
import time


class LTC1380:
    def __init__(self, bus):
        self.bus = bus
        self.ON = 8
        self.i2cAddress = 0x48
        self.set_i2c_Address()

        CH_name = [
            "ES_VGAIN",
            "ES_LIM",
            "ES_MAIN",
            "SS_VGAIN",
            "SS_AOUT1",
            "SS_AOUT2",
            "S6",
            "S7",
        ]
        self.CH = {}
        for i, text in enumerate(CH_name):
            self.CH[text] = i

    def set_ch(self, ch):
        self.set_i2c_Address()
        value = self.CH[ch]
        value |= self.ON
        self.bus.write_byte_data_b(reg=0, regValue=value)
        return

    def ch_off(self):
        self.bus.write_byte_data_b(reg=0, regValue=0)
        return

    def set_i2c_Address(self):
        if self.bus.i2cAddress != self.i2cAddress:
            self.bus.i2cAddress = self.i2cAddress
            self.bus.set_i2cAddress(self.i2cAddress)
            time.sleep(0.1)
        return


if __name__ == "__main__":
    import redpctl as redpctl
    import time, sys

    rp_c = redpctl.RedCtl()
    MUX = LTC1380(rp_c)

    for i in MUX.CH.keys():
        print(i)
        MUX.set_ch(i)
        time.sleep(1)

    MUX.set_ch("ES_VGAIN")
