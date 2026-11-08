# Installing the modded BIOS – JGINYUE B760M Snow Dream D4


> [!CAUTION]
> **B760M Snow Dream D4 only.** Do not flash this on any other board (the B760I GAMING looks similar inside but has a different layout).
> There is **no USB recovery** on this board. A failed or interrupted flash can only be fixed with an SPI programmer and a backup.
> Read this whole page before starting.

## What you need

1. **A JGINYUE B760M Snow Dream D4** running Windows 10/11 (64-bit) with a JYRPL… BIOS (any version; the script checks).
2. **This repository** – *Code → Download ZIP* and extract it, or `git clone`. Git LFS is not needed.
3. **Intel Flash Programming Tool `FPTW64.exe`.** It is not included here (Intel's licence does not allow redistributing it). Take it from **JGINYUE's own BIOS package for this board** – the vendor's JYRPL014 archive has a Windows flashing folder containing `FPTW64.exe` (the vendor flashes with `fptw64 -f <image> -rewrite`). The version used for testing was 16.1.25.1871 (SHA-256 `15d329ce4e5cbce10ad690e0727c54ffbbbb2a0489f80919c1b3b37858564aaa`).
4. **A stable power supply.** Don't flash during a storm, on a flaky UPS, or with an overclock that isn't fully stable. Close other programs.
5. *(Optional, step 5)* Intel ME firmware update files – see below.

## Before you start

- **Note your settings.** The flash resets all BIOS settings to the (new) factory defaults: XMP, fan curves, boot order, etc. Take photos of anything you changed.
- **CSM is off by default in this mod.** If Windows was installed in **Legacy/CSM (MBR)** mode it won't boot afterwards. Check first: run `msinfo32` → *BIOS Mode* must say **UEFI**. If it says *Legacy*, either convert the disk with `mbr2gpt` first or turn *CSM Support* back on in setup after flashing.
- **BitLocker:** if the system drive is BitLocker-encrypted, **suspend BitLocker** first (*Control Panel → BitLocker → Suspend protection*) or have your recovery key ready – firmware changes alter the TPM measurements.
- **Secure Boot** keys are reset to the vendor defaults. Windows boots normally; if you enrolled your own keys you'll need to re-enrol them.
- **Speaker:** the POST beep needs a speaker or piezo buzzer on the front-panel **SPEAKER** pins. Without one the mod works the same, just silently.

## Step 1 – Get the files in place

1. Extract the repository somewhere simple, e.g. `C:\SnowDream-mod\`.
2. Copy **`FPTW64.exe`** into the **`tools\`** folder (next to `flash_bios.cmd`).
3. Optional: check the image hash yourself in PowerShell:

   ```powershell
   Get-FileHash .\firmware\JYRPL014_mod8.bin -Algorithm SHA256
   ```

   It must be `920974C22DD03ECA90FEF70676626128DCB1E93E62C05385C8982B3113377906`. The script checks this too.

## Step 2 – Flash

1. Right-click **`tools\flash_bios.cmd`** → **Run as administrator**.
2. The script:
   1. checks the image's SHA-256;
   2. checks the PC is running a **JYRPL** (Snow Dream) BIOS – otherwise it stops;
   3. dumps the **whole current chip** to `tools\backup_before_mod_full.bin`;
   4. checks the board's **flash descriptor** matches the image – otherwise it stops;
   5. **waits for a key press**. This is your last chance to cancel (just close the window);
   6. writes the full 16 MiB chip with `FPTW64 -f … -rewrite` and verifies it.
3. Writing takes a few minutes. **Do not close the window, sleep, restart or power off** until it says *Done* and *FPT Operation Successful*.
4. If the script stops with an error **before** the key press, nothing was written – it's safe to reboot.
   If it reports an error **during writing**, do **not** reboot. Keep the window open and get help (see *Recovery* below).

**Copy `tools\backup_before_mod_full.bin` to a USB stick or another PC now.** It's your only way back if something goes wrong later.

## Step 3 – Power cycle

1. Shut down Windows (*Start → Power → Shut down*, not Restart).
2. Switch the PSU off at the rear (or unplug) for **about 10 seconds**, then switch back on and power up.
3. The first boot can take noticeably longer (memory training) and may restart once by itself. You should hear **one beep**, then the text POST screen with the American Megatrends logo.

## Step 4 – Set up

1. Press **Del** during POST to enter setup.
2. Re-apply your settings (XMP, fans, boot order …). The new defaults are already set: CSM off, ReBAR on, C-states Auto, Quiet Boot off.
3. **Beep:** the 8254 clock-gate default is already *Enabled In Runtime and S3 Resume*. If you ever *Load Defaults* from an older profile and lose the beep, set *Chipset → PCH-IO Configuration → Enable 8254 Clock Gate* to **Enabled In Runtime and S3 Resume**. Setting it to *Enabled* silences the beep.
4. Save and exit (F10), boot to Windows.
5. Test a restart from Windows and from setup (*Save Changes and Reset*) – the PC should reboot, not switch off.

## Step 5 – (Optional) Update Intel ME to 16.1.42.2872

The full-chip flash writes the vendor's original ME firmware (**16.1.25.1917**) back to the chip, because the ME region is part of the image and is unchanged. If you want the newer Intel ME (security fixes), update it **after** the power cycle in step 3:

1. Get Intel's **CSME 16.1 Consumer firmware 16.1.42.2872** and the matching **FWUpdLcl64.exe** (*Intel ME System Tools v16.1*; tested with FWUpdLcl 16.1.42.2886). They are Intel files and are not included here. Community mirrors that keep the official Intel packages are the Win-Raid forum thread *"Intel CSME (Converged Security and Management Engine): Drivers, Firmware and Tools – ME 16"* and the ASUS ROG forum firmware index thread *"[FIRMWARE] Intel ME – H610/B660/H670/Z690/B760/H770/Z790"*.
2. Copy **`FWUpdLcl64.exe`** and the firmware file renamed to **`16.1.42.2872.bin`** into `tools\`.
3. Right-click **`tools\update_me.cmd`** → **Run as administrator**. It runs `FWUpdLcl64 -ALLOWSV -F 16.1.42.2872.bin`.
4. When it reports success, **shut down fully and power on again**.

Do not run the ME update in the same Windows session as the BIOS flash. Skipping this step is safe; the board just keeps running the vendor's ME.

## Recovery

- **Flash completed but the PC won't POST:** clear CMOS (remove the coin cell or short the CLR_CMOS jumper for ~30 s with the PSU off) and try again. Remove extra hardware and leave one RAM stick in.
- **Still nothing:** reflash `tools\backup_before_mod_full.bin` (your original chip contents) with an SPI programmer (CH341A or similar + SOIC-8 clip, 3.3 V W25Q128-class chip, 16 MiB). You can also flash the vendor's original `BIOS.rom` this way, but your own backup also keeps your board's ME state.
- **Back to stock from Windows:** if the PC boots, flash the vendor package the vendor's way (`fptw64 -f BIOS.ROM -rewrite` from an admin prompt), or flash your backup with `FPTW64.exe -f backup_before_mod_full.bin -rewrite`.

## Verifying what's on the chip

From an admin prompt in `tools\`:

```bat
FPTW64.exe -verify ..\firmware\JYRPL014_mod8.bin
```

Only the NVRAM area (your settings, which change as you use the PC) and possibly the ME data area should differ.
