"""Exact HII string-package walker (UEFI 2.x SIBT blocks)."""
import struct
def walk(d, o):
    """Return (lang, langname_id, blocks, max_id, end_off) for string package at o. Raises on unknown block."""
    L = int.from_bytes(d[o:o + 3], 'little'); hs, so = struct.unpack_from('<II', d, o + 4)
    lname = struct.unpack_from('<H', d, o + 44)[0]
    lang = d[o + 46:o + hs - 1].decode()
    p = o + so; sid = 1; blocks = []; end = o + L
    def z8(q):
        return d.index(b'\0', q) + 1
    def z16(q):
        while d[q:q + 2] != b'\0\0': q += 2
        return q + 2
    while True:
        if p >= end: raise ValueError('ran past package end')
        t = d[p]; q = p + 1; n = 0
        if t == 0x00: blocks.append((p, t, 0)); return lang, lname, blocks, sid - 1, p + 1
        elif t == 0x10: q = z8(q); n = 1
        elif t == 0x11: q = z8(q + 1); n = 1
        elif t == 0x12: c = struct.unpack_from('<H', d, q)[0]; q += 2; n = c; [q := z8(q) for _ in range(c)]
        elif t == 0x13: c = struct.unpack_from('<H', d, q + 1)[0]; q += 3; n = c; [q := z8(q) for _ in range(c)]
        elif t == 0x14: q = z16(q); n = 1
        elif t == 0x15: q = z16(q + 1); n = 1
        elif t == 0x16: c = struct.unpack_from('<H', d, q)[0]; q += 2; n = c; [q := z16(q) for _ in range(c)]
        elif t == 0x17: c = struct.unpack_from('<H', d, q + 1)[0]; q += 3; n = c; [q := z16(q) for _ in range(c)]
        elif t == 0x20: q += 2; n = 1
        elif t == 0x21: n = struct.unpack_from('<H', d, q)[0]; q += 2
        elif t == 0x22: n = d[q]; q += 1
        elif t == 0x30: q = p + d[p + 2]
        elif t == 0x31: q = p + struct.unpack_from('<H', d, p + 2)[0]
        elif t == 0x32: q = p + struct.unpack_from('<I', d, p + 2)[0]
        else: raise ValueError(f'unknown block {t:#x} at {p:#x}')
        blocks.append((p, t, n)); sid += n; p = q
