import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import chirp

# Signal parameters
fs = 96000  # Sampling frequency
t1 = 0.004  # Chirp duration 4 ms
t2 = 0.002  # Chirp duration 2 ms
pause = 0.008  # Pause 8 ms
max_samples = 16384


# Chirp generation
def generate_chirp(f0, f1, t, fs):
    t = np.linspace(0, t, int(fs * t))
    return chirp(t, f0=f0, f1=f1, t1=t[-1], method="linear")


# Generate the signal
def generate_signal(fs, t1, t2, pause):
    signal = []

    # First chirp 18-34 kHz, 4 ms, pause 8 ms
    signal.extend(generate_chirp(18000, 34000, t1, fs))
    signal.extend(np.zeros(int(fs * pause)))

    # Second and third chirps 34-18 kHz, 4 ms, pause 8 ms
    for _ in range(2):
        signal.extend(generate_chirp(34000, 18000, t1, fs))
        signal.extend(np.zeros(int(fs * pause)))

    # Remaining chirps 34-18 kHz, 2 ms, no pause
    for _ in range(129):
        signal.extend(generate_chirp(34000, 18000, t2, fs))

    return np.array(signal)


if __name__ == "__main__":

    # Signal generation
    signal = generate_signal(fs, t1, t2, pause)

    # Display the resulting signal
    plt.plot(signal)
    plt.title("Resulting Signal")
    plt.xlabel("Sample")
    plt.ylabel("Amplitude")