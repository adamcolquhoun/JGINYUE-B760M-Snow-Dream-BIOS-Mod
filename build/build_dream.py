"""Build the Snow Dream mod v3 from step1.bin (vendor JYRPL014 + 3 StdDefaults edits).
python -I build_dream.py <step1.bin> <post_logo.bmp> <out.bin> <workdir>
  - StdDefaults: Quiet Boot 1 -> 0 (full-screen logo never shown; vendor logo file untouched)
  - DXE FV (LZMA): FADT RESET_VALUE 0x0E; System Language hidden + default -> en-US (index 1);
    Quiet Boot hidden with IFR default Disabled; POST-screen AMI logo BMP replaced (same size);
    zh-chs strings emptied in Setup + AMITSE (language name kept, ids preserved with SKIP2 blocks);
    CJK glyph bitmaps zeroed in the extra font file.
"""
import sys, os, struct, subprocess, hashlib, uuid
LZ = os.environ.get('LZMA_EXE', 'lzma.exe')   # 7-Zip LZMA SDK encoder (bin/x64/lzma.exe)
GUID_LZMA = uuid.UUID('EE4E5898-3914-4259-9D6E-DC7BD79403CF').bytes_le
src, post_bmp, out, wd = sys.argv[1:5]
img = bytearray(open(src, 'rb').read())
os.makedirs(wd, exist_ok=True)

def lzma_sdk(data, name):
    rp = os.path.join(wd, name + '.raw'); cp = os.path.join(wd, name + '.lzma')
    open(rp, 'wb').write(data)
    if os.path.exists(cp): os.remove(cp)
    subprocess.run([LZ, 'e', rp, cp, '-d24'], check=True, capture_output=True)   # 16 MiB dict like EDK2/vendor
    c = open(cp, 'rb').read()
    assert c[:5] == bytes.fromhex('5d00000001') and struct.unpack_from('<Q', c, 5)[0] == len(data)
    return c

def ffs_header(old_hdr, new_size):
    h = bytearray(old_hdr); h[0x14:0x17] = new_size.to_bytes(3, 'little')
    state = h[0x17]; h[0x10] = h[0x11] = h[0x17] = 0
    h[0x10] = (-sum(h)) & 0xFF; h[0x11] = 0xAA; h[0x17] = state
    assert not (h[0x13] & 0x40), 'file uses data checksum'
    return bytes(h)

def replace_lzma_file(file_off, region_end, new_inner, tag):
    """Rebuild FFS file at file_off whose only section is an LZMA GUIDed section; pad with FF to region_end."""
    sec = file_off + 24; ss = int.from_bytes(img[sec:sec + 3], 'little')
    assert img[sec + 3] == 0x02 and img[sec + 4:sec + 20] == GUID_LZMA
    doff = struct.unpack_from('<H', img, sec + 20)[0]
    assert (file_off + 24 + ss + 7) & ~7 >= file_off + int.from_bytes(img[file_off + 0x14:file_off + 0x17], 'little')
    c = lzma_sdk(new_inner, tag)
    section = bytearray(img[sec:sec + doff]); section[0:3] = (doff + len(c)).to_bytes(3, 'little'); section += c
    newfile = ffs_header(img[file_off:file_off + 24], 24 + len(section)) + bytes(section)
    assert file_off + len(newfile) <= region_end, f'{tag}: does not fit'
    old_end = file_off + int.from_bytes(img[file_off + 0x14:file_off + 0x17], 'little')
    assert all(b == 0xFF for b in img[(old_end + 7) & ~7:region_end]), f'{tag}: data after file'
    img[file_off:region_end] = newfile + b'\xff' * (region_end - file_off - len(newfile))
    print(f'{tag}: file {old_end - file_off} -> {len(newfile)} bytes, free {region_end - file_off - len(newfile)}')

# ------------------------------------------------------------------ 1. Quiet Boot default off (StdDefaults: AMITSESetup+0x50)
# (the full-screen boot logo file is left exactly as the vendor shipped it)
import re
hits = []
for m in re.finditer(b'NVAR', img[0x400000:0x430000]):
    o = 0x400000 + m.start(); at = img[o + 9]
    if at & 0x08 or not at & 0x02: continue
    p = o + 11; e = img.index(b'\0', p)
    if img[p:e] == b'AMITSESetup': hits.append((e + 1, o + struct.unpack_from('<H', img, o + 4)[0]))
assert len(hits) == 1, hits
qb = hits[0][0] + 0x50; assert qb < hits[0][1] and img[qb] == 1
img[qb] = 0; print(f'Quiet Boot default 1 -> 0 at {qb:#x}')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'beep'))
import beepinject
beepinject.set_8254_default(img, 2)          # 8254 stays clocked during POST so the speaker works

# ------------------------------------------------------------------ 1b. PEI (uncompressed XIP TE): CF9 0x06 -> 0x0E
def ffs_attr_of(buf, pos):
    for o in range(pos & ~7, max(0, pos - 0x200000), -8):
        sz = int.from_bytes(buf[o + 0x14:o + 0x17], 'little'); t = buf[o + 0x12]
        if o + sz > pos and 0x01 <= t <= 0x0F and buf[o + 0x17] in (0xF8, 0xF0) and 24 < sz < 0x400000:
            h = bytearray(buf[o:o + 24]); h[0x11] = 0; h[0x17] = 0
            if sum(h) & 0xFF == 0: return o, buf[o + 0x13]
    raise SystemExit(f'no FFS header for {pos:#x}')
pei_warm = bytes.fromhex('b006ebba558bec')     # ResetSystemPei warm path: mov al,6 ; jmp -> shared 'mov edx,0CF9h ; out'
hits = [m.start() for m in re.finditer(re.escape(pei_warm), img)]
assert hits == [0xDF82E9, 0xF505C1], [hex(h) for h in hits]
for a in hits:
    img[a + 1] = 0x0E; fo, at = ffs_attr_of(img, a); assert not at & 0x40
    print(f'ResetSystemPei warm reset @ {a:#x}: 0x06 -> 0x0E (FFS @ {fo:#x})')
pei_core = bytes.fromhex('b001eebaf90c00000405ee')      # mov al,1 ; out ; mov edx,0CF9h ; add al,5 ; out  -> add al,0Dh
hits = [m.start() for m in re.finditer(re.escape(pei_core), img)]
assert len(hits) == 1, hits
a = hits[0]; img[a + 9] = 0x0D; fo, at = ffs_attr_of(img, a); assert not at & 0x40
print(f'PeiCore CF9 write @ {a:#x}: 1+5 -> 1+0x0D = 0x0E (FFS @ {fo:#x})')

# ------------------------------------------------------------------ 2. DXE FV
FV = 0x470000; FILE = 0x4910C0
fv_end = FV + struct.unpack_from('<Q', img, FV + 0x20)[0]
sec = FILE + 24; ss = int.from_bytes(img[sec:sec + 3], 'little'); doff = struct.unpack_from('<H', img, sec + 20)[0]
import lzma
raw = bytearray(lzma.decompress(bytes(img[sec + doff:sec + ss]), format=lzma.FORMAT_ALONE))
orig_raw = bytes(raw)

def patch(off, old, new, what):
    assert raw[off:off + len(old)] == old, f'{what}: unexpected bytes {raw[off:off+len(old)].hex()}'
    assert len(old) == len(new)
    raw[off:off + len(new)] = new; print(f'  {what} @ {off:#x}')

def find1(needle, what):
    assert orig_raw.count(needle) == 1, f'{what}: {orig_raw.count(needle)} matches'
    return orig_raw.index(needle)

# 2a FADT reset value (ACPI driver)
o = find1(bytes.fromhex('48c74078f90c0000c6808000000006c74070e5c60300'), 'FADT store')
patch(o + 14, b'\x06', b'\x0e', 'FADT RESET_VALUE 06->0E')

# 2a' every direct CF9 'hard reset' (0x06) write in DXE/SMM -> full reset 0x0E (same sites as B760I mod4)
EXF = os.environ['EXTRACTED_BIOS'] + '/FV01_0470000_8C8CE578/002_9E21FD93-9C72-4C15-8C4B-E77F1DB2D792/fv1/'
SITES = [('160_ResetSystemRuntimeDxe', [0xb19]), ('217_SbRunSmm', [0x1f95]), ('156_CardCheckDxe', [0x611, 0x6c3]),
         ('230_PlatformInitAdvancedSmm', [0xf7f]), ('241_UsbRtSmm', [0x1a222])]
for mod, offs in SITES:
    pe = open(EXF + mod + '/1_PE32.efi', 'rb').read()
    assert orig_raw.count(pe) == 1, mod
    b = orig_raw.index(pe)
    for o in offs:
        a = b + o
        assert orig_raw[a - 5:a] == b'\xba\xf9\x0c\x00\x00' or (orig_raw[a - 1] == 0xEE and orig_raw[a + 2] == 0xEB), (mod, hex(o))
        patch(a, b'\xb0\x06', b'\xb0\x0e', f'{mod}+{o:#x} CF9 0x06 -> 0x0E')

# 2a'' boot beep stub in CapsuleRuntimeDxe
beepinject.inject_beep(raw, EXF + '157_CapsuleRuntimeDxe/1_PE32.efi')

# 2b System Language: SuppressIf (EqIdVal Q0x123a==0xffff) -> SuppressIf (TRUE AND TRUE); defaults 0 -> 1 (en-US)
o = find1(bytes.fromhex('0a8212063a12ffff0594'), 'language suppressif')
patch(o + 2, bytes.fromhex('12063a12ffff'), bytes.fromhex('460246021502'), 'System Language hidden')
oneof = o + 8; L = raw[oneof + 1] & 0x7F
assert struct.unpack_from('<H', raw, oneof + 6)[0] == 0x0008
p = oneof + L; seen = 0
while raw[p] != 0x29:
    op, ln = raw[p], raw[p + 1] & 0x7F
    if op == 0x5B:
        did, ty = struct.unpack_from('<HB', raw, p + 2); assert ty == 1 and ln == 7
        patch(p + 5, b'\x00\x00', b'\x01\x00', f'System Language default id={did} -> 1 (en-US)'); seen += 1
    p += ln
assert seen == 2

# 2c Quiet Boot: hidden in place (CheckBox and all referenced opcodes keep their offsets) + AMITSESetupData record
import quietboot
quietboot.hide_quiet_boot(raw, wd)

# 2c' POST-screen logo (FREEFORM 63819805..., drawn by AMITSE): 378x100 24-bit BMP, same size in place
new_bmp = open(post_bmp, 'rb').read()
POST_GUID = uuid.UUID('63819805-67BB-46EF-AA8D-1524A19A01E4').bytes_le
fo = [m.start() for m in re.finditer(re.escape(POST_GUID), orig_raw) if orig_raw[m.start() + 0x12] == 0x02]
assert len(fo) == 1; fo = fo[0]; s = fo + 24
assert orig_raw[s + 3] == 0x19 and int.from_bytes(orig_raw[s:s + 3], 'little') == 4 + len(new_bmp)
assert orig_raw[s + 4:s + 4 + 54] == new_bmp[:54], 'BMP header differs'
patch(s + 4, orig_raw[s + 4:s + 4 + len(new_bmp)], new_bmp, 'POST-screen AMI logo replaced')

# 2d zh-chs string packages: keep language name (id 1), SKIP2 the rest, END, zero fill
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hiistr
def blank_zh(src, dst, pkg_off, what):
    lang, lname, blocks, maxid, endp = hiistr.walk(src, pkg_off)
    assert lang == 'zh-chs' and lname == 1
    L = int.from_bytes(src[pkg_off:pkg_off + 3], 'little'); hs = struct.unpack_from('<I', src, pkg_off + 4)[0]
    first = blocks[0]; assert first[1] == 0x14
    p = first[0] + 1
    while src[p:p + 2] != b'\0\0': p += 2
    name_blk = src[first[0]:p + 2]
    body = bytearray(name_blk); rest = maxid - 1
    while rest:
        n = min(rest, 0xFFFF); body += b'\x21' + struct.pack('<H', n); rest -= n
    body += b'\x00'
    new = bytearray(src[pkg_off:pkg_off + hs]) + body
    new += b'\0' * (L - len(new))
    dst[pkg_off:pkg_off + L] = new
    chk = hiistr.walk(dst, pkg_off); assert chk[3] == maxid and chk[0] == 'zh-chs'
    print(f'  {what}: zh-chs {len([b for b in blocks if b[1]==0x14])} strings removed, ids 1..{maxid} kept, {L} bytes')
import re
ZH_HDR = rb'[\x00-\xff]{3}\x04\x35\x00\x00\x00\x35\x00\x00\x00'   # HdrSize 0x35 = 46 + len("zh-chs\0")
def blank_all_zh(src, dst, what):
    n = 0
    for m in re.finditer(ZH_HDR, src):
        o = m.start()
        if src[o + 46:o + 53] == b'zh-chs\0' and int.from_bytes(src[o:o + 3], 'little') > 0x100:
            blank_zh(src, dst, o, f'{what} string package @{o:#x}'); n += 1
    return n
assert blank_all_zh(orig_raw, raw, 'DXE') == 1

# 2d' AMITSE is LZMA-compressed again inside the DXE FV: decompress, blank, recompress, fill the gap with a pad file
AMITSE = uuid.UUID('B1DA0ADF-4F77-4070-A88E-BFFE1C60529A').bytes_le
fo = [m.start() for m in re.finditer(re.escape(AMITSE), orig_raw) if orig_raw[m.start() + 0x12] == 0x07]
assert len(fo) == 1; fo = fo[0]
fsz = int.from_bytes(raw[fo + 0x14:fo + 0x17], 'little'); old_next = (fo + fsz + 7) & ~7
s = fo + 24; ss = int.from_bytes(raw[s:s + 3], 'little'); sdo = struct.unpack_from('<H', raw, s + 20)[0]
assert raw[s + 3] == 0x02 and raw[s + 4:s + 20] == GUID_LZMA and s + ss == fo + fsz, 'unexpected AMITSE layout'
tse_inner = lzma.decompress(bytes(raw[s + sdo:s + ss]), format=lzma.FORMAT_ALONE)
tse_new = bytearray(tse_inner)
assert blank_all_zh(tse_inner, tse_new, 'AMITSE') == 1
c = lzma_sdk(bytes(tse_new), 'amitse')
sec_new = bytearray(raw[s:s + sdo]); sec_new[0:3] = (sdo + len(c)).to_bytes(3, 'little'); sec_new += c
file_new = ffs_header(raw[fo:fo + 24], 24 + len(sec_new)) + bytes(sec_new)
new_next = (fo + len(file_new) + 7) & ~7; gap = old_next - new_next
assert gap == 0 or gap >= 24, f'AMITSE gap {gap} cannot hold a pad file'
blob = bytearray(file_new) + b'\xff' * (new_next - fo - len(file_new))
if gap:
    pad = bytearray(24); pad[0x12] = 0xF0; pad[0x13] = 0x00; pad[0x14:0x17] = gap.to_bytes(3, 'little')
    pad[0x10] = (-sum(pad)) & 0xFF; pad[0x11] = 0xAA; pad[0x17] = 0xF8      # state as the vendor files (erase polarity 1)
    blob += pad + b'\xff' * (gap - 24)
assert len(blob) == old_next - fo
raw[fo:old_next] = blob
print(f'  AMITSE file {fsz} -> {len(file_new)} bytes, pad file {gap} bytes')

# 2e font file: zero bitmaps of CJK (U+4E00-9FFF) wide glyphs; structure and code points unchanged
sub = bytes.fromhex('9174fea7542c724fb80e7649a8210193')
o = find1(sub + bytes.fromhex('d4770007'), 'font package') + 16   # simple font package, length 0x77d4 = 30676
nn, nw = struct.unpack_from('<HH', raw, o + 4); assert 8 + nn * 22 + nw * 44 == int.from_bytes(raw[o:o + 3], 'little')
w = o + 8 + nn * 22; z = 0
for i in range(nw):
    g = w + 44 * i; cp = struct.unpack_from('<H', raw, g)[0]
    if 0x4E00 <= cp <= 0x9FFF:
        raw[g + 3:g + 41] = b'\0' * 38; z += 1     # GlyphCol1[19] + GlyphCol2[19]; keep code point, attributes, pad
print(f'  font: {z} CJK glyph bitmaps zeroed of {nw} wide')

# FFS data checksums inside the DXE FV for touched files
diff = [i for i in range(len(raw)) if raw[i] != orig_raw[i]] if False else None
def fv_files(buf):
    i = buf.find(b'_FVH')
    while i >= 0:
        fvs = i - 0x28; flen = struct.unpack_from('<Q', buf, fvs + 0x20)[0]
        hl = struct.unpack_from('<H', buf, fvs + 0x30)[0]; ext = struct.unpack_from('<H', buf, fvs + 0x34)[0]
        o = fvs + (ext + struct.unpack_from('<I', buf, fvs + ext + 16)[0] if ext else hl); o = (o + 7) & ~7
        while o + 24 <= fvs + flen and buf[o:o + 24] != b'\xff' * 24:
            sz = int.from_bytes(buf[o + 0x14:o + 0x17], 'little'); yield o, sz
            o = (o + sz + 7) & ~7
        i = buf.find(b'_FVH', fvs + flen)
for fo, fsz in fv_files(raw):
    if raw[fo:fo + fsz] != orig_raw[fo:fo + fsz]:
        attr = raw[fo + 0x13]
        print(f'  touched FFS @ {fo:#x} attr {attr:#x} chk {raw[fo+0x11]:#x}')
        assert not (attr & 0x40), 'data checksum needed - not expected'

replace_lzma_file(FILE, fv_end, bytes(raw), 'dxe')
open(os.path.join(wd, 'dxe_mod2.raw'), 'wb').write(raw)
open(out, 'wb').write(img)
print('sha256', hashlib.sha256(img).hexdigest())
