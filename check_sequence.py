if __name__ == "__main__":
    import redpctl as redpctl
    import time, sys
    import signal_helper as sh
    import numpy as np
    import matplotlib.pyplot as plt
    import pandas as pd


    dec = 32
    rp_c = redpctl.RedCtl(dec=dec)
    sample_rate = rp_c.fs
    buffTime = rp_c.buffTime
    duration = buffTime/2
    # duration = 0.0001
    ampl=0.5

    print(f"Sample rate: {sample_rate}, Buffer time: {buffTime} , Duration: {duration}")
    frequencies = [250e3, 500e3]
    t, signal = sh.gen_signals_sequence(frequencies, duration=duration, sample_rate=sample_rate)
    rp_c.gen_on(1)

    # rp_c.arbitrary(signal, duration=buffTime,ch=1, ampl=0.5)

    # for i in range(2):
    #     rp_c.set_gen(wave_form="sine", freq=frequencies[i], ampl=ampl)
    #     time.sleep(0.5)

    # rp_c.set_gen(wave_form="sine", freq=frequencies[1], ampl=0.5)
    # rp_c.gen_on(1)

    wave_form = "arbitrary"
    rp_c.rp_s.tx_txt("GEN:RST")
    rp_c.rp_s.sour_set(2, wave_form, ampl, 1 / buffTime, data=signal)
    rp_c.gen_on(1)
    rp_c.rp_s.tx_txt("OUTPUT:STATE ON")
    rp_c.rp_s.tx_txt("SOUR:TRIG:INT")

    plt.figure(figsize=(10, 4))
    plt.plot(t, signal)
    plt.title('Signal')
    plt.xlabel('Time')
    plt.ylabel('Amplitude')
    plt.grid(True)
    plt.show()

    # pd.DataFrame(signal).to_csv('arb_waveform1.csv', index=False, header=False, float_format=np.float64)

