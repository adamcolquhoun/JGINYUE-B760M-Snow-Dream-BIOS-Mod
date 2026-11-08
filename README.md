# JGINYUE B760M Snow Dream D4 – modded BIOS (JYRPL014)

A modified version of JGINYUE's own **JYRPL014** BIOS for the **JGINYUE B760M Snow Dream D4** (micro-ATX, LGA1700, DDR4).
It fixes the vendor's restart bug, sets better factory defaults, removes the Chinese language pack, replaces the boot-screen logo and adds a POST beep.

> [!WARNING]
> **For the JGINYUE B760M Snow Dream D4 only.** Flashing it to any other board, including the B760I GAMING (same AMI template, different layout), will brick that board.
> The flash script checks the BIOS version and the flash descriptor and refuses to run on anything else.
> Flashing firmware always carries risk. This board has **no USB crisis recovery** from Windows; if a flash fails, recovery needs an SPI programmer (e.g. CH341A + SOIC-8 clip) and the backup the script makes. You flash at your own risk.

**Status: flashed and confirmed working on a real B760M Snow Dream D4.** This is a port of the [B760I GAMING mod](https://github.com/adamcolquhoun/JGINYUE-B760I-Gaming-BIOS-Mod); both boards share the same AMI code base and the patches sit at identical locations (except one PEI offset, see CHANGELOG).

## What's changed (summary)

| Area | Change |
|---|---|
| **Restart bug** | Restarting (from Windows *or* from BIOS setup) powered the PC off instead of rebooting. Every reset path now does a full reset (`0x0E` to port `0xCF9`) instead of the `0x06` hard reset this board family turns into a power-off. |
| **Factory defaults** | CSM **off** (pure UEFI), Re-Size BAR **on**, Package C-State Limit **Auto**, Quiet Boot **off**, 8254 clock gate set so the PC speaker works. |
| **Setup menu** | *Quiet Boot* and *System Language* options hidden (always off / always English). |
| **Language** | Chinese (zh-chs) strings removed from Setup and the AMI setup browser (2,727 strings) and the 615 Chinese font glyphs blanked; English only. |
| **Boot screen** | The full-screen vendor logo never shows (the file itself is left untouched). The classic text POST screen is used, with the American Megatrends logo (white on black) in place of the small "ami" logo. |
| **POST beep** | One ~2 kHz, ~0.5 s beep through the motherboard speaker header on every boot. |
| **Untouched** | Intel ME region, CPU microcode, Secure Boot keys, flash descriptor, everything else. |

Full byte-level details: **[CHANGELOG.md](CHANGELOG.md)**. How to flash: **[INSTALL.md](INSTALL.md)**.

## Files

| Path | What |
|---|---|
| `firmware/JYRPL014_mod6.bin` | The modded 16 MiB full-chip image (descriptor + ME + BIOS). |
| `firmware/SHA256SUMS.txt` | `6264ffac3f7da70a54a630d0aa1fb08f554bd87c6988bbc03968631a4a90da49` |
| `tools/flash_bios.cmd` | Safe flashing script (hash, board and descriptor checks, full backup, then flash). |
| `tools/update_me.cmd` | Optional Intel ME 16.1.42.2872 update (Intel files not included – see INSTALL.md). |
| `build/` | The build script, its helpers, the beep stub source (`beep.s`) and the logo assets. Reference only – see [build/README.md](build/README.md). |

## Not affiliated

Not affiliated with or endorsed by JGINYUE, AMI or Intel. The firmware remains the property of its respective owners; this repository only documents and distributes a modification of the vendor's publicly released BIOS for owners of this board. "American Megatrends" and the AMI logo are trademarks of AMI.
