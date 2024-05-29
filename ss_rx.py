if __name__ == "__main__":
    import redpctl as redpctl
    import time, sys
    import signal_helper as sh
    import numpy as np
    import matplotlib.pyplot as plt

    dec = 32
    rp_c = redpctl.RedCtl(dec=dec)
    frequencies = [250e3, 500e3]
    rp_c.gen_on(1)
    # Power on
    rp_c.set_power(1)
    # turn on the RX relay

    # rename rx_on to rx_relay_on
    rp_c.rx_on(1)
    rp_c.set_ch(0)

    while True:
        try:
            rp_c.set_gen(wave_form="sine", freq=frequencies[0], ampl=0.5)
            time.sleep(10)
            rp_c.set_gen(wave_form="sine", freq=frequencies[1], ampl=1.0)
            time.sleep(10)

        except KeyboardInterrupt:
            # turn off the RX relay
            rp_c.rx_on(0)
            # Power off
            rp_c.set_power(0)
            break
