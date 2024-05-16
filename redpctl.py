import redpitaya_scpi as scpi
import numpy as np
import time
import scipy
import signal_helper as sh

P_ON_pin = "0"
ES_SS_pin = "1"
DAC_ADC_pin = "2"
ADC1_2_pin = "3"
SS_GL_pin = "4"
ES_GL_pin = "5"
FLG_pin = "7"


class RedCtl:
    """RedPitaya ctrl class
    parameters:
    """

    def __init__(self, ip="192.168.0.15", trig=0.2, dec=1, ch=1):

        self.data = []
        self.ip = ip
        self.rp_s = scpi.scpi(self.ip)
        self.trig_lev = trig
        self.trig_ch = ch
        self.dec = dec
        sampleClock = 125e6
        self.buffSize = 16384  # 2**14
        self.fs = sampleClock / self.dec  # sampling frequency
        # self.n=(int)(self.fs/self.fsweep)      # number of datapoints per ramp
        self.buffTime = self.buffSize / self.fs  # Max acquisition time
        # self.Nsamples = int(self.fs * self.durationSeconds)
        self.i2cAddress = None
        self.rp_s.tx_txt("DIG:RST")
        self.rp_s.tx_txt("ACQ:RST")

        self.spi_init()
        self.set_dir()

        # self.rp_s.tx_txt("I2C:FMODE ON")

        self.rp_s.tx_txt("ACQ:DATA:FORMAT ASCII")
        self.rp_s.tx_txt("ACQ:DATA:UNITS VOLTS")
        self.rp_s.tx_txt("ACQ:TRIG:DLY 0")
        self.rp_s.tx_txt("ACQ:TRIG:LEV %d" % self.trig_lev)

    def read(self, quantity=800, counter=50):

        self.data.clear()
        self.rp_s.tx_txt("ACQ:DEC %d" % self.dec)

        self.rp_s.tx_txt("ACQ:START")
        time.sleep(0.05)
        self.rp_s.tx_txt("ACQ:TRIG CH%d_PE" % self.trig_ch)

        for i in range(counter):

            while 1:
                self.rp_s.tx_txt("ACQ:TRIG:STAT?")
                if self.rp_s.rx_txt() == "TD":
                    break

            while 1:
                self.rp_s.tx_txt("ACQ:TRIG:FILL?")
                if self.rp_s.rx_txt() == "1":
                    break

            self.rp_s.tx_txt("ACQ:SOUR1:DATA:OLD:N? " + str(quantity))

            buff_string = self.rp_s.rx_txt()
            buff_string = buff_string.strip("{}\n\r").replace("  ", "").split(",")
            buff = list(map(float, buff_string))
            arr = np.array(buff)
            self.data.append(arr)

            self.rp_s.tx_txt("ACQ:SOUR2:DATA:OLD:N? " + str(quantity))

            buff_string = self.rp_s.rx_txt()
            buff_string = buff_string.strip("{}\n\r").replace("  ", "").split(",")
            buff = list(map(float, buff_string))
            arr = np.array(buff)
            self.data.append(arr)

            # data = np.append(data,np.array(buff))
            self.rp_s.tx_txt("ACQ:STOP")

        return self.data

    def read_oneL0(self):

        self.data.clear()
        self.rp_s.tx_txt("ACQ:DEC %d" % self.dec)
        # self.set_trig(trig_lev=0, ch=self.trig_ch)
        self.rp_s.tx_txt("ACQ:START")
        self.rp_s.tx_txt("ACQ:TRIG NOW")
        # self.rp_s.tx_txt("ACQ:TRIG CH%d_PE" % self.trig_ch)

        while 1:
            self.rp_s.tx_txt("ACQ:TRIG:STAT?")
            if self.rp_s.rx_txt() == "TD":
                break

        while 1:
            self.rp_s.tx_txt("ACQ:TRIG:FILL?")
            if self.rp_s.rx_txt() == "1":
                break

        buff = self.rp_s.acq_data(1, old=True, num_samples=16384 / 3, convert=True)
        # self.rp_s.tx_txt("ACQ:SOUR1:DATA?")
        # # self.rp_s.tx_txt("ACQ:SOUR1:DATA:OLD:N? 16384")
        # buff_string = self.rp_s.rx_txt()
        # buff_string = buff_string.strip("{}\n\r").replace("  ", "").split(",")
        # buff = list(map(float, buff_string))
        arr = np.array(buff)
        self.data.append(arr)
        self.rp_s.tx_txt("ACQ:STOP")
        return self.data

    def read_now(self):

        self.data.clear()
        self.rp_s.tx_txt("ACQ:DEC %d" % self.dec)
        self.rp_s.tx_txt("ACQ:START")
        self.rp_s.tx_txt("ACQ:TRIG NOW")

        while 1:
            self.rp_s.tx_txt("ACQ:TRIG:STAT?")
            if self.rp_s.rx_txt() == "TD":
                break

        while 1:
            self.rp_s.tx_txt("ACQ:TRIG:FILL?")
            if self.rp_s.rx_txt() == "1":
                break

        buff = self.rp_s.acq_data(1, old=False, num_samples=16384, convert=True)
        arr = np.array(buff)
        self.data.append(arr)
        self.rp_s.tx_txt("ACQ:STOP")
        return self.data

    def set_trig(self, trig_lev=0.2, ch=1):
        self.trig_lev = trig_lev
        self.trig_ch = ch
        self.rp_s.tx_txt("ACQ:TRIG:LEV %d" % self.trig_lev)

    def set_dec(self, dec=1):
        self.dec = dec

    def set_gen(self, wave_form="square", freq=500000, ampl=0.5):
        """ wave form sine square """
        self.rp_s.tx_txt("GEN:RST")
        self.rp_s.sour_set(1, wave_form, ampl, freq)
        self.rp_s.tx_txt("OUTPUT1:STATE ON")
        self.rp_s.tx_txt("SOUR1:TRIG:INT")
        # self.rp_s.close()

    def set_burst(
        self,
        wave_form="square",
        freq=500000,
        ampl=1.0,
        duration=0.001,
        period=0.500,
        nor=65536,
    ):
        # wave_form "sine" "square"
        self.rp_s.tx_txt("GEN:RST")
        period = int(period * 1000000)
        ncyc = int(duration * freq)

        self.rp_s.sour_set(
            1, wave_form, ampl, freq, burst=True, ncyc=ncyc, nor=nor, period=period
        )
        self.gen_on(1)
        # self.rp_s.tx_txt("OUTPUT:STATE ON")
        time.sleep(2)
        self.rp_s.tx_txt("SOUR1:TRIG:INT")
        time.sleep(2)
        self.rp_s.tx_txt("SOUR:TRIG:INT")

    def set_ch(self, ch, value=1, pol="N"):
        for i in range(4):
            self.rp_s.tx_txt("DIG:PIN DIO" + str(i) + "_" + pol + "," + str(0))
        if ch != 0:
            self.rp_s.tx_txt("DIG:PIN DIO" + str(ch) + "_" + pol + "," + str(value))

    def set_power(self, value=1):
        self.rp_s.tx_txt("DIG:PIN DIO" + str(4) + "_N," + str(value))

    def pre_on(self, value=1):
        self.rp_s.tx_txt("DIG:PIN DIO" + P_ON_pin + "_N," + str(value))

    def es_ss(self, type="ES"):
        if type == "ES":
            value = 0
        else:
            value = 1
        self.rp_s.tx_txt("DIG:PIN DIO" + ES_SS_pin + "_N," + str(value))

    def dac_adc(self, type="DAC"):
        if type == "DAC":
            value = 0
        else:
            value = 1
        self.rp_s.tx_txt("DIG:PIN DIO" + DAC_ADC_pin + "_N," + str(value))

    def adc1_2(self, type="1"):
        if type == "1":
            value = 0
        else:
            value = 1
        self.rp_s.tx_txt("DIG:PIN DIO" + ADC1_2_pin + "_N," + str(value))

    def ss_gl(self, value=1):
        self.rp_s.tx_txt("DIG:PIN DIO" + SS_GL_pin + "_N," + str(value))

    def es_gl(self, value=1):
        self.rp_s.tx_txt("DIG:PIN DIO" + ES_GL_pin + "_N," + str(value))

    def set_dir(self):
        for i in range(6):
            self.rp_s.tx_txt("DIG:PIN:DIR OUT,DIO" + str(i) + "_N")

    def chirp(self, phi=270, f_min=600000, f_max=1000000, duration=0.00025, ampl=1):
        wave_form = "arbitrary"
        buffer = 16384
        _, x0 = sh.chirp_l(
            buffer=buffer,
            phi=phi,
            f_min=f_min,
            f_max=f_max,
            duration=duration,
            ampl=ampl,
        )
        self.rp_s.tx_txt("GEN:RST")
        self.rp_s.sour_set(1, wave_form, ampl, 1 / duration, data=x0)
        self.gen_on(1)
        # self.rp_s.tx_txt("OUTPUT:STATE ON")
        self.rp_s.tx_txt("SOUR:TRIG:INT")
        return

    def gen_on(self, state=1):
        if state == 1:
            self.rp_s.tx_txt("OUTPUT:STATE ON")
        else:
            self.rp_s.tx_txt("OUTPUT:STATE OFF")

    def arbitrary(self, data, duration=0.0001, ch=1, ampl=1):
        freq = 1 / duration
        waveform_ch_10 = []
        for n in data:
            waveform_ch_10.append(f"{n:.5f}")
        waveform_ch_1 = ", ".join(map(str, waveform_ch_10))
        # z = ''
        self.rp_s.tx_txt("GEN:RST")
        # for i, text in enumerate(data):
        #     z += str(text) + ', '
        self.rp_s.tx_txt(("SOUR1:FUNC ARBITRARY").replace("1", str(ch), 1))
        self.rp_s.tx_txt(("SOUR1:TRAC:DATA:DATA " + waveform_ch_1).replace("1", str(ch), 1))
        self.rp_s.tx_txt(("SOUR1:FREQ:FIX " + str(freq)).replace("1", str(ch), 1))
        self.rp_s.tx_txt(("SOUR1:VOLT " + str(ampl)).replace("1", str(ch), 1))
        # self.rp_s.tx_txt("OUTPUT1:STATE ON")
        self.rp_s.tx_txt("SOUR:TRIG:INT")
        return

    def read_byte_data(self, i2cAddress=32, reg=0):
        self.set_i2cAddress(i2cAddress)
        self.rp_s.tx_txt("I2C:Smbus:Read%d?" % reg)
        value = self.rp_s.rx_txt()
        value = int(value)
        return value

    def write_byte_data(self, i2cAddress=32, reg=0, regValue=0):
        self.rp_s.tx_txt("I2C:Smbus:Write" + str(reg) + " " + str(regValue))
        return

    def write_byte_data_b(self, i2cAddress=32, reg=0, regValue=0):
        self.rp_s.tx_txt("I2C:IO:W:B1 " + str(regValue))
        return

    def set_i2cAddress(self, i2cAddress):
        self.rp_s.tx_txt('I2C:DEV%d "/dev/i2c-0"' % i2cAddress)
        self.rp_s.tx_txt("I2C:FMODE ON")
        return

    def spi_init(self):
        self.rp_s.tx_txt("SPI:INIT")
        self.rp_s.tx_txt('SPI:INIT:DEV "/dev/spidev1.0"')
        self.rp_s.tx_txt("SPI:SET:DEF")
        self.rp_s.tx_txt("SPI:SET:MODE HISL")  # HISL LIST
        self.rp_s.tx_txt("SPI:SET:CSMODE NORMAL")
        self.rp_s.tx_txt("SPI:SET:SPEED 250000")
        self.rp_s.tx_txt("SPI:SET:WORD 8")
        self.rp_s.tx_txt("SPI:SET:SET")
        self.rp_s.tx_txt("SPI:MSG:CREATE 1")
        return

    def spi_csmode(self, mode):
        print("SPI:SET:CSMODE " + mode)
        self.rp_s.tx_txt("SPI:SET:CSMODE " + mode)
        self.rp_s.tx_txt("SPI:SET:SET")
        return

    def spi_mode(self, mode):
        """
        - LISL = Low idle level, Sample on leading edge
        - LIST = Low idle level, Sample on trailing edge
        - HISL = High idle level, Sample on leading edge
        - HIST = High idle level, Sample on trailing edge
        """
        self.rp_s.tx_txt("SPI:SET:MODE " + mode)
        self.rp_s.tx_txt("SPI:SET:SET")
        return

    def send_spi_msc(self, msg):
        # self.rp_s.tx_txt("SPI:MSG:CREATE 1")
        self.rp_s.tx_txt("SPI:MSG0:TX3 " + msg)
        self.rp_s.tx_txt("SPI:PASS")
        # self.rp_s.tx_txt("SPI:MSG:DEL")
        return

    def send_spi_msc1(self, msg):
        # self.rp_s.tx_txt("SPI:MSG:CREATE 1")
        self.rp_s.tx_txt("SPI:MSG0:TX1 " + msg)
        self.rp_s.tx_txt("SPI:PASS")
        # self.rp_s.tx_txt("SPI:MSG:DEL")
        return

    def read_spi_msc(self):
        self.rp_s.tx_txt("SPI:MSG0:RX3")
        self.rp_s.tx_txt("SPI:PASS")
        self.rp_s.tx_txt("SPI:MSG0:RX?")
        data = self.rp_s.rx_txt()
        return data

    def spi_release(self):
        self.rp_s.tx_txt("SPI:MSG:DEL")
        self.rp_s.tx_txt("SPI:RELEASE")
        return

    def select_spi(self, ch="ES_DAC"):
        if ch == "ES_DAC":
            self.es_ss("ES")
            self.dac_adc("DAC")
            self.adc1_2("1")
        elif ch == "SS_DAC":
            self.es_ss("SS")
            self.dac_adc("DAC")
            self.adc1_2("1")
        elif ch == "SS_ADC1":
            self.es_ss("SS")
            self.dac_adc("ADC")
            self.adc1_2("1")
        elif ch == "SS_ADC2":
            self.es_ss("SS")
            self.dac_adc("ADC")
            self.adc1_2("2")
        return
