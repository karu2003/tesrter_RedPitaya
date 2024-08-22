import numpy as np
import matplotlib.pyplot as plt
import fcwt

# Параметры сигнала
f0 = 7000           # начальная частота (Гц)
f1 = 17000           # конечная частота (Гц)
T = 0.016            # длительность сигнала (с)
fs = 96000           # частота дискретизации (Гц)
num_segments = 8      # количество изменений направления чирпа

t = np.linspace(0, T, int(T * fs))  # временной вектор
segment_duration = T / num_segments  # длительность одного сегмента
frequencies = np.linspace(f0, f1, num_segments + 1)  # Частоты на границах сегментов

chirp_signal = np.array([])  # Инициализация итогового сигнала

# Генерация чирп-сигнала с 8 сегментами
for i in range(num_segments):
    t_segment = np.linspace(0, segment_duration, int(segment_duration * fs))

    # Падение частоты от текущей частоты до нижней границы сегмента
    freq_start = frequencies[i]
    freq_end = frequencies[i+1]
    amplitude = (freq_start + freq_end) / 2  # Амплитуда пропорциональна средней частоте сегмента
    chirp_segment = amplitude * np.cos(2 * np.pi * (freq_start * t_segment + 
                    (freq_end - freq_start) / (2 * segment_duration) * t_segment**2))
    
    # Добавление сегмента в общий сигнал
    chirp_signal = np.concatenate((chirp_signal, chirp_segment))



# Временной вектор для всего сигнала
t_total = np.linspace(0, T * num_segments, chirp_signal.size)

# Применение вейвлет-преобразования
freqs, cwt_matrix = fcwt.cwt(chirp_signal , fs, f0, f1, fn=128)

# Визуализация результатов
fig, ax = plt.subplots(3, 1, sharex=True, figsize=(12, 8))

ax[0].plot(t_total, chirp_signal)
ax[0].set_title("Исходный чирп-сигнал")
ax[0].set_xlabel("Время (с)")
ax[0].set_ylabel("Амплитуда")

# ax[1].plot(t, chirp_pm_signal)
# ax[1].set_title("Фазово модулированный чирп-сигнал")
# ax[1].set_xlabel("Время (с)")
# ax[1].set_ylabel("Амплитуда")

ax[2].imshow(np.abs(cwt_matrix), aspect="auto", extent=[0, T, f0, f1])#, cmap="jet")
ax[2].set_title("Амплитуда вейвлет-преобразования")
ax[2].set_xlabel("Время (с)")
ax[2].set_ylabel("Частота (Гц)")

plt.tight_layout()
plt.show()
