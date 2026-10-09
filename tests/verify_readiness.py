"""Verify vanilla test supplies and compile Lua with the installed engine DLL."""
import ctypes
import os
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]


def records(path):
    with path.open('rb') as stream:
        while header := stream.read(16):
            if len(header) != 16:
                raise ValueError('Truncated ESM header')
            tag, size, _, _ = struct.unpack('<4sIII', header)
            payload = stream.read(size)
            if len(payload) != size:
                raise ValueError('Truncated ESM record')
            if tag not in (b'SPEL', b'ENCH', b'BOOK', b'CLOT', b'FACT', b'ACTI', b'SCPT'):
                continue
            fields = {}
            offset = 0
            while offset < size:
                if offset + 8 > size:
                    raise ValueError('Truncated ESM subrecord header')
                key, length = struct.unpack_from('<4sI', payload, offset)
                offset += 8
                if offset + length > size:
                    raise ValueError('Truncated ESM subrecord')
                fields.setdefault(key, []).append(payload[offset:offset + length])
                offset += length
            name = (fields[b'SCHD'][0][:32] if tag == b'SCPT' else fields[b'NAME'][0]).rstrip(b'\0').lower()
            yield tag, name, fields


def verify_data(path):
    data = {(tag, name): fields for tag, name, fields in records(path)}
    for name in (b'imperial cult', b'temple'):
        assert (b'FACT', name) in data, f'Missing faction {name!r}'
    for name in (b'divine intervention', b'almsivi intervention', b'mark', b'recall'):
        fields = data[b'SPEL', name]
        assert struct.unpack_from('<I', fields[b'SPDT'][0])[0] == 0, f'Not a normal spell: {name}'
    for name in (b'divine intervention', b'almsivi intervention'):
        effect = struct.unpack_from('<H', data[b'SPEL', name][b'ENAM'][0])[0]
        for tag, enchant_type in ((b'BOOK', 0), (b'CLOT', 2)):
            matches = []
            for (record_tag, record_id), fields in data.items():
                if record_tag != tag or b'ENAM' not in fields:
                    continue
                enchant_id = fields[b'ENAM'][0].rstrip(b'\0').lower()
                enchantment = data.get((b'ENCH', enchant_id))
                if not enchantment:
                    continue
                kind = struct.unpack_from('<I', enchantment[b'ENDT'][0])[0]
                effects = [struct.unpack_from('<H', value)[0] for value in enchantment.get(b'ENAM', [])]
                if kind == enchant_type and effect in effects:
                    matches.append(record_id)
            assert matches, f'Missing {tag!r} fixture for {name!r}'
            print(f'PASS: {name.decode()} {tag.decode()} fixture: {min(matches).decode()}')
    print('PASS: four ordinary spells and both factions exist in Morrowind.esm')
    for name, script in ((b'furn_imp_altar_cure_01', b'shrineimperial'),
                         (b'furn_shrine_tribunal_cure_01', b'shrinetemple')):
        fields = data[b'ACTI', name]
        assert fields[b'SCRI'][0].rstrip(b'\0').lower() == script
    for name in (b'shrineimperial', b'shrinetemple', b'shrineveloth', b'shrinevivecfury',
                 b'shrinevivechumility', b'shrinevivecmystery'):
        source = data[b'SCPT', name][b'SCTX'][0].decode('cp1252').lower()
        assert 'questionstate' in source and 'button' in source
        assert 'cure poison touch' in source
    for name in (b"lady's grace shrine", b'restore attributes', b'cure poison touch'):
        assert (b'SPEL', name) in data
    print('PASS: both shrine templates retain vanilla scripts; six supported service scripts exist')


def verify_lua(engine):
    with os.add_dll_directory(str(engine)):
        lua = ctypes.CDLL(str(engine / 'lua51.dll'))
        lua.luaL_newstate.restype = ctypes.c_void_p
        lua.luaL_loadfile.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        lua.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        lua.lua_tolstring.restype = ctypes.c_char_p
        lua.lua_settop.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lua.lua_close.argtypes = [ctypes.c_void_p]
        state = lua.luaL_newstate()
        if not state:
            raise RuntimeError('Cannot allocate Lua state')
        try:
            for path in sorted((ROOT / 'scripts').rglob('*.lua')):
                if lua.luaL_loadfile(state, os.fsencode(path)):
                    raise RuntimeError(lua.lua_tolstring(state, -1, None).decode())
                lua.lua_settop(state, 0)
        finally:
            lua.lua_close(state)
    print('PASS: all production and fixture Lua scripts compile with engine Lua 5.1')


if __name__ == '__main__':
    verify_data(Path(sys.argv[1] if len(sys.argv) > 1 else
                     r'D:\Steam\steamapps\common\Morrowind\Data Files\Morrowind.esm'))
    verify_lua(Path(sys.argv[2] if len(sys.argv) > 2 else r'C:\Program Files\OpenMW 0.51.0'))
