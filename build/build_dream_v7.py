"""Snow Dream v7 = v6 + AMI USB 'device connected' beeps disabled (UsbRtDxe + UsbRtSmm).
In both modules the beep routine starts with
    test dword [rax+6C9h], 200000h ; je skip ; test byte [rax], 1 ; je skip ; mov edx,43h ...
The first 'je skip' (74 xx) becomes 'jmp skip' (EB xx), so the routine never touches the speaker.
StatusCode error beep codes are left alone. Same size, in place; nothing moves.
python -I build_dream_v7.py <JYRPL014_mod6.bin> <out.bin> <workdir>"""
import sys, os, struct, lzma, hashlib, uuid, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quietboot
src, out, wd = sys.argv[1:4]
os.makedirs(wd, exist_ok=True)
img = bytearray(open(src, 'rb').read())
assert hashlib.sha256(img).hexdigest() == '6264ffac3f7da70a54a630d0aa1fb08f554bd87c6988bbc03968631a4a90da49', 'input is not v6'
GUID_LZMA = uuid.UUID('EE4E5898-3914-4259-9D6E-DC7BD79403CF').bytes_le

FV = 0x470000; FILE = 0x4910C0
fv_end = FV + struct.unpack_from('<Q', img, FV + 0x20)[0]
sec = FILE + 24; ss = int.from_bytes(img[sec:sec + 3], 'little'); doff = struct.unpack_from('<H', img, sec + 20)[0]
assert img[sec + 3] == 0x02 and img[sec + 4:sec + 20] == GUID_LZMA
raw = bytearray(lzma.decompress(bytes(img[sec + doff:sec + ss]), format=lzma.FORMAT_ALONE))

def ffs_attr_of(buf, pos):
    for o in range(pos & ~7, max(0, pos - 0x200000), -8):
        sz = int.from_bytes(buf[o + 0x14:o + 0x17], 'little'); t = buf[o + 0x12]
        if o + sz > pos and 0x01 <= t <= 0x0F and buf[o + 0x17] in (0xF8, 0xF0) and 24 < sz < 0x400000:
            h = bytearray(buf[o:o + 24]); h[0x11] = 0; h[0x17] = 0
            if sum(h) & 0xFF == 0: return o, buf[o + 0x13], bytes(buf[o:o + 16])
    raise SystemExit(f'no FFS header for {pos:#x}')


pat = re.compile(rb'\xf7\x80\xc9\x06\x00\x00\x00\x00\x20\x00\x74([\x30-\x40])\xf6\x00\x01\x74[\x30-\x40]\xba\x43\x00\x00\x00\xb0\xb6\xee')
hits = [m.start() for m in pat.finditer(raw)]
assert len(hits) == 2, [hex(h) for h in hits]
for h in hits:
    a = h + 10
    assert raw[a] == 0x74
    raw[a] = 0xEB
    fo, attr, g = ffs_attr_of(raw, a); assert not attr & 0x40
    print(f'  USB beep disabled @ DXE+{a:#x} (FFS {uuid.UUID(bytes_le=g)} @ {fo:#x}): je -> jmp')

c = quietboot._sdk(bytes(raw), wd, 'dxe_v7')
section = bytearray(img[sec:sec + doff]); section[0:3] = (doff + len(c)).to_bytes(3, 'little'); section += c
newfile = quietboot._hdr(img[FILE:FILE + 24], 24 + len(section)) + bytes(section)
old_end = FILE + 24 + ss
assert all(b == 0xFF for b in img[(old_end + 7) & ~7:fv_end]) and FILE + len(newfile) <= fv_end
img[FILE:fv_end] = newfile + b'\xff' * (fv_end - FILE - len(newfile))
print(f'  DXE file {ss + 24} -> {len(newfile)}, free after {fv_end - FILE - len(newfile)}')
open(out, 'wb').write(img)
open(os.path.join(wd, 'dxe_v7_expected.raw'), 'wb').write(raw)
print('sha256', hashlib.sha256(img).hexdigest())
