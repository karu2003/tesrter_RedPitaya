# control digital step Attenuator DAT-31R5A+ over i2C MCP23008

import redpctl as redpctl
import time

MCP23008_REG_IODIR = 0  # I/O DIRECTION Register
MCP23008_REG_IOCON = 5  # I/O EXPANDER CONFIGURATION Register
MCP23008_REG_GPIO = 9  # GENERAL PURPOSE I/O PORT Register


class Attenuator:
    def __init__(self, bus):
        self.bus = bus
        self.i2cAddress = 0x20
        self.set_i2c_Address()
        self.LE = 64
        self.bus.write_byte_data(reg=MCP23008_REG_IODIR, regValue=0)  # all output
        self.loss = {
            "0db": 0,
            "0.5db": 1,
            "1db": 2,
            "2db": 4,
            "4db": 8,
            "8db": 16,
            "16db": 32,
            "31.5db": 63,
        }

    def set_loss(self, loss):
        self.set_i2c_Address()
        if loss in self.loss:
            value = self.loss[loss]
        else:
            value = loss & 63
        value_LE = value | self.LE
        self.bus.write_byte_data(reg=MCP23008_REG_GPIO, regValue=value)
        self.bus.write_byte_data(reg=MCP23008_REG_GPIO, regValue=value_LE)
        self.bus.write_byte_data(reg=MCP23008_REG_GPIO, regValue=value)
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
    ATT = Attenuator(rp_c)
    for i in ATT.loss.keys():
        print(i)
        ATT.set_loss(i)
        time.sleep(1)

    ATT.set_loss("0db")
    time.sleep(3)
    ATT.set_loss(10)
