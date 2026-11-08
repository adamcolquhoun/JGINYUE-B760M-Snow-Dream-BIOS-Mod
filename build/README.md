# Build scripts (reference)

Kept so every change can be audited. Not a one-click build.

| File | Purpose |
|---|---|
| `build_dream.py` | Builds v6 from `step1.bin` (= vendor JYRPL014 + the 3 hand-made defaults: Re-Size BAR, CSM, Package C-State). Applies everything else in CHANGELOG.md. Usage: `python build_dream.py step1.bin assets/text_screen_logo.bmp out.bin workdir` |
| `build_dream_v7.py` | v6 → v7: disables the AMI USB-device beeps (one byte in UsbRtDxe and UsbRtSmm). Usage: `python build_dream_v7.py JYRPL014_mod6.bin out.bin workdir` |
| `build_beep_v2.py` (+ `beep_v2.py`) | v7 → v8. Beep v2: rewrites the stub in place (1 kHz, counter 2 parked) and disables the AMI USB-device beeps. `python build_beep_v2.py <b760i|snowdream> in.bin out.bin workdir`. Note: `beep.s`/`beep.bin` are now v2; the older scripts were built with the v1 stub (see git history). |
| `quietboot.py` | Hides Quiet Boot in place and patches its AMITSESetupData record (shared with the B760I mod). |
| `hiistr.py` | Exact HII string-package (SIBT block) walker used to empty the zh-chs packages. |
| `beepinject.py`, `beep.s`, `beep.bin` | POST beep stub and its injection into CapsuleRuntimeDxe; 8254 clock-gate default. Build the stub with `as beep.s -o beep.o && objcopy -O binary beep.o beep.bin`. |
| `makepostlogo.ps1` | Converts the source logo into the 378×100 24-bit BMP (`assets/text_screen_logo.bmp`) with a black background. |

Requirements: Python 3.10+, the 7-Zip **LZMA SDK** `lzma.exe` encoder (`set LZMA_EXE=…\lzma_sdk\bin\x64\lzma.exe`) and an extraction of the vendor image (UEFITool/UEFIExtract-style folder tree) in `EXTRACTED_BIOS`. `build_dream.py` imports `beepinject` from a `beep/` subfolder; put the three beep files there or adjust `sys.path`.
