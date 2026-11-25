from collections import deque
from pathlib import Path
import sys
import threading
import time

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from CapsuleSDK.Capsule import Capsule, Capsule_Log_Level
from CapsuleSDK.Device import Device, Device_Connection_Status
from CapsuleSDK.DeviceLocator import DeviceLocator
from CapsuleSDK.DeviceType import DeviceType


DEVICE_TYPE = DeviceType.Noise
BIPOLAR_CHANNELS = False
TARGET_SERIAL = None
EEG_SECONDS = 5
PSD_MAX_HZ = 40
ALPHA_LOW_HZ = 8
ALPHA_HIGH_HZ = 13
ALPHA_HISTORY_SECONDS = 20
UPDATE_MS = 100

locator = None
device = None
channel_names = []
eeg_buffers = []
sample_rate = 250.0
psd_frequencies = np.array([])
psd_values = []
alpha_times = deque()
alpha_values = deque()
recording_started_at = 0.0
device_found = threading.Event()
device_connected = threading.Event()


def on_devices(current_locator, devices, fail_reason):
    global device

    if len(devices) == 0:
        print("Capsule не найдена. Причина:", fail_reason.value)
        return

    selected = None
    for index in range(len(devices)):
        info = devices[index]
        print(f"{index + 1}. {info.get_name()} | {info.get_serial()}")

        if TARGET_SERIAL is None and selected is None:
            selected = info
        elif info.get_serial() == TARGET_SERIAL:
            selected = info

    if selected is None:
        print("Устройство с указанным серийным номером не найдено")
        return

    device = Device(current_locator, selected.get_serial(), current_locator.get_lib())
    device_found.set()


def on_connection(_device, status):
    value = status.value if hasattr(status, "value") else status
    names = {
        Device_Connection_Status.Device_ConnectionState_Disconnected: "отключено",
        Device_Connection_Status.Device_ConnectionState_Connected: "подключено",
        Device_Connection_Status.Device_ConnectionState_UnsupportedConnection: "не поддерживается",
    }
    print("Статус подключения:", names.get(value, value))

    if value == Device_Connection_Status.Device_ConnectionState_Connected:
        device_connected.set()


def on_eeg(_device, eeg):
    for sample_index in range(eeg.get_samples_count()):
        for channel_index in range(eeg.get_channels_count()):
            value = eeg.get_processed_value(channel_index, sample_index)
            eeg_buffers[channel_index].append(value)


def calculate_alpha_power(frequencies, spectra):
    alpha_mask = (
        (frequencies >= ALPHA_LOW_HZ)
        & (frequencies <= ALPHA_HIGH_HZ)
    )

    if np.count_nonzero(alpha_mask) < 2:
        return 0.0

    channel_powers = [
        np.trapezoid(spectrum[alpha_mask], frequencies[alpha_mask])
        for spectrum in spectra
    ]
    return float(np.mean(channel_powers))


def on_psd(_device, psd):
    global psd_frequencies, psd_values

    frequencies_count = psd.get_frequencies_count()
    psd_frequencies = np.array([
        psd.get_frequency(index)
        for index in range(frequencies_count)
    ])
    psd_values = [
        np.array([
            psd.get_psd(channel_index, frequency_index)
            for frequency_index in range(frequencies_count)
        ])
        for channel_index in range(psd.get_channels_count())
    ]

    alpha_power = calculate_alpha_power(psd_frequencies, psd_values)
    elapsed = time.monotonic() - recording_started_at
    alpha_times.append(elapsed)
    alpha_values.append(alpha_power)

    while alpha_times and elapsed - alpha_times[0] > ALPHA_HISTORY_SECONDS:
        alpha_times.popleft()
        alpha_values.popleft()


def wait_for(event, timeout):
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        locator.update()
        if event.is_set():
            return True
        time.sleep(0.02)

    return False


def prepare_eeg_buffers():
    global channel_names, eeg_buffers, sample_rate

    channels = device.get_channel_names()
    channel_names = [
        channels.get_name_by_index(index)
        for index in range(len(channels))
    ]
    sample_rate = device.get_eeg_sample_rate()
    buffer_size = int(sample_rate * EEG_SECONDS)
    eeg_buffers = [deque(maxlen=buffer_size) for _ in channel_names]

    print("Частота дискретизации:", sample_rate, "Гц")
    print("Каналы:", ", ".join(channel_names))


def make_interface():
    figure, (eeg_axis, psd_axis, alpha_axis) = plt.subplots(3, 1, figsize=(11, 10))
    eeg_lines = [eeg_axis.plot([], [], label=name)[0] for name in channel_names]
    psd_lines = [psd_axis.plot([], [], label=name)[0] for name in channel_names]
    alpha_line = alpha_axis.plot([], [], color="#4C78A8", linewidth=2)[0]
    alpha_text = alpha_axis.text(0.99, 0.92, "", ha="right", transform=alpha_axis.transAxes)

    eeg_axis.set_title("ЭЭГ")
    eeg_axis.set_xlabel("Время, с")
    eeg_axis.set_ylabel("Амплитуда, В")
    eeg_axis.set_xlim(-EEG_SECONDS, 0)
    eeg_axis.grid(alpha=0.2)
    eeg_axis.legend(loc="upper left", ncols=2)

    psd_axis.set_title("Спектральная плотность мощности")
    psd_axis.set_xlabel("Частота, Гц")
    psd_axis.set_ylabel("PSD, В²/Гц")
    psd_axis.set_xlim(0, PSD_MAX_HZ)
    psd_axis.set_yscale("log")
    psd_axis.set_ylim(1e-15, 1e-6)
    psd_axis.axvspan(ALPHA_LOW_HZ, ALPHA_HIGH_HZ, color="#F2CF5B", alpha=0.25)
    psd_axis.grid(alpha=0.2)
    psd_axis.legend(loc="upper right", ncols=2)

    alpha_axis.set_title("Средняя мощность альфа-ритма")
    alpha_axis.set_xlabel("Время, с")
    alpha_axis.set_ylabel("Мощность, В²")
    alpha_axis.set_xlim(0, ALPHA_HISTORY_SECONDS)
    alpha_axis.grid(alpha=0.2)
    figure.tight_layout()

    def update(_frame):
        locator.update()

        for line, buffer in zip(eeg_lines, eeg_buffers):
            values = np.asarray(buffer)
            times = np.arange(-len(values), 0) / sample_rate
            line.set_data(times, values)

        eeg_axis.relim()
        eeg_axis.autoscale_view(scalex=False, scaley=True)

        for line, values in zip(psd_lines, psd_values):
            positive_values = np.maximum(values, np.finfo(float).tiny)
            line.set_data(psd_frequencies, positive_values)

        if psd_values:
            psd_axis.relim()
            psd_axis.autoscale_view(scalex=False, scaley=True)

        if alpha_values:
            times = np.asarray(alpha_times)
            values = np.asarray(alpha_values)
            alpha_line.set_data(times, values)
            alpha_text.set_text(f"{values[-1]:.3e} В²")
            alpha_axis.set_xlim(
                max(0, times[-1] - ALPHA_HISTORY_SECONDS),
                max(ALPHA_HISTORY_SECONDS, times[-1]),
            )
            alpha_axis.relim()
            alpha_axis.autoscale_view(scalex=False, scaley=True)

        return eeg_lines + psd_lines + [alpha_line, alpha_text]

    animation = FuncAnimation(
        figure,
        update,
        interval=UPDATE_MS,
        blit=False,
        cache_frame_data=False,
    )
    return figure, animation


def main():
    global locator, recording_started_at

    library = "CapsuleClient.dll" if sys.platform.startswith("win") else "libCapsuleClient.dylib"
    capsule = Capsule(str(ROOT / "CapsuleSDK" / library))
    capsule.set_log_level(Capsule_Log_Level.Error)
    locator = DeviceLocator(capsule.get_lib())
    locator.set_on_devices_list(on_devices)

    print("Ищем...")
    locator.request_devices(DEVICE_TYPE, 15)
    if not wait_for(device_found, 20):
        raise RuntimeError("Не удалось найти устройство")

    device.set_on_connection_status_changed(on_connection)
    device.set_on_eeg(on_eeg)
    device.set_on_psd(on_psd)

    try:
        device.connect(bipolarChannels=BIPOLAR_CHANNELS)
        if not wait_for(device_connected, 40):
            raise RuntimeError("Не удалось подключиться")

        prepare_eeg_buffers()
        recording_started_at = time.monotonic()
        device.start()

        try:
            _figure, _animation = make_interface()
            plt.show()
        finally:
            device.stop()
    finally:
        if device_connected.is_set():
            device.disconnect()
        device.release()


if __name__ == "__main__":
    main()
