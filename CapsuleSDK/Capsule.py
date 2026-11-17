import ctypes


class Capsule_Log_Level(ctypes.c_int):
    Trace = 0
    Debug = 1
    Info = 2
    Warning = 3
    Error = 4
    Critical = 5
    Off = 6


class Capsule:
    def __init__(self, path_to_lib):
        self._path_to_lib = path_to_lib
        self._lib = ctypes.CDLL(self._path_to_lib)
        self._lib.clCCapsule_SetSingleThreaded.argtypes = [ctypes.c_bool]
        self._lib.clCCapsule_SetLogLevel.argtypes = [ctypes.c_int]
        self._lib.clCCapsule_GetLogLevel.restype = ctypes.c_int
        self._lib.clCCapsule_SetSingleThreaded(True)

    def get_path(self):
        return self._path_to_lib
    
    def get_lib(self):
        return self._lib

    def set_log_level(self, level):
        self._lib.clCCapsule_SetLogLevel(level)

    def get_log_level(self):
        return self._lib.clCCapsule_GetLogLevel()
