import numpy as np
import time
import scipy
from scipy.signal import butter, lfilter, sosfilt, sosfreqz, filtfilt
from scipy.signal import hilbert, find_peaks, peak_widths, argrelextrema


def butter_bandpass(lowcut, highcut, fs, order=5):
    return butter(order, [lowcut, highcut], fs=fs, btype="band")


def butter_bandpass_filter(data, lowcut, highcut, fs, order=5):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = lfilter(b, a, data)
    return y


def butter_highpass(cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype="high", analog=False)
    return b, a


def butter_highpass_filter(data, cutoff, fs, order=5):
    b, a = butter_highpass(cutoff, fs, order=order)
    y = filtfilt(b, a, data)
    return y


def butter_lowpass(cutoff, fs, order=5):
    return butter(order, cutoff, fs=fs, btype="low", analog=False)


def butter_lowpass_filter(data, cutoff, fs, order=5):
    b, a = butter_lowpass(cutoff, fs, order=order)
    y = lfilter(b, a, data)
    return y


class SOS:
    def __init__(self):
        pass

    def butter_bandpass(self, lowcut, highcut, fs, order=5):
        nyq = 0.5 * fs
        low = lowcut / nyq
        high = highcut / nyq
        sos = butter(order, [low, high], analog=False, btype="band", output="sos")
        return sos

    def butter_bandpass_filter(self, data, lowcut, highcut, fs, order=5):
        sos = self.butter_bandpass(lowcut, highcut, fs, order=order)
        y = sosfilt(sos, data)
        return y


def chirp_l(
    buffer=16384, phi=270, f_min=600000, f_max=1000000, duration=0.00025, ampl=1
):
    t = np.linspace(0, duration, buffer)
    beta = (f_max - f_min) / duration
    phase = 2 * np.pi * (f_min * t + 0.5 * beta * t * t)
    phi *= np.pi / 180
    x0 = np.cos(phase + phi) * ampl
    return t, x0


def gen_signals_sequence(frequencies, duration=0.0001, sample_rate=10e6):
    # Initialize signal and time arrays
    signal = np.array([])
    t = np.array([])

    # Initialize phase
    phase = 0

    # Generate signals
    for i, freq in enumerate(frequencies):
        t_i = np.arange(
            i * duration, (i + 1) * duration, 1 / sample_rate
        )  # Time array for current signal
        signal_i = np.sin(
            2 * np.pi * freq * (t_i - i * duration) + phase
        )  # Generate signal with phase shift
        phase += 2 * np.pi * freq * duration  # Update phase for next signal

        # Concatenate current signal and time array to the total signal and time arrays
        signal = np.concatenate((signal, signal_i))
        t = np.concatenate((t, t_i))

    return t, signal


# frequencies = [100e3, 150e3, 200e3, 250e3, 300e3]  # List of frequencies
# t, signal = gen_signals_sequence(frequencies)


def x_edge(data, thresh=0.2):
    mask1 = (data[:-1] < thresh) & (data[1:] > thresh)
    mask2 = (data[:-1] > thresh) & (data[1:] < thresh)
    rising_edge = np.flatnonzero(mask1) + 1
    falling_edge = np.flatnonzero(mask2) + 1
    return rising_edge, falling_edge


def rising_edge(data, thresh):
    sign = data >= thresh
    pos = np.where(np.convolve(sign, [1, -1]) == 1)
    return pos


def falling_edge(data, thresh):
    sign = data >= thresh
    pos = np.where(np.convolve(sign, [1, -1]) == -1)
    return pos


def envelope(sig, distance=50):
    # split signal into negative and positive parts
    u_x = np.where(sig > 0)[0]
    l_x = np.where(sig < 0)[0]
    u_y = sig.copy()
    u_y[l_x] = 0
    l_y = -sig.copy()
    l_y[u_x] = 0

    # find upper and lower peaks
    u_peaks, _ = scipy.signal.find_peaks(u_y, distance=distance)
    l_peaks, _ = scipy.signal.find_peaks(l_y, distance=distance)

    # use peaks and peak values to make envelope
    u_x = u_peaks
    u_y = sig[u_peaks]
    l_x = l_peaks
    l_y = sig[l_peaks]

    # add start and end of signal to allow proper indexing
    end = len(sig)
    u_x = np.concatenate((u_x, [0, end]))
    u_y = np.concatenate((u_y, [0, 0]))
    l_x = np.concatenate((l_x, [0, end]))
    l_y = np.concatenate((l_y, [0, 0]))

    # create envelope functions
    u = scipy.interpolate.interp1d(u_x, u_y)
    l = scipy.interpolate.interp1d(l_x, l_y)
    # return u, l
    return u(np.arange(end))


def hl_envelopes_idx(s, dmin=1, dmax=1, split=False):
    """
    Input :
    s: 1d-array, data signal from which to extract high and low envelopes
    dmin, dmax: int, optional, size of chunks, use this if the size of the input signal is too big
    split: bool, optional, if True, split the signal in half along its mean, might help to generate the envelope in some cases
    Output :
    lmin,lmax : high/low envelope idx of input signal s
    """

    # locals min
    lmin = (np.diff(np.sign(np.diff(s))) > 0).nonzero()[0] + 1
    # locals max
    lmax = (np.diff(np.sign(np.diff(s))) < 0).nonzero()[0] + 1

    if split:
        # s_mid is zero if s centered around x-axis or more generally mean of signal
        s_mid = np.mean(s)
        # pre-sorting of locals min based on relative position with respect to s_mid
        lmin = lmin[s[lmin] < s_mid]
        # pre-sorting of local max based on relative position with respect to s_mid
        lmax = lmax[s[lmax] > s_mid]

    # global min of dmin-chunks of locals min
    lmin = lmin[
        [i + np.argmin(s[lmin[i : i + dmin]]) for i in range(0, len(lmin), dmin)]
    ]
    # global max of dmax-chunks of locals max
    lmax = lmax[
        [i + np.argmax(s[lmax[i : i + dmax]]) for i in range(0, len(lmax), dmax)]
    ]
    return lmin, lmax


def envelope_fft(sig, distance=50):
    u_y = sig.copy()
    u_peaks, _ = scipy.signal.find_peaks(u_y, distance=distance)
    u_x = u_peaks
    u_y = sig[u_peaks]
    end = len(sig)
    u_x = np.concatenate((u_x, [0, end]))
    u_y = np.concatenate((u_y, [0, 0]))
    f = scipy.interpolate.interp1d(u_x, u_y)
    return f(np.arange(end))


def voltage_divider(voltage):
    """
    Vout = Vin * R2 / (R1 + R2)
    Vin = Vout * (R1 + R2) / R2
    R1 = R2 * (Vin - Vout) / Vout
    R2 = R1 * Vout / (Vin – Vout)
    """
    R1 = 120
    R2 = 5
    Attenuator = 20
    voltage = voltage * ((R1 + R2) / R2)
    ratio = 10 ** (Attenuator / 20)
    voltage = voltage * ratio
    return voltage

def CQ_330E(voltage):
    R1 = 12000
    R2 = 3000
    Zero_Current = 0.5
    Sensitivity = 0.2
    voltage = voltage * ((R1 + R2) / R2)
    return (voltage - Zero_Current) / Sensitivity


def voltage_divider_pre(voltage):
    """
    Vout = Vin * R2 / (R1 + R2)
    Vin = Vout * (R1 + R2) / R2
    R1 = R2 * (Vin - Vout) / Vout
    R2 = R1 * Vout / (Vin – Vout)
    """
    R1 = 6200
    R2 = 2700
    voltage = voltage * ((R1 + R2) / R2)
    return voltage

def voltage_divider_KV(ch, voltage):
    if ch == 2:
        R1 = 1.5e6
        R2 = 6e3
        R3 = 2e3
        # two resistors in parallel
        R2 = 1 / (1 / R2 + 1 / R3)
    else:
        R1 = 2e6
        R2 = 4e3
    voltage = voltage * ((R1 + R2) / R2)
    return voltage


def rms(voltage):
    return np.sqrt(np.mean(np.square(voltage)))
    # return  lambda voltage, axis=None: np.sqrt(np.mean(np.square(voltage), axis))
    # return np.sqrt(np.mean(voltage**2))
    # return np.sqrt(voltage.dot(voltage)/voltage.size)


def find_max_level(voltage, thresh=0.2, width=20):
    rising_edge, falling_edge = x_edge(voltage, thresh)
    level = []
    for i in falling_edge:
        if voltage[i - width * 2] > 0:
            level.append(voltage[i - width * 2 : i - width])
    return np.mean(np.array(level))  # np.max(np.array(level))


def percentage_change(previous, current):
    try:
        percentage = abs(previous - current) / ((previous + current) / 2) * 100
    except ZeroDivisionError:
        percentage = float("inf")
    return percentage


def find_minima_widths(y):
    # minima_ind = argrelextrema(y, np.less)[0]
    minima_ind = argrelextrema(y, np.greater)[0]
    arr_diff = np.diff(minima_ind)
    max_diff = np.max(arr_diff)
    max_idx = np.where(arr_diff == max_diff)
    # print(max_idx)
    return minima_ind[max_idx[0] - 2][0], minima_ind[max_idx[0] + 1][0]


def find_widths(y, width=700, idx=0):
    peaks, properties = find_peaks(y, width=width)
    full_peak_res = peak_widths(y, [peaks[idx]], rel_height=1)
    return int(full_peak_res[2]), int(full_peak_res[3])


def find_widths_min(y, width=700, delta=1000):
    peaks, _ = find_peaks(y, width=width)
    idx = []
    for i in peaks:
        if i > delta:
            arr_l = y[i - delta : i]
            arr_r = y[i : i + delta]
            min_l = np.min(arr_l)
            min_r = np.min(arr_r)
            l_idx = np.where(arr_l == min_l)[0]
            r_idx = np.where(arr_r == min_r)[0]
            idx.append([i - l_idx[0], i + r_idx[0], i])
    return idx


def near_peak(y, L, R):
    cutout = y[L:R]
    max = np.max(cutout)
    # res = [i for i, j in enumerate(cutout) if j == max]
    res = np.where(cutout == max)[0]
    return R - (L + res)


def ratio_db(V1, V2):
    return 20 * np.log10(V2 / V1)


def div_db(div):
    return 20 * np.log10(div)


def db_ratio(db):
    return 10 ** (db / 20)


def checking_conditions(low, high, current):
    if current > low and current < high:
        return False
    return True


def checking_width(width, pattern, current):
    low = pattern - width
    high = pattern + width
    if current > low and current < high:
        return False
    return True
