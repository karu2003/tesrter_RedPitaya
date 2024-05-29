if __name__ == "__main__":
    import redpctl as redpctl
    import time, sys
    import signal_helper as sh
    import numpy as np
    import matplotlib.pyplot as plt

    dec = 128
    rx_buffer_size = 16384
    nrows = 1
    thresh = 0.065
    rp_c = redpctl.RedCtl(dec=dec, trig=thresh)
    rp_c.set_power(1)

    # IMPORTANT!!!! for TX test RX relay should be OFF
    # turn off the RX relay
    rp_c.rx_on(0)
    rp_c.set_ch(0)
    sample_rate = rp_c.fs

    channel_dict = {"SSR": 1, "SSL": 3, "ES": 2}

    while True:
        try:
            for key, value in channel_dict.items():
                print(f"turn channel {key}")
                rp_c.set_ch(value)
                time.sleep(0.1)
                data = rp_c.read(counter=nrows, quantity=rx_buffer_size)
                data = np.array(data)
                real_current = np.real(sh.CQ_330E(voltage=data[1]))
                real_voltage = np.real(sh.voltage_divider_KV(value, data[0]))

                try:
                    rising_edge, falling_edge = sh.x_edge(real_voltage, thresh=30)
                    voltage_period = real_voltage[rising_edge[0] : rising_edge[-1]]
                    current_period = real_current[rising_edge[0] : rising_edge[-1]]
                except:
                    print("Something went wrong.")
                    continue

                max_current = np.max(current_period)
                print(f"Max current: {max_current:.2f}")
                max_voltage = np.max(voltage_period)
                min_voltage = np.min(voltage_period)
                peak_to_peak = max_voltage - min_voltage
                num_points = len(voltage_period)
                duration = num_points / sample_rate
                duration_milliseconds = duration * 1000

                print(f"Duration: {duration_milliseconds} mS")
                print(
                    f"Voltage +-: {max_voltage:.2f} on channel {key} and PP: {peak_to_peak:.2f}"
                )

                # fig, (ax1, ax2) = plt.subplots(2, 1)
                # ax1.plot(voltage_period)
                # ax1.set_title("Voltage channel " + key)

                # ax2.plot(current_period)
                # ax2.set_title("Current " + key)
                # plt.show()
                time.sleep(2)

        except KeyboardInterrupt:
            # turn off the RX relay
            rp_c.rx_on(0)
            # Power off
            rp_c.set_power(0)
            break
