"""Hide the Quiet Boot option without moving any IFR opcode that AMITSESetupData references.

IFR (in the Setup driver, inside the decompressed DXE FV), same total length, CheckBox stays at its offset:
  before: [NumLock Default0 6][NumLock Default1 6][End 2] CheckBox(QuietBoot) [Default0 6][Default1 6][End 2]
  after:  [NumLock Default0 len 8 (value kept, 2 pad bytes)][End 2][SuppressIf 2][TRUE 2]
          CheckBox(QuietBoot) [Default0 len 10 = value 0 (Disabled), 4 pad bytes][End 2][End 2]
AMITSESetupData (nested LZMA FFS FE612B72...): Quiet Boot control record -> conditional at -4 (the SuppressIf),
  +0x2C = 0xFFFFFFFF, exactly like the vendor's own 'SuppressIf TRUE' controls (e.g. Limit CPUID).
"""
import re, struct, uuid, lzma, os, subprocess

LZ = os.environ.get('LZMA_EXE', 'lzma.exe')   # 7-Zip LZMA SDK encoder (bin/x64/lzma.exe)
GUID_LZMA = uuid.UUID('EE4E5898-3914-4259-9D6E-DC7BD79403CF').bytes_le
SETUPDATA_GUID = uuid.UUID('FE612B72-203C-47B1-8560-A66D946EB371').bytes_le

PAT = re.compile(rb'\x5b\x06\x00\x00\x00(.)\x5b\x06\x01\x00\x00(.)\x29\x02'           # NumLock Def0, Def1, End
                 rb'(\x06\x8e....(..)..\x50\x00\x00\x00)'                                 # CheckBox Quiet Boot (VarOffset 0x50)
                 rb'\x5b\x06\x00\x00\x00[\x00\x01]\x5b\x06\x01\x00\x00[\x00\x01]\x29\x02', re.S)

def _sdk(data, wd, tag):
    rp = os.path.join(wd, tag + '.raw'); cp = os.path.join(wd, tag + '.lzma')
    open(rp, 'wb').write(data)
    if os.path.exists(cp): os.remove(cp)
    subprocess.run([LZ, 'e', rp, cp, '-d24'], check=True, capture_output=True)
    c = open(cp, 'rb').read()
    assert c[:5] == bytes.fromhex('5d00000001') and struct.unpack_from('<Q', c, 5)[0] == len(data)
    return c

def _hdr(old, size):
    h = bytearray(old); h[0x14:0x17] = size.to_bytes(3, 'little'); assert not h[0x13] & 0x40
    st = h[0x17]; h[0x10] = h[0x11] = h[0x17] = 0; h[0x10] = (-sum(h)) & 0xFF; h[0x11] = 0xAA; h[0x17] = st
    return bytes(h)

def replace_nested_lzma_file(raw, fo, new_inner, wd, tag):
    """FFS at fo (8-aligned) whose single section is an LZMA GUIDed section; keep the next file in place (pad file)."""
    fsz = int.from_bytes(raw[fo + 0x14:fo + 0x17], 'little'); nxt = (fo + fsz + 7) & ~7
    s = fo + 24; ss = int.from_bytes(raw[s:s + 3], 'little'); do = struct.unpack_from('<H', raw, s + 20)[0]
    assert raw[s + 3] == 0x02 and raw[s + 4:s + 20] == GUID_LZMA and s + ss == fo + fsz
    c = _sdk(new_inner, wd, tag)
    sec = bytearray(raw[s:s + do]); sec[0:3] = (do + len(c)).to_bytes(3, 'little'); sec += c
    f = _hdr(raw[fo:fo + 24], 24 + len(sec)) + bytes(sec)
    nn = (fo + len(f) + 7) & ~7; gap = nxt - nn
    assert gap == 0 or gap >= 24, f'{tag}: gap {gap}'
    blob = bytearray(f) + b'\xff' * (nn - fo - len(f))
    if gap:
        pad = bytearray(24); pad[0x12] = 0xF0; pad[0x14:0x17] = gap.to_bytes(3, 'little')
        pad[0x10] = (-sum(pad)) & 0xFF; pad[0x11] = 0xAA; pad[0x17] = 0xF8
        blob += pad + b'\xff' * (gap - 24)
    assert len(blob) == nxt - fo
    raw[fo:nxt] = blob
    print(f'  {tag}: file {fsz} -> {len(f)} bytes, pad file {gap} bytes')

def hide_quiet_boot(raw, wd):
    src = bytes(raw)
    hits = list(PAT.finditer(src)); assert len(hits) == 1, f'quiet boot IFR pattern: {len(hits)} hits'
    m = hits[0]; base = m.start()
    nl_d0_val = m.group(1)[0]
    cb = base + 14; assert src[cb:cb + 2] == b'\x06\x8e'
    qid = struct.unpack_from('<H', src, cb + 6)[0]
    before = bytes([0x5b, 0x08, 0, 0, 0, nl_d0_val, 0, 0]) + b'\x29\x02' + b'\x0a\x82' + b'\x46\x02'
    after = bytes([0x5b, 0x0a, 0, 0, 0, 0, 0, 0, 0, 0]) + b'\x29\x02' + b'\x29\x02'
    assert len(before) == 14 and len(after) == 14
    raw[base:base + 14] = before
    raw[cb + 14:cb + 28] = after
    print(f'  Quiet Boot IFR: SuppressIf TRUE before CheckBox @ {cb:#x} (qid {qid:#x}), default Disabled')

    # form package containing the CheckBox: <len24><0x02> followed by FormSet opcode 0x0E
    def walks_to(o, L):
        p = o + 4
        while p < o + L:
            ln = src[p + 1] & 0x7F
            if ln < 2: return False
            if p == cb: return True
            if p > cb: return False
            p += ln
        return False
    cands = []
    for pm in re.finditer(rb'[\x00-\xff]{3}\x02\x0e', src[max(0, cb - 0x400000):cb]):
        o = max(0, cb - 0x400000) + pm.start(); L = int.from_bytes(src[o:o + 3], 'little')
        if o < cb < o + L and walks_to(o, L): cands.append(o)
    assert len(cands) == 1, [hex(x) for x in cands]
    P = cands[0]
    rel = cb - P

    # AMITSESetupData record
    fos = [x.start() for x in re.finditer(re.escape(SETUPDATA_GUID), src) if x.start() % 8 == 0 and src[x.start() + 0x12] == 0x02]
    assert len(fos) == 1; fo = fos[0]
    s = fo + 24; ss = int.from_bytes(src[s:s + 3], 'little'); do = struct.unpack_from('<H', src, s + 20)[0]
    inner = bytearray(lzma.decompress(src[s + do:s + ss], format=lzma.FORMAT_ALONE))
    recs = [r - 0x20 for r in (x.start() for x in re.finditer(re.escape(struct.pack('<I', rel)), inner))
            if struct.unpack_from('<I', inner, r - 0x20 + 4)[0] == qid]
    assert len(recs) == 1, recs
    r = recs[0]
    assert struct.unpack_from('<iiI', inner, r + 0x24) == (0, 0, 0), inner[r:r + 0x50].hex()
    struct.pack_into('<iI', inner, r + 0x28, -4, 0xFFFFFFFF)
    print(f'  AMITSESetupData: Quiet Boot record @ {r:#x} (ptr {rel:#x}) -> conditional -4')
    replace_nested_lzma_file(raw, fo, bytes(inner), wd, 'amitsesetupdata')
    return cb, P, r
