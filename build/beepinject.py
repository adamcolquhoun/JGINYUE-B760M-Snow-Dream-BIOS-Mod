"""Shared helpers: boot-beep injection into CapsuleRuntimeDxe (inside a decompressed DXE FV) and the
8254 clock-gate default (PchSetup+0x6BE in StdDefaults)."""
import os, struct, re, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
STUB = open(os.path.join(HERE, 'beep.bin'), 'rb').read()[:0x67]
assert STUB[:3] == b'SQR' and STUB[-5:] == b'\xe9\x00\x00\x00\x00'
CAPSULE_PE_SHA = 'd6aeb20d7c5442715842f60c7297425d421b65bc1cfd8843d9364e482f86b737'

def inject_beep(raw, pe_path):
    """raw: bytearray of the decompressed DXE FV. Patches CapsuleRuntimeDxe in place (same size)."""
    pe = open(pe_path, 'rb').read()
    assert hashlib.sha256(pe).hexdigest() == CAPSULE_PE_SHA, 'unexpected CapsuleRuntimeDxe'
    assert bytes(raw).count(pe) == 1
    base = bytes(raw).index(pe)
    o = struct.unpack_from('<I', pe, 0x3c)[0]; oh = o + 24; osz = struct.unpack_from('<H', pe, o + 20)[0]
    ep = struct.unpack_from('<I', pe, oh + 16)[0]
    s = oh + osz                                   # first section header = .text
    assert pe[s:s + 5] == b'.text'
    vs, va, rs, rp = struct.unpack_from('<IIII', pe, s + 8)
    assert (vs, va, rs, rp, ep) == (0xc6f, 0x1000, 0xe00, 0x400, 0x1124)
    cave_off = (vs + 15) & ~15                     # 0xc70 inside .text
    assert cave_off + len(STUB) <= rs
    assert pe[rp + cave_off:rp + cave_off + len(STUB)] == b'\0' * len(STUB), 'cave not empty'
    stub = bytearray(STUB)
    cave_rva = va + cave_off
    disp = ep - (cave_rva + len(stub))
    stub[-4:] = struct.pack('<i', disp)
    a = base + rp + cave_off
    raw[a:a + len(stub)] = stub
    struct.pack_into('<I', raw, base + s + 8, cave_off + len(stub))      # .text VirtualSize covers the stub
    struct.pack_into('<I', raw, base + oh + 16, cave_rva)                # AddressOfEntryPoint -> stub
    print(f'  boot beep: CapsuleRuntimeDxe entry {ep:#x} -> stub at {cave_rva:#x} ({len(stub)} bytes, jmp back disp {disp})')
    return base

def set_8254_default(img, value=2):
    """StdDefaults PchSetup+0x6BE: 'Enable 8254 Clock Gate' -> 2 (Enabled In Runtime and S3 Resume)."""
    hits = []
    for m in re.finditer(b'NVAR', img[0x400000:0x430000]):
        o = 0x400000 + m.start(); at = img[o + 9]
        if at & 0x08 or not at & 0x02: continue
        p = o + 11; e = img.index(b'\0', p)
        if img[p:e] == b'PchSetup': hits.append((e + 1, o + struct.unpack_from('<H', img, o + 4)[0]))
    assert len(hits) == 1, hits
    a = hits[0][0] + 0x6BE; assert a < hits[0][1]
    assert img[a] in (1, value), f'unexpected 8254CG default {img[a]}'
    old = img[a]; img[a] = value
    print(f'  8254 clock gate default {old} -> {value} at {a:#x}')
    return a
