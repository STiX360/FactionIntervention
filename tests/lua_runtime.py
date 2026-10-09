"""Mock-test Lua 5.1 adapter: installed OpenMW on Windows, Lupa in portable CI."""
import ctypes
import os
from pathlib import Path


class Globals:
    def __init__(self, runtime):
        object.__setattr__(self, 'runtime', runtime)

    def __setattr__(self, key, value):
        data = str(value).encode('utf-8')
        self.runtime.dll.lua_pushlstring(self.runtime.state, data, len(data))
        self.runtime.dll.lua_setfield(self.runtime.state, -10002, key.encode('ascii'))


class LuaRuntime:
    def __init__(self, **_):
        self.backend = None
        if os.name != 'nt' or os.environ.get('FI_TEST_LUA_BACKEND') == 'portable':
            from lupa.lua51 import LuaRuntime as PortableLuaRuntime
            self.backend = PortableLuaRuntime(**_)
            return
        engine = Path(os.environ.get('FI_TEST_ENGINE', r'C:\Program Files\OpenMW 0.51.0'))
        self.directory = os.add_dll_directory(str(engine))
        self.dll = ctypes.CDLL(str(engine / 'lua51.dll'))
        self.dll.luaL_newstate.restype = ctypes.c_void_p
        self.dll.luaL_openlibs.argtypes = [ctypes.c_void_p]
        self.dll.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        self.dll.lua_pcall.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        self.dll.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        self.dll.lua_tolstring.restype = ctypes.c_char_p
        self.dll.lua_settop.argtypes = [ctypes.c_void_p, ctypes.c_int]
        self.dll.lua_pushlstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]
        self.dll.lua_pushlstring.restype = ctypes.c_void_p
        self.dll.lua_setfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
        self.dll.lua_close.argtypes = [ctypes.c_void_p]
        self.state = self.dll.luaL_newstate()
        if not self.state:
            raise RuntimeError('Cannot allocate Lua test state')
        self.dll.luaL_openlibs(self.state)

    def globals(self):
        if self.backend is not None:
            return self.backend.globals()
        return Globals(self)

    def execute(self, source):
        if self.backend is not None:
            return self.backend.execute(source)
        if self.dll.luaL_loadstring(self.state, source.encode('utf-8')) or self.dll.lua_pcall(self.state, 0, 0, 0):
            error = self.dll.lua_tolstring(self.state, -1, None).decode('utf-8', errors='replace')
            self.dll.lua_settop(self.state, 0)
            raise RuntimeError(error)
        self.dll.lua_settop(self.state, 0)

    def close(self):
        if getattr(self, 'backend', None) is not None:
            self.backend = None
            return
        if getattr(self, 'state', None):
            self.dll.lua_close(self.state)
            self.state = None
        if getattr(self, 'directory', None):
            self.directory.close()
            self.directory = None

    def __del__(self):
        self.close()
