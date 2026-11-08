"""Beep update shared by B760I mod9 and Snow Dream v8 (operates on a decompressed DXE FV that already holds the
v1 stub in CapsuleRuntimeDxe):
  - replace_stub(raw): rewrite the stub at RVA 0x1C70 with beep.bin v2 (1 kHz, counter 2 parked afterwards),
    re-point the trailing jmp to the original entry 0x1124, update .text VirtualSize.
  - disable_usb_beeps(raw): AMI USB 'device connected' beep in UsbRtDxe + UsbRtSmm: first 'je skip' -> 'jmp skip'.
"""
import os, struct, re

HERE = os.path.dirname(os.path.abspath(__file__))
OLD_STUB_LEN = 0x67
ORIG_EP, CAVE_RVA, TEXT_VA, TEXT_RAWPTR, TEXT_RAWSIZE = 0x1124, 0x1C70, 0x1000, 0x400, 0xE00

def _new_stub():
    b = open(os.path.join(HERE, 'beep.bin'), 'rb').read()
    n = b.index(b'\xe9\x00\x00\x00\x00') + 5          # stub ends with jmp rel32 placeholder
    s = b[:n]
    assert s[:3] == b'SQR' and b'\xb0\xa9\xe6\x42\xb0\x04\xe6\x42' in s and b'\xb0\xb0\xe6\x43' in s
    return bytearray(s)

def replace_stub(raw):
    # locate the v1 stub: 'push rbx; push rcx; push rdx; mov eax,16h; xor ecx,ecx; cpuid'
    sig = bytes.fromhex('535152b81600000031c90fa2')
    hits = [m.start() for m in re.finditer(re.escape(sig), raw)]
    assert len(hits) == 1, [hex(h) for h in hits]
    a = hits[0]
    base = a - (TEXT_RAWPTR + (CAVE_RVA - TEXT_VA))
    assert raw[base:base + 2] == b'MZ'
    o = base + struct.unpack_from('<I', raw, base + 0x3c)[0]; oh = o + 24; osz = struct.unpack_from('<H', raw, o + 20)[0]
    assert struct.unpack_from('<I', raw, oh + 16)[0] == CAVE_RVA, 'entry point is not the stub'
    s = oh + osz; assert raw[s:s + 5] == b'.text'
    vs, va, rs, rp = struct.unpack_from('<IIII', raw, s + 8)
    assert (va, rs, rp) == (TEXT_VA, TEXT_RAWSIZE, TEXT_RAWPTR) and vs == (CAVE_RVA - TEXT_VA) + OLD_STUB_LEN
    old = bytes(raw[a:a + OLD_STUB_LEN])
    assert old[-5] == 0xE9 and struct.unpack_from('<i', old, OLD_STUB_LEN - 4)[0] == ORIG_EP - (CAVE_RVA + OLD_STUB_LEN)
    assert b'\xb0\x54\xe6\x42\xb0\x02\xe6\x42' in old, 'v1 stub (2 kHz) not found'
    stub = _new_stub()
    end_off = (CAVE_RVA - TEXT_VA) + len(stub)
    assert end_off <= TEXT_RAWSIZE
    assert all(x == 0 for x in raw[a + OLD_STUB_LEN:a + len(stub)]), 'cave after old stub not empty'
    struct.pack_into('<i', stub, len(stub) - 4, ORIG_EP - (CAVE_RVA + len(stub)))
    raw[a:a + len(stub)] = stub
    struct.pack_into('<I', raw, s + 8, end_off)
    print(f'  boot beep: stub v2 ({len(stub)} bytes, 1 kHz, counter 2 parked) @ DXE+{a:#x}, .text VirtualSize {vs:#x} -> {end_off:#x}')
    return a

USB_BEEP = re.compile(rb'\xf7\x80\xc9\x06\x00\x00\x00\x00\x20\x00(\x74|\xeb)[\x30-\x40]\xf6\x00\x01\x74[\x30-\x40]\xba\x43\x00\x00\x00\xb0\xb6\xee')

def disable_usb_beeps(raw):
    hits = [m.start() for m in USB_BEEP.finditer(raw)]
    assert len(hits) == 2, [hex(h) for h in hits]
    n = 0
    for h in hits:
        if raw[h + 10] == 0x74:
            raw[h + 10] = 0xEB; n += 1
            print(f'  USB device beep disabled @ DXE+{h + 10:#x}: je -> jmp')
    return n
