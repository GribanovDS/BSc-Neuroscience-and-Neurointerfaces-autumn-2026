# Курс "Нейронауки и нейроинтерфейсы" – Неделя 11

## 🧠 Проектное занятие №1
Добро пожаловать на первое проектное занятие по курсу Центрального Университета "Нейронауки и нейроинтерфейсы" в 2025 году! Сегодня мы познакомимся с нейроинтерфейсом Neiry HeadBand и научимся получать данные, используя Python и CapsuleSDK

### Цель занятия

Научиться подключаться к устройству, получать ЭЭГ, PSD и другие данные в реальном времени и визуализировать их.

---

### По итогам занятия вы сможете:

1. Подключаться к устройству Neiry HeadBand
2. Считывать EEG, MEMS, PPG и PSD данные 
3. Отрисовывать графики EEG в реальном времени
4. Понимать разницу между монополярным и биполярным режимом  

## Собираем скрипт-скелет по шагам

Создайте файл `lesson_1/device_info.py` и последовательно добавляйте в него блоки ниже

В результате получится скрипт, который

1. Загружает CapsuleSDK
2. Ищет доступные устройства
3. Выбирает первое устройство или Capsule с нужным серийным номером
4. Подключается к нему
5. Выводит основные характеристики

### Шаг 1. Подключаем стандартные модули

```python
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
```

`Path` помогает построить путь к корню репозитория независимо от операционной системы

Корень добавляется в `sys.path`, чтобы Python смог импортировать локальную папку `CapsuleSDK`

`threading.Event` будет использоваться как флаг наступления события

`time` нужен для ожидания событий без блокировки работы SDK

### Шаг 2. Импортируем классы CapsuleSDK

```python
from CapsuleSDK.Capsule import Capsule, Capsule_Log_Level
from CapsuleSDK.Device import Device, Device_Connection_Status
from CapsuleSDK.DeviceLocator import DeviceLocator
from CapsuleSDK.DeviceType import DeviceType
```

`Capsule` загружает нативную библиотеку

`DeviceLocator` ищет доступные устройства

`Device` отвечает за подключение и получение данных

`DeviceType` определяет, какой тип устройства нужно искать

### Шаг 3. Добавляем настройки и состояние программы

```python
BIPOLAR_CHANNELS = False
TARGET_SERIAL = None

locator = None
device = None
device_found = threading.Event()
device_connected = threading.Event()
```

`BIPOLAR_CHANNELS = False` включает обычный монополярный режим

При `BIPOLAR_CHANNELS = True` SDK формирует биполярные каналы

Если `TARGET_SERIAL` равен `None`, программа подключается к первому найденному устройству

Если в аудитории работает несколько устройств, в `TARGET_SERIAL` можно записать серийный номер своей

```python
TARGET_SERIAL = "1234567"
```

События `device_found` и `device_connected` позволяют понять, когда можно переходить к следующему этапу

### Шаг 4. Обрабатываем список найденных устройств

```python
def on_devices(current_locator, devices, fail_reason):
    global device

    if len(devices) == 0:
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
```

`on_devices` является callback-функцией

SDK вызовет её после завершения поиска

Функция выводит все найденные устройства, выбирает нужное и создаёт объект `Device`

После этого `device_found.set()` сообщает основной части программы, что поиск завершён успешно

### Шаг 5. Следим за статусом подключения

```python
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
```

Этот callback вызывается каждый раз при изменении состояния соединения

Когда HeadBand подключен, событие `device_connected` переводится в активное состояние

Имя `_device` начинается с подчёркивания, потому что этот аргумент требуется SDK, но внутри функции не используется

### Шаг 6. Создаём ожидание событий

```python
def wait_for(event, timeout):
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        locator.update()
        if event.is_set():
            return True
        time.sleep(0.02)

    return False
```

CapsuleSDK передаёт callbacks только во время вызова `locator.update()`

Поэтому нельзя просто использовать один длинный `time.sleep()` и ждать результата

Цикл обновляет SDK каждые 20 миллисекунд и одновременно проверяет нужное событие

`time.monotonic()` используется для надёжного измерения прошедшего времени

Если событие не произошло до окончания `timeout`, функция возвращает `False`

### Шаг 7. Выводим информацию об устройстве

```python
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
```

После подключения SDK позволяет запросить характеристики устройства

Количество и названия каналов нужно получать из SDK, потому что они зависят от устройства и выбранного режима подключения

### Шаг 8. Собираем основной сценарий

```python
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

    try:
        device.connect(bipolarChannels=BIPOLAR_CHANNELS)
        if not wait_for(device_connected, 40):
            raise RuntimeError("Не удалось подключиться")
        print_device_info()
    finally:
        if device_connected.is_set():
            device.disconnect()
            print("\nДевайс отключен")
        device.release()
```

Сначала выбирается нативная библиотека для текущей операционной системы

Уровень логов `Error` скрывает внутренние предупреждения SDK, но оставляет сообщения об ошибках

`DeviceType.Noise` запускает встроенный генератор случайного сигнала и позволяет проверить код без физического устройства

Для работы с Neiry HeadBand замените тип устройства

```python
locator.request_devices(DeviceType.Band, 15)
```

После поиска программа назначает callback подключения и вызывает `device.connect()`

Блок `finally` выполняется даже при ошибке, поэтому устройство будет отключено и освобождено

`device.release()` должен выполниться до уничтожения `DeviceLocator`

### Шаг 9. Добавляем точку запуска

```python
if __name__ == "__main__":
    main()
```

Эта проверка запускает `main()` только при прямом запуске файла

Теперь готовый скрипт можно выполнить из корня репозитория

```bash
python lesson_1/device_info.py
```

Для проверки без устройства оставьте `DeviceType.Noise`

Для занятия с физическим устройством используйте `DeviceType.Band`

## Какие данные можно получать

CapsuleSDK передаёт данные через callback-функции

Сначала callback нужно передать нужному объекту SDK, затем вызвать `device.start()` и продолжать вызывать `locator.update()`

### Импеданс электродов

Импеданс показывает качество электрического контакта между электродом и кожей

В SDK эта оценка называется `Resistances` и возвращается в омах

Высокое или нестабильное значение часто означает, что электрод плохо прижат, кожа сухая или волосы мешают контакту

```python
def on_resistances(_device, resistances):
    for index in range(len(resistances)):
        name = resistances.get_channel_name(index)
        value = resistances.get_value(index)
        print(name, value, "Ом")


device.set_on_resistances(on_resistances)
```

Готовый минимальный пример находится в `device_info_resistances.py`

### ЭЭГ

Электроэнцефалография или ЭЭГ это изменение электрической разности потенциалов во времени

`get_raw_value()` возвращает исходное значение, а `get_processed_value()` значение после встроенной обработки SDK

```python
def on_eeg(_device, eeg):
    sample_index = eeg.get_samples_count() - 1
    values = [
        eeg.get_processed_value(channel_index, sample_index)
        for channel_index in range(eeg.get_channels_count())
    ]
    print(values)


device.set_on_eeg(on_eeg)
```

`device_info_eeg.py` считывает один пакет данных

`device_info_eeg_continuous.py` выводит ЭЭГ непрерывно до нажатия `Ctrl+C`

### PSD

PSD или спектральная плотность мощности показывает, как мощность сигнала распределена по частотам

HeadBand рассчитывает PSD для каждого ЭЭГ канала и передаёт сетку частот вместе со значениями мощности

```python
def on_psd(_device, psd):
    frequencies = [
        psd.get_frequency(index)
        for index in range(psd.get_frequencies_count())
    ]
    values = [
        psd.get_psd(0, index)
        for index in range(psd.get_frequencies_count())
    ]
    print(frequencies, values)


device.set_on_psd(on_psd)
```

Пример `device_info_psd_continuous.py` выводит диапазон частот и частоту с максимальной мощностью для каждого канала

По PSD можно рассчитывать мощность в диапазонах, например альфа 8–13 Гц и бета 13–30 Гц

### MEMS

MEMS это инерциальные датчики движения

В CapsuleSDK они дают ускорение и угловую скорость по трём осям

Эти данные можно использовать для оценки движений головы, жестов и артефактов движения

```python
from CapsuleSDK.MEMS import MEMS


def on_mems(_mems, data):
    index = len(data) - 1
    accelerometer = data.get_accelerometer(index)
    gyroscope = data.get_gyroscope(index)
    print(accelerometer.x, accelerometer.y, accelerometer.z)
    print(gyroscope.x, gyroscope.y, gyroscope.z)


mems = MEMS(device, capsule.get_lib())
mems.set_on_update(on_mems)
```

Создавайте объект `MEMS` внутри `main()` после подключения и до `device.start()`

MEMS доступен не на всех моделях устройств

### PPG

PPG или фотоплетизмография это оптический сигнал, который отражает изменение кровенаполнения тканей во времени

Из PPG можно оценивать пульс и другие кардиометрики

В CapsuleSDK сырой PPG передаёт объект `Cardio`

```python
from CapsuleSDK.Cardio import Cardio


def on_ppg(_cardio, ppg):
    index = len(ppg) - 1
    print(ppg.get_timestamp(index), ppg.get_value(index))


cardio = Cardio(device, capsule.get_lib())
cardio.set_on_ppg(on_ppg)
```

Создавайте объект `Cardio` внутри `main()` после подключения и до `device.start()`

---

## Собираем MVP для управления прогресс-баром (а-ля устройством)

Мы уже умеем искать устройства, подключаться к ней и получать ЭЭГ

Теперь добавим буферы, расчёт peak-to-peak и интерфейс из трёх графиков

Скопируйте `device_info_eeg_continuous.py` в новый файл `final_mvp.py`

Функции `on_devices`, `on_connection`, `wait_for` и логика выбора библиотеки остаются прежними

### Шаг 1. Добавляем библиотеки для буферов и графиков

```python
from collections import deque

import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np
```

`deque` хранит ограниченное количество последних отсчётов

`NumPy` нужен для расчёта peak-to-peak

`Matplotlib` рисует ЭЭГ, peak-to-peak и прогресс

### Шаг 2. Добавляем настройки и состояние

```python
EEG_SECONDS = 5
P2P_WINDOW_SECONDS = 0.5
P2P_THRESHOLD = 0.00004
UPDATE_MS = 100

eeg_received = threading.Event()
stop_event = threading.Event()
data_lock = threading.Lock()

sample_rate = 250.0
eeg_buffers = []
```

`EEG_SECONDS` определяет длину видимого окна ЭЭГ

`P2P_WINDOW_SECONDS` определяет окно для расчёта peak-to-peak

`P2P_THRESHOLD` задаёт фиксированный порог мышечной активности

`UPDATE_MS` задаёт интервал обновления графика

`data_lock` не даёт callback и графику одновременно изменять буферы

### Шаг 3. Готовим буферы после подключения

Замените `print_device_info` на расширенную версию

```python
def print_device_info():
    global sample_rate, channel_names, eeg_buffers

    info = device.get_info()
    channels = device.get_channel_names()
    channel_names = [
        channels.get_name_by_index(index)
        for index in range(len(channels))
    ]
    sample_rate = float(device.get_eeg_sample_rate())
    buffer_size = int(sample_rate * EEG_SECONDS)
    eeg_buffers = [deque(maxlen=buffer_size) for _ in channel_names]

    print("\nИнформация об устройстве")
    print("Название:", info.get_name())
    print("Серийный номер:", info.get_serial())
    print("Прошивка:", info.get_firmware())
    print("Заряд:", device.get_battery_charge(), "%")
    print("Частота дискретизации:", sample_rate, "Гц")
    print("Каналы:", ", ".join(channel_names))
```

Размер каждого буфера равен частоте дискретизации, умноженной на `EEG_SECONDS`

Количество буферов равно количеству ЭЭГ каналов

### Шаг 4. Сохраняем все отсчёты ЭЭГ

Замените callback `on_eeg`

```python
def on_eeg(_device, eeg):
    with data_lock:
        for sample_index in range(eeg.get_samples_count()):
            values = [
                eeg.get_processed_value(channel_index, sample_index)
                for channel_index in range(eeg.get_channels_count())
            ]

            for buffer, value in zip(eeg_buffers, values):
                buffer.append(float(value))

    eeg_received.set()
```

В `device_info_eeg_continuous.py` достаточно выводить последний отсчёт пакета

Для графика и peak-to-peak нужно сохранять все отсчёты, иначе масштаб времени будет неверным

### Шаг 5. Продолжаем обновлять SDK во время работы окна

```python
def locator_loop():
    while not stop_event.is_set():
        locator.update()
        time.sleep(0.01)


def copy_eeg():
    with data_lock:
        channels = [np.asarray(buffer) for buffer in eeg_buffers]
        names = list(channel_names)
        rate = sample_rate

    return channels, names, rate
```

`plt.show()` запускает цикл окна Matplotlib

Поэтому `locator.update()` переносится в отдельный поток

`copy_eeg()` создаёт безопасную копию данных для отрисовки

### Шаг 6. Создаём три графика

Функция `make_interface` состоит из нескольких блоков

Сначала создадим оси и линии

```python
def make_interface():
    channels, names, _ = copy_eeg()
    figure, axes = plt.subplots(
        3,
        1,
        figsize=(12, 8),
        gridspec_kw={"height_ratios": [3, 2, 1]},
        constrained_layout=True,
    )
    eeg_axis, p2p_axis, progress_axis = axes

    eeg_lines = [
        eeg_axis.plot([], [], linewidth=1.2, label=names[index])[0]
        for index in range(len(channels))
    ]
    eeg_axis.set(title="ЭЭГ", ylabel="Напряжение, µV")
    eeg_axis.set_xlim(-EEG_SECONDS, 0)
    eeg_axis.legend(loc="upper right", ncols=len(eeg_lines))

    p2p_line, = p2p_axis.plot([], [], linewidth=2, color="#2563eb")
    threshold_line = p2p_axis.axhline(
        P2P_THRESHOLD,
        color="#dc2626",
        linestyle="--",
        label="Порог",
    )
    p2p_axis.set(title="Peak-to-peak", ylabel="Амплитуда", xlabel="Время, с")
    p2p_axis.legend(loc="upper right")

    progress_axis.barh([0], [100], height=0.55, color="#e2e8f0")
    progress_bar = progress_axis.barh([0], [0], height=0.55, color="#2563eb")[0]
    progress_text = progress_axis.text(50, 0, "0%", ha="center", va="center")
    progress_axis.set(xlim=(0, 100), ylim=(-0.5, 0.5), xlabel="Прогресс")
    progress_axis.set_yticks([])

    for axis in axes:
        axis.grid(alpha=0.2)
        axis.spines[["top", "right"]].set_visible(False)

    p2p_times = deque(maxlen=1000)
    p2p_values = deque(maxlen=1000)
    started_at = time.monotonic()
    progress = 0
```

Первая ось показывает окно ЭЭГ

Вторая ось показывает peak-to-peak и порог

Третья ось содержит прогресс-бар

Значение порога задаётся в `P2P_THRESHOLD`

### Шаг 7. Обновляем ЭЭГ и рассчитываем peak-to-peak

Добавьте эту вложенную функцию внутрь `make_interface`

```python
    def update(_frame):
        nonlocal progress

        channels, names, rate = copy_eeg()
        all_eeg = []

        for line, values in zip(eeg_lines, channels):
            x_values = np.arange(-len(values) + 1, 1) / rate
            line.set_data(x_values, values)
            all_eeg.extend(values)

        if all_eeg:
            low, high = min(all_eeg), max(all_eeg)
            padding = max((high - low) * 0.1, np.finfo(float).eps)
            eeg_axis.set_ylim(low - padding, high + padding)

        window_size = int(rate * P2P_WINDOW_SECONDS)
        if any(len(values) < window_size for values in channels):
            return eeg_lines

        p2p_by_channel = [float(np.ptp(values[-window_size:])) for values in channels]
        p2p = max(p2p_by_channel)
        now = time.monotonic()
        elapsed = now - started_at

        p2p_times.append(elapsed)
        p2p_values.append(p2p)
        p2p_line.set_data(p2p_times, p2p_values)
        p2p_axis.set_xlim(max(0, elapsed - 20), max(20, elapsed))
```

`np.ptp()` вычитает минимум окна из его максимума

Для управления берётся максимальное peak-to-peak среди всех каналов

### Шаг 8. Применяем порог и обновляем прогресс

Этот блок продолжает функцию `update`

```python
        active = p2p > P2P_THRESHOLD
        progress = np.clip(progress + (2 if active else -1), 0, 100)
        progress_bar.set_color("#16a34a" if active else "#2563eb")
        progress_text.set_text(f"{progress:.0f}%")

        progress_bar.set_width(progress)

        y_max = max(max(p2p_values), P2P_THRESHOLD, np.finfo(float).eps)
        p2p_axis.set_ylim(0, y_max * 1.25)
        p2p_axis.set_title(
            "Peak-to-peak   "
            + "  ".join(
                f"{name} {value:.2e}"
                for name, value in zip(names, p2p_by_channel)
            )
        )

        return [*eeg_lines, p2p_line, threshold_line, progress_bar, progress_text]

    return figure, update
```

Пока peak-to-peak выше порога, прогресс растёт и бар становится зелёным

Когда peak-to-peak ниже порога, прогресс уменьшается

Гистерезис в этой логике не используется

### Шаг 9. Обновляем main

Поиск и подключение остаются такими же, как в `device_info_eeg_continuous.py`

После получения первого пакета ЭЭГ запускаем поток SDK и окно

```python
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

            threading.Thread(target=locator_loop, daemon=True).start()
            figure, update = make_interface()
            animation = FuncAnimation(
                figure,
                update,
                interval=UPDATE_MS,
                blit=False,
                cache_frame_data=False,
            )
            plt.show()
        finally:
            stop_event.set()
            device.stop()
    finally:
        if device_connected.is_set():
            device.disconnect()
            print("Девайс отключен")
        device.release()
```

Переменная `animation` должна сохраняться до закрытия окна

Блоки `finally` останавливают поток данных, отключают HeadBand и освобождают объект `Device`

### Шаг 10. Запускаем программу

```python
if __name__ == "__main__":
    main()
```

Установите зависимости из корня репозитория

```bash
python -m pip install -r requirements.txt
```

Запустите MVP

```bash
python lesson_1/final_mvp.py
```

## Что показывает final_mvp.py

Первый график показывает ЭЭГ в реальном времени. В монополярном режиме обычно отображаются четыре канала, в биполярном два

Второй график показывает peak-to-peak амплитуду в окне 0.5 секунды

Третий график показывает прогресс

Попробуйте сжать челюсть, нахмуриться или поднять брови

## Важно

В этом MVP используется мышечный артефакт, а не распознавание мыслей или команд мозга

Сокращение мышц создаёт большую амплитуду в ЭЭГ каналах, поэтому peak-to-peak хорошо подходит для первого простого управляющего сигнала

## Домашнее задание

1. Создайте `device_info_mems_continuous.py` по аналогии с `device_info_eeg_continuous.py`

   Выводите время, ускорение и угловую скорость по осям X, Y и Z

2. Добавьте в `device_info_psd_continuous.py` расчёт мощности альфа и бета ритмов

   Используйте диапазоны 8–13 Гц для альфа и 13–30 Гц для бета

   Для полной мощности диапазона проинтегрируйте PSD по частоте

3. Создайте версию MVP, в которой прогресс-бар управляется мощностью альфа ритма

   Прогресс должен расти, когда мощность альфа выше порога, и уменьшаться, когда она ниже порога

