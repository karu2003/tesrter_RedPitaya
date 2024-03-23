import time, sys


class ADC:
    def __init__(self, bus):
        self.bus = bus
        self.width = 0x3FFF
        self.bus.pre_on(1)
        self.vref = 3
        self.adc_lsb = self.vref / self.width

    def read_24bit_int(self):
        data = self.bus.read_spi_msc()
        data = data.translate({ord(i): None for i in "{}"}).split(",")
        data = int(data[0]) << 8 | int(data[1])
        return data >> 1

    def read_data(self, brd="SS_ADC1"):
        self.bus.select_spi(brd)
        time.sleep(0.1)
        data = self.read_24bit_int()
        return data

    def code_volt(self, code):
        return code * self.adc_lsb


if __name__ == "__main__":
    import redpctl as redpctl
    import time, sys
    from DAC70501 import DAC70501

    brd = ["SS_ADC1", "SS_ADC2"]
    dec = 16
    rp_c = redpctl.RedCtl(dec=dec)
    DAC = DAC70501(rp_c)
    DAC.send_data("SS", "DAC_DATA", 0x0000)
    adc = ADC(rp_c)
    for i in brd:
        data = adc.read_data(i)
        print(hex(data))
        print(adc.code_volt(data))
