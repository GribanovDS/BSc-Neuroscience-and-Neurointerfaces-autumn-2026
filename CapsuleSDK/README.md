# CapsuleSDK

`CapsuleSDK` содержит Python обёртки и нативные библиотеки Capsule v2.0.98 для работы с Neiry HeadBand

SDK позволяет находить и подключать устройство, получать ЭЭГ, сопротивление электродов, данные движения, ФПГ, спектры и метрики встроенных классификаторов

## Состав папки

```text
CapsuleSDK/
├── examples/
│   ├── main.py
│   └── load_npy_example.py
├── Capsule.py
├── DeviceLocator.py
├── DeviceInfo.py
├── Device.py
├── EEGTimedData.py
├── EEGArtifacts.py
├── Resistances.py
├── PSDData.py
├── MEMS.py
├── MEMSTimedData.py
├── PPGTimedData.py
├── Cardio.py
├── Emotions.py
├── Calibrator.py
├── Productivity.py
├── PhysiologicalStates.py
├── Error.py
├── DeviceType.py
├── libCapsuleClient.dylib
└── CapsuleClient.dll
```

`libCapsuleClient.dylib` используется на macOS

`CapsuleClient.dll` используется на Windows

## С чего начать

Для первой проверки подключения используйте короткий пример курса

```bash
python lesson_1/device_info.py
```

Он найдёт устройство, подключится к нему, выведет основную информацию и корректно завершит соединение

## Полный пример SDK

`examples/main.py` показывает работу почти со всеми возможностями SDK

В примере есть ЭЭГ, сопротивление электродов, MEMS, ФПГ, PSD, калибровка и встроенные классификаторы

Запускайте его из корня репозитория

```bash
python CapsuleSDK/examples/main.py
```

Пример рассчитан на физическое устройство `DeviceType.Band`

Записанные массивы сохраняются в `CapsuleSDK/examples/data`

Эта папка создаётся автоматически и не добавляется в Git

## Просмотр записанных данных

`examples/load_npy_example.py` содержит отдельные блоки для загрузки и визуализации сохранённых массивов

Сначала запишите данные с помощью `examples/main.py`, затем открывайте файл в редакторе с поддержкой Python cells и запускайте нужные блоки

```bash
python CapsuleSDK/examples/load_npy_example.py
```

Некоторые блоки требуют конкретного потока данных и не будут работать, если соответствующий файл ещё не был записан

## Как устроено подключение

Обычный сеанс состоит из следующих шагов

1. Загрузить нативную библиотеку через `Capsule`
2. Создать `DeviceLocator`
3. Назначить callback со списком найденных устройств
4. Запустить поиск через `request_devices`
5. Создать `Device` для выбранного устройства
6. Назначить callbacks для нужных данных
7. Подключиться через `device.connect`
8. Запустить поток через `device.start`
9. Регулярно вызывать `locator.update`
10. Остановить поток, отключиться и освободить устройство

`locator.update()` должен вызываться во время поиска, подключения и получения данных

Без него SDK не сможет передавать новые события в Python callbacks

## Завершение работы

Если был вызван `device.start()`, сначала вызовите

```python
device.stop()
```

Затем отключите и освободите устройство

```python
device.disconnect()
device.release()
```

`device.release()` должен выполниться до уничтожения `DeviceLocator`

Это предотвращает повторное освобождение памяти при завершении Python

## Уровень сообщений SDK

Чтобы скрыть служебные предупреждения и оставить только ошибки, установите уровень `Error`

```python
from CapsuleSDK.Capsule import Capsule_Log_Level

capsule.set_log_level(Capsule_Log_Level.Error)
```

Во время отладки можно использовать уровни `Debug`, `Info` или `Warning`

## Проверка без физического устройства

Для проверки ЭЭГ-потока можно использовать генераторы

```python
DeviceType.SinWave
DeviceType.Noise
```

Они не заменяют физическую Capsule и не позволяют полноценно проверить MEMS, ФПГ, сопротивление электродов и качество контакта

## Если устройство не находится

Проверьте следующее

- Bluetooth включён
- Capsule заряжена и находится рядом
- Устройство не подключено к другой программе
- В `request_devices` выбран правильный `DeviceType`
- Во время ожидания вызывается `locator.update()`
- Используется библиотека для текущей операционной системы

На macOS система может заблокировать первый запуск `libCapsuleClient.dylib`

В этом случае откройте «Системные настройки», перейдите в «Конфиденциальность и безопасность» и нажмите «Всё равно открыть»
