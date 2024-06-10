#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
import os
import time
import argcomplete, argparse, configparser
import re
import logging
import traceback

import redpitaya_scpi as scpi
import numpy as np
import scipy
import signal_helper as sh


######################## start: logging #####################################
def addLoggingLevel(levelNum, levelName, methodName=None):
    """
    Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.

    `levelName` becomes an attribute of the `logging` module with the value
    `levelNum`. `methodName` becomes a convenience method for both `logging`
    itself and the class returned by `logging.getLoggerClass()` (usually just
    `logging.Logger`). If `methodName` is not specified, `levelName.lower()`is
    used.

    To avoid accidental clobberings of existing attributes, this method will
    raise an `AttributeError` if the level name is already an attribute of the
    `logging` module or if the method name is already present

    Example
    -------
    >>> addLoggingLevel('TRACE', logging.DEBUG - 5)
    >>> logging.getLogger(__name__).setLevel("TRACE")
    >>> logging.getLogger(__name__).trace('that worked')
    >>> logging.trace('so did this')
    >>> logging.TRACE
    5

    """
    if not methodName:
        methodName = levelName.lower()

    if hasattr(logging, levelName):
        raise AttributeError("{} already defined in logging module".format(levelName))
    if hasattr(logging, methodName):
        raise AttributeError("{} already defined in logging module".format(methodName))
    if hasattr(logging.getLoggerClass(), methodName):
        raise AttributeError("{} already defined in logger class".format(methodName))

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(levelNum):
            self._log(levelNum, message, args, **kwargs)

    def logToRoot(message, *args, **kwargs):
        logging.log(levelNum, message, *args, **kwargs)

    logging.addLevelName(levelNum, levelName)
    setattr(logging, levelName, levelNum)
    setattr(logging.getLoggerClass(), methodName, logForLevel)
    setattr(logging, methodName, logToRoot)


addLoggingLevel(logging.WARN - 5, "NOTE")
addLoggingLevel(logging.INFO - 5, "VERBOSE")
addLoggingLevel(logging.DEBUG - 5, "TRACE")

try:
    import colorlog

    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(asctime)s %(log_color)s%(message)s",
            log_colors={
                "TRACE": "cyan",
                "DEBUG": "cyan",
                "VERBOSE": "",
                "INFO": "",
                "WARNING": "bold_yellow",
                "ERROR": "bold_red",
                "CRITICAL": "bold_red",
            },
        )
    )

except:
    # https://stackoverflow.com/questions/43109355/logging-setlevel-is-being-ignored
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))

log = logging.getLogger(__name__)
log.addHandler(handler)
log.setLevel("INFO")


######################## start: RedCtl ######################################
P_ON_pin = "0"
ES_SS_pin = "1"
DAC_ADC_pin = "2"
ADC1_2_pin = "3"
SS_GL_pin = "4"
ES_GL_pin = "5"
FLG_pin = "7"
RX_pin = "5"
SSRinput_pin = "1"
ESinput_pin = "2"
SSLinput_pin = "3"

class RedCtl:
    """RedPitaya ctrl class
    parameters:
    """
    data = []

    sampleClock = 125e6
    buffSize = 16384  # 2**14

    i2cAddress = None

    waveforms = {}
    waveforms["es"] = {"wave_form": "sine", "freq": 250e3, "ampl": 0.5}
    waveforms["ss"] = {"wave_form": "sine", "freq": 500e3, "ampl": 1}
    waveform_types = waveforms.keys()

    channels = {"ssr": 1, "es": 2, "ssl": 3}
    channel_types = channels.keys()

    def __init__(self, ip="192.168.0.15", trig=0.2, dec=1, ch=1):
        self.ip = ip
        self.rp_s = scpi.scpi(self.ip)
        self.trig_lev = trig
        self.trig_ch = ch

        self.set_dec(dec)

        # self.Nsamples = int(self.fs * self.durationSeconds)

    def init(self):
        log.trace("init()")

        self.rp_s.tx_txt("ACQ:RST")

        # self.rp_s.tx_txt("I2C:FMODE ON")

        self.rp_s.tx_txt("ACQ:DATA:FORMAT ASCII")
        self.rp_s.tx_txt("ACQ:DATA:UNITS VOLTS")
        self.rp_s.tx_txt("ACQ:TRIG:DLY 0")
        self.rp_s.tx_txt("ACQ:TRIG:LEV %d" % self.trig_lev)

    def read(self, quantity=800, counter=50):
        log.trace(f"read(quantity={quantity}, counter={counter})")

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
        log.trace("read_oneL0()")

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
        log.trace("read_now()")

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
        log.trace(f"set_trig(trig_lev={trig_lev},ch={ch})")

        self.trig_lev = trig_lev
        self.trig_ch = ch
        self.rp_s.tx_txt("ACQ:TRIG:LEV %d" % self.trig_lev)

    def set_dec(self, dec=1):
        log.trace(f"set_dec({dec})")

        self.dec = dec
        self.fs = self.sampleClock / self.dec    # sampling frequency
        # self.n=(int)(self.fs/self.fsweep)      # number of datapoints per ramp
        self.buffTime = self.buffSize / self.fs  # Max acquisition time

    def set_gen(self, wave_form="square", freq=500000, ampl=0.5):
        """wave form sine square"""

        log.trace(f"set_gen({wave_form}, {freq}, {ampl})")

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
        log.trace(
            f"set_burst({wave_form}, {freq}, {ampl}, {duration}, {period}, {nor})"
        )

        # wave_form "sine" "square"
        self.rp_s.tx_txt("GEN:RST")
        period = int(period * 1000000)
        ncyc = int(duration * freq)

        self.rp_s.sour_set(
            1, wave_form, ampl, freq, burst=True, ncyc=ncyc, nor=nor, period=period
        )
        self.gen_on(1)
        # self.rp_s.tx_txt("OUTPUT:STATE ON"
        time.sleep(2)
        self.rp_s.tx_txt("SOUR1:TRIG:INT")
        time.sleep(2)
        self.rp_s.tx_txt("SOUR:TRIG:INT")

    def set_ch(self, ch, value=1, pol="N"):
        log.trace(f"set_ch({ch})")

        for i in range(4):
            self.rp_s.tx_txt("DIG:PIN DIO" + str(i) + "_" + pol + "," + str(0))
        if ch != 0:
            self.rp_s.tx_txt("DIG:PIN DIO" + str(ch) + "_" + pol + "," + str(value))

    def set_power(self, value=1):
        log.trace(f"set_power({value})")
        self.rp_s.tx_txt("DIG:PIN DIO" + str(4) + "_N," + str(value))

    def pre_on(self, value=1):
        log.trace(f"pre_on({value})")
        self.rp_s.tx_txt("DIG:PIN DIO" + P_ON_pin + "_N," + str(value))

    def es_ss(self, type="ES"):
        log.trace(f"es_ss({type})")
        if type == "ES":
            value = 0
        else:
            value = 1
        self.rp_s.tx_txt("DIG:PIN DIO" + ES_SS_pin + "_N," + str(value))

    def dac_adc(self, type="DAC"):
        log.trace(f"dac_adc({type})")

        if type == "DAC":
            value = 0
        else:
            value = 1
        self.rp_s.tx_txt("DIG:PIN DIO" + DAC_ADC_pin + "_N," + str(value))

    def adc1_2(self, type="1"):
        log.trace(f"adc1_2({type})")

        if type == "1":
            value = 0
        else:
            value = 1
        self.rp_s.tx_txt("DIG:PIN DIO" + ADC1_2_pin + "_N," + str(value))

    def ss_gl(self, value=1):
        log.trace(f"ss_gl({value})")
        self.rp_s.tx_txt("DIG:PIN DIO" + SS_GL_pin + "_N," + str(value))

    def es_gl(self, value=1):
        log.trace(f"es_gl({value})")
        self.rp_s.tx_txt("DIG:PIN DIO" + ES_GL_pin + "_N," + str(value))

    def rx_on(self, value=1):
        log.trace(f"rx_on({value})")
        self.rp_s.tx_txt("DIG:PIN DIO" + ES_GL_pin + "_N," + str(value))

    def set_dir(self):
        log.trace("set_dir()")

        for i in range(6):
            self.rp_s.tx_txt("DIG:PIN:DIR OUT,DIO" + str(i) + "_N")

    def chirp(self, phi=270, f_min=600000, f_max=1000000, duration=0.00025, ampl=1):
        log.trace(f"chirp({phi}, {f_min}, {f_max}, {duration}, {ampl})")

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
        log.trace(f"gen_on({state})")

        if state == 1:
            self.rp_s.tx_txt("OUTPUT:STATE ON")
        else:
            self.rp_s.tx_txt("OUTPUT:STATE OFF")

    def arbitrary(self, data, duration=0.0001, ch=1, ampl=1):
        log.trace(f"arbitrary({data}, {duration}, {ch}, {ampl})")

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
        self.rp_s.tx_txt(
            ("SOUR1:TRAC:DATA:DATA " + waveform_ch_1).replace("1", str(ch), 1)
        )
        self.rp_s.tx_txt(("SOUR1:FREQ:FIX " + str(freq)).replace("1", str(ch), 1))
        self.rp_s.tx_txt(("SOUR1:VOLT " + str(ampl)).replace("1", str(ch), 1))
        # self.rp_s.tx_txt("OUTPUT1:STATE ON")
        self.rp_s.tx_txt("SOUR:TRIG:INT")
        return

    def read_byte_data(self, i2cAddress=32, reg=0):
        log.trace(f"read_byte_data({i2cAddress}, {reg})")

        self.set_i2cAddress(i2cAddress)
        self.rp_s.tx_txt("I2C:Smbus:Read%d?" % reg)
        value = self.rp_s.rx_txt()
        value = int(value)
        return value

    def write_byte_data(self, i2cAddress=32, reg=0, regValue=0):
        log.trace(f"write_byte_data({i2cAddress}, {reg}, {regValue})")

        self.rp_s.tx_txt("I2C:Smbus:Write" + str(reg) + " " + str(regValue))

    def write_byte_data_b(self, i2cAddress=32, reg=0, regValue=0):
        self.rp_s.tx_txt("I2C:IO:W:B1 " + str(regValue))

    def set_i2cAddress(self, i2cAddress):
        log.trace(f"set_i2cAddress({i2cAddress})")

        self.rp_s.tx_txt('I2C:DEV%d "/dev/i2c-0"' % i2cAddress)
        self.rp_s.tx_txt("I2C:FMODE ON")

    def spi_init(self):
        log.trace("spi_init()")

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
        log.trace(f"spi_csmode({mode})")

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
        log.trace(f"spi_mode({mode})")

        self.rp_s.tx_txt("SPI:SET:MODE " + mode)
        self.rp_s.tx_txt("SPI:SET:SET")
        return

    def send_spi_msc(self, msg):
        log.trace(f"send_spi_msc({msg})")

        # self.rp_s.tx_txt("SPI:MSG:CREATE 1")
        self.rp_s.tx_txt("SPI:MSG0:TX3 " + msg)
        self.rp_s.tx_txt("SPI:PASS")
        # self.rp_s.tx_txt("SPI:MSG:DEL")
        return

    def send_spi_msc1(self, msg):
        log.trace(f"send_spi_msc1({msg})")

        # self.rp_s.tx_txt("SPI:MSG:CREATE 1")
        self.rp_s.tx_txt("SPI:MSG0:TX1 " + msg)
        self.rp_s.tx_txt("SPI:PASS")
        # self.rp_s.tx_txt("SPI:MSG:DEL")
        return

    def read_spi_msc(self):
        log.trace(f"read_spi_msc()")

        self.rp_s.tx_txt("SPI:MSG0:RX3")
        self.rp_s.tx_txt("SPI:PASS")
        self.rp_s.tx_txt("SPI:MSG0:RX?")
        data = self.rp_s.rx_txt()
        return data

    def spi_release(self):
        log.trace(f"spi_release()")

        self.rp_s.tx_txt("SPI:MSG:DEL")
        self.rp_s.tx_txt("SPI:RELEASE")
        return

    def select_spi(self, ch="ES_DAC"):
        log.trace(f"select_spi({ch})")

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


######################## start: utils #####################################
def human_size(bytes, units=["", "Kb", "Mb", "Gb", "Tb", "Pb", "Eb"]):
    """Returns a human readable string representation of bytes"""
    if isinstance(bytes, (int, float)):
        return (
            "({:.0f}{})".format(bytes, units[0])
            if bytes < 1024
            else human_size(bytes / 1024, units[1:])
        )
    else:
        return "(" + str(bytes) + "b)"


def str2bool(str: str):
    if str.lower() in ["true", "1", "yes", "on", "enable", "enabled"]:
        return 1
    if str.lower() in ["false", "0", "no", "off", "disable", "disabled"]:
        return 0
    raise TypeError(f'"{str}" should be boolean-like string')


######################## end: utils #######################################

######################## start: setup command line commands ###############
setup_argparse_subparsers = []


###### command 'init' ######
def do_init(args):
    redpctl, args = args
    redpctl.init()


def setup_argparse_init(cmd_subparser):
    parser = cmd_subparser.add_parser(
        "init",
        description="RedPitaya initialization",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.set_defaults(func=do_init)

    return parser


setup_argparse_subparsers.append({"callback": setup_argparse_init})


###### command 'power' ######
def do_power(args):
    redpctl, args = args
    on_off = str2bool(args.on_off[0])
    redpctl.set_power(on_off)


def setup_argparse_power(cmd_subparser):
    parser = cmd_subparser.add_parser(
        "power",
        description="testbed power on/off",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.set_defaults(func=do_power)
    parser.add_argument("on_off", type=str, nargs=1, help="testbed power on/off")

    return parser


setup_argparse_subparsers.append({"callback": setup_argparse_power})


###### command 'generator' ######
def do_generator_power(args):
    redpctl, args = args

    on_off = str2bool(args.on_off[0])
    redpctl.gen_on(on_off)


def do_generator_waveform(args):
    redpctl, args = args
    redpctl.set_ch(0)

    kwargs = redpctl.waveforms.get(args.waveform_type)
    redpctl.set_gen(**kwargs)


def setup_argparse_generator(cmd_subparser):
    parser = cmd_subparser.add_parser(
        "generator",
        aliases=["gen"],
        description="RedPitaya generator control",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    subparser = parser.add_subparsers(
        title="RedPitaya control functions", required=True
    )
    parser = subparser.add_parser(
        "power",
        description="Testbed power on/off",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="produce more verbose output"
    )
    parser.add_argument("on_off", type=str, nargs=1, help="on/off")
    parser.set_defaults(func=do_generator_power)

    parser = subparser.add_parser(
        "waveform",
        description="Generate waveform",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "waveform_type",
        choices=RedCtl.waveform_types,
        help="Generate predefined waveform",
    )
    parser.set_defaults(func=do_generator_waveform)

    return parser


setup_argparse_subparsers.append({"callback": setup_argparse_generator})


###### command 'relay' ######
def do_relay(args):
    redpctl, args = args
    on_off = str2bool(args.on_off[0])
    redpctl.rx_on(on_off)


def setup_argparse_relay(cmd_subparser):
    parser = cmd_subparser.add_parser(
        "relay",
        description="testbed relay on/off",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.set_defaults(func=do_relay)
    parser.add_argument("on_off", type=str, nargs=1, help="testbed relay on/off")

    return parser


setup_argparse_subparsers.append({"callback": setup_argparse_relay})


###### command 'tx-test' ######
def do_tx_test(args):
    redpctl, args = args

    ch = redpctl.channels[args.channel]
    redpctl.set_dec(128)
    redpctl.set_trig(trig_lev=0.065, ch=1)

    print(f"======== test channel {args.channel} ========")
    redpctl.set_ch(ch)
    thresh_level = 0.045
    cnt = 0
    sub = 0.0
    time.sleep(0.1)
    while True:
        data = redpctl.read(counter=1, quantity=16384)
        data = np.array(data)
        real_current = np.real(sh.CQ_330E(voltage=data[1]))
        real_voltage = np.real(sh.voltage_divider_KV(ch, data[0]))
        sub = np.abs(np.mean(real_voltage))
        # print(f"sub: {sub:.2f}")
        cnt += 1
        if sub >= thresh_level:
            break
        if cnt == 20:
            break

    try:
        rising_edge, falling_edge = sh.x_edge(real_voltage, thresh=20)
        voltage_period = real_voltage[rising_edge[0] : rising_edge[-1]]
        current_period = real_current[rising_edge[0] : rising_edge[-1]]
    except Exception as e:
        print(f"Something went wrong: {e}")
        return

    max_current = np.max(current_period)
    max_voltage = np.max(voltage_period)
    min_voltage = np.min(voltage_period)
    peak_to_peak = max_voltage - min_voltage
    num_points = len(voltage_period)
    duration = num_points / redpctl.fs
    duration_milliseconds = duration * 1000

    print(f"{args.channel:3s} | Voltage      | V  | {max_voltage:.2f}")
    print(f"{args.channel:3s} | Max current  | A  | {max_current:.2f}")
    print(f"{args.channel:3s} | Peak to Peak | A  | {peak_to_peak:.2f}")
    print(f"{args.channel:3s} | Duration     | ms | {duration_milliseconds:.3f}")
    # redpctl.set_ch(0)


def setup_argparse_tx_test(cmd_subparser):
    parser = cmd_subparser.add_parser(
        "tx_test",
        description="read send evosonar tx and measure it",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.set_defaults(func=do_tx_test)
    parser.add_argument("channel", choices=RedCtl.channel_types, help="channel name")

    return parser


setup_argparse_subparsers.append({"callback": setup_argparse_tx_test})


def main():

    prog = os.path.splitext(os.path.basename(__file__))[0]
    configs_names = [prog + ".ini"]

    config_paths = ["/etc/", "/usr/local/etc/", "/opt/etc/", os.environ["HOME"] + "/."]
    configs = []
    for path in config_paths:
        for config_name in configs_names:
            configs.append(path + config_name)

    # argparse.ArgumentDefaultsHelpFormatter did't work for some reason
    # Added to each help' (default: %(default)s)'
    cmd_parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    cmd_subparser = cmd_parser.add_subparsers(
        title="commands",
        dest="command",
        required=True,
        help="Commands. Add --help to see help",
    )

    config = configparser.ConfigParser()

    defaults = {}
    for config_name in configs:
        if not os.path.exists(config_name):
            continue
        config.read(config_name)
        defaults.update(dict(config.items("defaults")))

    cmd_parser.set_defaults(**defaults)
    for subparser in setup_argparse_subparsers:
        parser = subparser["callback"](cmd_subparser)
        parser.add_argument(
            "-v",
            "--verbose",
            action="count",
            default=0,
            help="produce more verbose output",
        )
        parser.set_defaults(**defaults)

    argcomplete.autocomplete(parser)
    args = cmd_parser.parse_args()  # Overwrite arguments

    if not hasattr(args, "verbose"):
        args.verbose = 0

    # TODO: add -l, --loglevel flag and config option
    # then code for syncronization --loglevel and --verbose
    # will be meaningful.
    # but now this hack -_-
    args.loglevel_base = logging.NOTE
    args.loglevel = args.loglevel_base
    if args.verbose > 4:
        args.verbose = 4

    # 5 is steps between loglevels
    if args.loglevel > args.loglevel_base and args.verbose == 0:
        args.verbose = int(args.loglevel - args.loglevel_base / 5)

    args.loglevel = args.loglevel_base - args.verbose * 5
    log.setLevel(args.loglevel)

    redpctl = RedCtl(dec=32)

    # TODO: move to __init__
    redpctl.loglevel_base = args.loglevel_base

    rc = 0
    try:
        args.func([redpctl, args])
    except Exception as e:
        if args.verbose:
            log.critical(traceback.format_exc())
        else:
            log.critical(str(e))
        rc = 1

    exit(rc)

if __name__ == "__main__":
    main()
