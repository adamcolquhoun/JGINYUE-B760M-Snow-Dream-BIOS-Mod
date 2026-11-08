"""Apply beep_v2 to a full image: B760I mod8 -> mod9 (stub v2 + USB beeps off), Snow Dream v7 -> v8 (stub v2; USB beeps already off).
python -I build_beep_v2.py <b760i|snowdream> <in.bin> <out.bin> <workdir>"""
import sys, os, struct, lzma, hashlib, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quietboot, beep_v2
board, src, out, wd = sys.argv[1:5]
os.makedirs(wd, exist_ok=True)
CFG = {'b760i': (0x4D10C0, '60dd920842c96d7d1d46fe33d3f375767f7cec560d682efea3f13d57b1cab9ed'),
       'snowdream': (0x4910C0, 'aa689bb935da68e63b7abb235a65ab44ce738ae3c32b7cc540262cd31c871751')}
FILE, want = CFG[board]
img = bytearray(open(src, 'rb').read())
assert hashlib.sha256(img).hexdigest() == want, 'unexpected input image'
GUID_LZMA = uuid.UUID('EE4E5898-3914-4259-9D6E-DC7BD79403CF').bytes_le
FV = 0x470000
fv_end = FV + struct.unpack_from('<Q', img, FV + 0x20)[0]
sec = FILE + 24; ss = int.from_bytes(img[sec:sec + 3], 'little'); doff = struct.unpack_from('<H', img, sec + 20)[0]
assert img[sec + 3] == 0x02 and img[sec + 4:sec + 20] == GUID_LZMA
raw = bytearray(lzma.decompress(bytes(img[sec + doff:sec + ss]), format=lzma.FORMAT_ALONE))
beep_v2.replace_stub(raw)
n = beep_v2.disable_usb_beeps(raw)
assert n == (2 if board == 'b760i' else 0)
c = quietboot._sdk(bytes(raw), wd, 'dxe_beep2')
section = bytearray(img[sec:sec + doff]); section[0:3] = (doff + len(c)).to_bytes(3, 'little'); section += c
newfile = quietboot._hdr(img[FILE:FILE + 24], 24 + len(section)) + bytes(section)
old_end = FILE + 24 + ss
assert all(b == 0xFF for b in img[(old_end + 7) & ~7:fv_end]) and FILE + len(newfile) <= fv_end
img[FILE:fv_end] = newfile + b'\xff' * (fv_end - FILE - len(newfile))
print(f'  DXE file {ss + 24} -> {len(newfile)}, free after {fv_end - FILE - len(newfile)}')
open(out, 'wb').write(img)
open(os.path.join(wd, 'dxe_beep2_expected.raw'), 'wb').write(raw)
print('sha256', hashlib.sha256(img).hexdigest())
