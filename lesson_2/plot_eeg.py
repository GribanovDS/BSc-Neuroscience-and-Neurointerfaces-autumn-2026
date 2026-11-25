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
UPDATE_MS = 50

locator = None
device = None
channel_names = []
eeg_buffers = []
sample_rate = 250.0
device_found = threading.Event()
device_connected = threading.Event()


def on_devices(current_locator, devices, fail_reason):
    global device

    if len(devices) == 0:
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
    figure, axis = plt.subplots(figsize=(11, 6))
    lines = [axis.plot([], [], label=name)[0] for name in channel_names]

    axis.set_title("ЭЭГ в реальном времени")
    axis.set_xlabel("Время, с")
    axis.set_ylabel("Амплитуда, В")
    axis.set_xlim(-EEG_SECONDS, 0)
    axis.grid(alpha=0.2)
    axis.legend(loc="upper left", ncols=2)
    figure.tight_layout()

    def update(_frame):
        locator.update()

        for line, buffer in zip(lines, eeg_buffers):
            values = np.asarray(buffer)
            times = np.arange(-len(values), 0) / sample_rate
            line.set_data(times, values)

        axis.relim()
        axis.autoscale_view(scalex=False, scaley=True)
        return lines

    animation = FuncAnimation(
        figure,
        update,
        interval=UPDATE_MS,
        blit=False,
        cache_frame_data=False,
    )
    return figure, animation


def main():
    global locator

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

    try:
        device.connect(bipolarChannels=BIPOLAR_CHANNELS)
        if not wait_for(device_connected, 40):
            raise RuntimeError("Не удалось подключиться")

        prepare_eeg_buffers()
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
