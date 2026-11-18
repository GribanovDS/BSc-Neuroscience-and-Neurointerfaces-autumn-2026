from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from CapsuleSDK.Capsule import Capsule, Capsule_Log_Level
from CapsuleSDK.Device import Device, Device_Connection_Status
from CapsuleSDK.DeviceLocator import DeviceLocator
from CapsuleSDK.DeviceType import DeviceType

BIPOLAR_CHANNELS = False
TARGET_SERIAL = None

locator = None
device = None
device_found = threading.Event()
device_connected = threading.Event()
eeg_received = threading.Event()


def on_devices(current_locator, devices, fail_reason):
    global device

    if len(devices) == 0:
        print("Capsule не найдена. Причина:", fail_reason.value)
        return

    print(f"Найдено устройств: {len(devices)}")
    selected = None

    for index in range(len(devices)):
        info = devices[index]
        print(
            f"{index + 1}. {info.get_name()} | "
            f"серийный номер {info.get_serial()} | "
            f"прошивка {info.get_firmware()}"
        )

        if TARGET_SERIAL is None and selected is None:
            selected = info
        elif info.get_serial() == TARGET_SERIAL:
            selected = info

    if selected is None:
        print("Устройство с указанным серийным номером не найдено")
        return

    print("\nПодключаемся к", selected.get_serial())
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


def on_eeg(current_device, eeg):
    if eeg_received.is_set():
        return

    channels = current_device.get_channel_names()
    sample_index = eeg.get_samples_count() - 1

    print("\nПервый пакет ЭЭГ")
    print("Время:", eeg.get_timestamp(sample_index), "мс")

    for channel_index in range(eeg.get_channels_count()):
        name = channels.get_name_by_index(channel_index)
        raw = eeg.get_raw_value(channel_index, sample_index)
        processed = eeg.get_processed_value(channel_index, sample_index)
        print(f"{name}: raw={raw:.3e}, processed={processed:.3e}")

    eeg_received.set()


def wait_for(event, timeout):
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        locator.update()
        if event.is_set():
            return True
        time.sleep(0.02)

    return False


def print_device_info():
    info = device.get_info()
    channels = device.get_channel_names()
    channel_names = [
        channels.get_name_by_index(index)
        for index in range(len(channels))
    ]

    print("\nИнформация об устройстве")
    print("Название:", info.get_name())
    print("Серийный номер:", info.get_serial())
    print("Прошивка:", info.get_firmware())
    print("Заряд:", device.get_battery_charge(), "%")
    print("Частота дискретизации:", device.get_eeg_sample_rate(), "Гц")
    print("Каналы:", ", ".join(channel_names))


def main():
    global locator

    library = "CapsuleClient.dll" if sys.platform.startswith("win") else "libCapsuleClient.dylib"
    capsule = Capsule(str(ROOT / "CapsuleSDK" / library))
    capsule.set_log_level(Capsule_Log_Level.Error)
    locator = DeviceLocator(capsule.get_lib())
    locator.set_on_devices_list(on_devices)

    print("Ищем...")
    locator.request_devices(DeviceType.Noise, 15)
    if not wait_for(device_found, 20):
        raise RuntimeError("Не удалось найти")

    device.set_on_connection_status_changed(on_connection)
    device.set_on_eeg(on_eeg)

    try:
        device.connect(bipolarChannels=BIPOLAR_CHANNELS)
        if not wait_for(device_connected, 40):
            raise RuntimeError("Не удалось подключиться")

        print_device_info()
        device.start()

        try:
            if not wait_for(eeg_received, 10):
                raise RuntimeError("Не удалось получить ЭЭГ")
        finally:
            device.stop()
    finally:
        if device_connected.is_set():
            device.disconnect()
            print("\nДевайс отключен")
        device.release()


if __name__ == "__main__":
    main()
