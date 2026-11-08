# Changelog – JGINYUE B760M Snow Dream D4 modded BIOS

Base image: JGINYUE **JYRPL014** (16 MiB full chip), SHA-256 `312e3bdcece9192135b6fd813761d0b035ae82e62146029b106b93206390b3a5`.
Current release: **v6** – `firmware/JYRPL014_mod6.bin`, SHA-256 `6264ffac3f7da70a54a630d0aa1fb08f554bd87c6988bbc03968631a4a90da49`.

Offsets below are flash (image) offsets unless noted as *DXE+…* (offset inside the decompressed main DXE firmware volume, which is LZMA-compressed in FFS file `9E21FD93-9C72-4C15-8C4B-E77F1DB2D792` at flash `0x4910C0`) or *module+…* (offset inside that PE/TE module).

---

## Complete list of alterations (v6 vs. vendor JYRPL014)

Changed flash areas: `0x400000–0x401FFF` (factory defaults), `0x491000–0x7CCFFF` (main DXE volume), `0xDF8000`, `0xF50000`, `0xF6B000` (one 4 KB block each, PEI code).
**Not changed:** flash descriptor (`0x0–0xFFF`), Intel ME region (`0x1000–0x3D8FFF`, ME 16.1.25.1917 as shipped), CPU microcode, Secure Boot keys (PK/KEK/db/dbx), SMBIOS data, the full-screen logo, the rest of the BIOS region.

### 1. Restart / reset fix

**Problem:** on this board family a *hard reset* (writing `0x06` to the Reset Control Register, I/O port `0xCF9`) powers the system **off** instead of restarting it. Windows restarts (via the ACPI FADT reset register) and *Save Changes and Reset* in BIOS setup both used that value, so "Restart" left the PC switched off.

**Fix:** every `0x06` write to `0xCF9` became `0x0E` (full reset: SYS_RST + RST_CPU + FULL_RST).

| # | Where | Location | Original → New |
|---|---|---|---|
| 1 | ACPI FADT `RESET_VALUE` (built by the ACPI DXE driver; `RESET_REG` = I/O `0xCF9`) | DXE, store `mov byte [rax+80h], 06h` | `06` → `0E` |
| 2 | ResetSystemRuntimeDxe – warm-reset path | module+`0xB19` (`mov al,06h`) | `06` → `0E` |
| 3 | SbRunSmm (SMM) | module+`0x1F95` | `06` → `0E` |
| 4 | CardCheckDxe | module+`0x611` | `06` → `0E` |
| 5 | CardCheckDxe | module+`0x6C3` | `06` → `0E` |
| 6 | PlatformInitAdvancedSmm (SMM) | module+`0xF7F` | `06` → `0E` |
| 7 | UsbRtSmm (SMM) | module+`0x1A222` | `06` → `0E` |
| 8 | ResetSystemPei (FV05, execute-in-place) – warm-reset path | flash `0xDF82EA` (pattern `b0 06 eb ba 55 8b ec`) | `06` → `0E` |
| 9 | ResetSystemPei (FV07 copy) – warm-reset path | flash `0xF505C2` | `06` → `0E` |
| 10 | PeiCore – `mov al,1; out 0CF9h,al; add al,5; out 0CF9h,al` | flash `0xF6BC3B` | `add al,05h` → `add al,0Dh` (writes `0x0E`) |

Every site was located by pattern and checked to be the only match. They are the same modules and module offsets as on the B760I GAMING, where this fix is flashed and confirmed; only the PeiCore flash offset differs (B760I `0xF6BC7B`).
Deliberately left unchanged (as on the B760I): one further CF9 write in PEI module `1BA0062E…` (FV07).

### 2. Factory defaults (StdDefaults NVRAM store)

These are the values used after a flash, CMOS clear or *Load Optimized Defaults*. Your own saved settings override them.

| Setting | Variable + offset | Flash offset | Vendor → Mod |
|---|---|---|---|
| Re-Size BAR Support | `Setup`+`0xC8C` | `0x400D44` | `0` Disabled → `1` **Enabled** |
| CSM Support | `Setup`+`0xCB7` | `0x400D6F` | `1` Enabled → `0` **Disabled** |
| Quiet Boot (full-screen logo) | `AMITSESetup`+`0x50` | `0x400E14` | `1` Enabled → `0` **Disabled** |
| Package C State Limit | `CpuSetup`+`0x4B` | `0x400E74` | `0` → `0xFF` **Auto** |
| Enable 8254 Clock Gate | `PchSetup`+`0x6BE` | `0x401E5D` | `1` Enabled → `2` **Enabled In Runtime and S3 Resume** |

The last one keeps the legacy 8254 timer clocked during POST so the PC speaker can sound (with the vendor default the speaker stays silent). The timer is still gated once the OS runs, so Modern Standby is unaffected.

### 3. Setup menu (IFR in the Setup driver + AMITSESetupData)

All edits are **in place and the same length**. AMI's setup browser uses a prebuilt index (`AMITSESetupData`, FFS `FE612B72-203C-47B1-8560-A66D946EB371`, itself LZMA-compressed inside the DXE volume) that stores the exact position of every setup control, so no referenced IFR opcode may move. After the edits, all 11,532 references were checked and still land on the same opcodes as in the vendor image.

- **System Language hidden.** Its `SuppressIf { EqIdVal Q0x123A == 0xFFFF }` became `SuppressIf { TRUE TRUE AND }` (same 6 bytes). Both of its defaults (standard + manufacturing) changed from `0` (zh-chs) to `1` (en-US); the platform language list is `zh-chs;en-US`.
- **Quiet Boot hidden** (CheckBox, VarStore `AMITSESetup`+`0x50`, page *Boot*):
  - before: `[NumLock Default0][NumLock Default1][End]` `CheckBox` `[Default0=1][Default1=1][End]`
  - after: `[NumLock Default0 (padded to 8 bytes)][End][SuppressIf][TRUE]` `CheckBox` `[Default0=0 (padded to 10 bytes)][End][End]`
  - The CheckBox stays at the same offset. NumLock keeps its standard default; only its redundant manufacturing default was dropped to make room.
  - In AMITSESetupData the Quiet Boot control record's condition pointer was set to the new `SuppressIf` (`+0x28 = -4`, `+0x2C = 0xFFFFFFFF`), the same encoding the vendor uses for its own always-hidden options. 8 bytes changed.

### 4. Chinese language pack removed

- **Strings:** every zh-chs HII string package in Setup and in AMITSE (the AMI setup browser, a nested LZMA stream) was emptied: 2,727 strings in total. Each package keeps its header and the language-name string (id 1). All other string ids are kept with `SKIP2` blocks, so ids and the language list are unchanged, then `END` and zero fill. Package lengths are unchanged.
- **Font:** in the extra font file (`DAC2B117…`, simple font package of 30,676 bytes), the bitmaps of the 615 wide CJK glyphs (U+4E00–U+9FFF) were zeroed. Structure and code points are unchanged.
- The zh-chs entry itself is kept in the language list so the firmware's language handling is unchanged; the System Language option is hidden and defaults to English (see §3).

### 5. Logo

- **Text POST screen logo** (FFS `63819805-67BB-46EF-AA8D-1524A19A01E4`, freeform, drawn by AMITSE): the 378×100 24-bit BMP "ami" logo was replaced by the **American Megatrends** logo, white text and red mark on black (`build/assets/text_screen_logo.bmp`). Same size (113,654 bytes), same BMP header, in place. An identical, unreferenced copy of the old logo in PEI volume FV03 (`52BF7D53…`) is left alone.
- **Full-screen boot logo:** untouched. Quiet Boot is always off, so it is never shown.

### 6. POST beep

A 103-byte routine (`build/beep.s`) was placed in unused space at the end of the `.text` section of **CapsuleRuntimeDxe** (RVA `0x1C70`, raw zero padding). The module's entry point was redirected to it (`AddressOfEntryPoint 0x1124 → 0x1C70`, `.text VirtualSize 0xC6F → 0xCD7`). The module is byte-identical to the B760I's (SHA-256 checked). The routine:

1. reads the CPU base frequency from `CPUID 0x16` (falls back to 2500 MHz);
2. programs 8254 counter 2 for a square wave with divisor `0x254` (≈ 2,002 Hz) and sets bits 0–1 of port `0x61` (speaker on);
3. waits ≈ 0.5 s using the TSC;
4. switches the speaker off and jumps to the original entry point.

It makes no calls and writes no memory except the stack. It needs a speaker on the SPEAKER header and the 8254 clock-gate default from §2.

### 7. Recompression

The main DXE volume and AMITSE / AMITSESetupData were recompressed with the 7-Zip **LZMA SDK** encoder (`lzma.exe e -d24`: no end marker, 16 MiB dictionary, props `5D 00 00 00 01`), the format EDK2's `LzmaDecompress` expects. Every stream was checked by decoding it with the SDK's reference decoder (`LZMA_FINISH_END`), and the output matched the intended data byte for byte. FFS header checksums were recalculated. Where a nested file got smaller, a standard FFS pad file fills the gap so the next file keeps its position. A full re-extraction of the image gives every module with no errors.

---

## Release history

All builds 2026-11. Only v6 is published and has been flashed and confirmed working on a real Snow Dream board; earlier versions were never flashed.

| Release | Changes |
|---|---|
| **v6** | Quiet Boot hidden **in place** (§3). v3–v5 hid it by inserting 4 bytes, which shifted the CheckBox and left its AMITSESetupData entry pointing at the wrong opcode. Fixed before any flash. |
| v5 | POST beep (§6); 8254 clock-gate default → 2. |
| v4 | All remaining CF9 `0x06` writes → `0x0E` (§1 rows 2–10) – fixes *Save Changes and Reset* in setup powering off. |
| v3 | Quiet Boot default off; text-screen logo replaced (full-screen logo left untouched). |
| v2 | zh-chs strings and CJK glyphs removed (§4); System Language hidden, default English; Quiet Boot hidden. |
| v1 | Factory defaults: CSM off, Re-Size BAR on, Package C-State Auto; FADT `RESET_VALUE` `0x06` → `0x0E`. |
