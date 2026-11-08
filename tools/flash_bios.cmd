@echo off
:: Flash JYRPL014_mod8.bin to a JGINYUE B760M Snow Dream D4 (vendor BIOS JYRPL014 + the changes in CHANGELOG.md).
:: ONLY for the B760M Snow Dream. The script refuses to run on any other board.
:: Needs FPTW64.exe (from JGINYUE's own BIOS package) in this folder. Run as Administrator.
:: Do not interrupt or power off once writing starts.
setlocal
cd /d "%~dp0"
net session >nul 2>&1 || (echo Run this as Administrator. & pause & exit /b 1)
if not exist FPTW64.exe (echo FPTW64.exe not found - copy it here from the vendor BIOS package. See INSTALL.md. & pause & exit /b 1)

set IMG=..\firmware\JYRPL014_mod8.bin
set EXPECT=920974c22dd03eca90fef70676626128dcb1e93e62c05385c8982b3113377906

echo === Check 1: image integrity ===
if not exist %IMG% (echo %IMG% not found - NOT flashing. & pause & exit /b 1)
for /f "tokens=* delims=" %%h in ('certutil -hashfile %IMG% SHA256 ^| findstr /v ":"') do (set GOT=%%h& goto :gotHash)
:gotHash
set GOT=%GOT: =%
if /i not "%GOT%"=="%EXPECT%" (echo Image hash mismatch: %GOT% - NOT flashing. & pause & exit /b 1)
echo Image hash OK.

echo.
echo === Check 2: this must be a B760M Snow Dream (BIOS version JYRPL...) ===
for /f "tokens=* delims=" %%v in ('powershell -NoProfile -Command "(Get-CimInstance Win32_BIOS).SMBIOSBIOSVersion"') do set BIOSVER=%%v
for /f "tokens=* delims=" %%p in ('powershell -NoProfile -Command "(Get-CimInstance Win32_BaseBoard).Product"') do set BOARD=%%p
echo Current BIOS: %BIOSVER%   Board: %BOARD%
if /i not "%BIOSVER:~0,5%"=="JYRPL" (echo This PC is not running a Snow Dream BIOS - NOT flashing. & pause & exit /b 1)

echo.
echo === Step 1: full backup of the current chip to backup_before_mod_full.bin ===
FPTW64.exe -d backup_before_mod_full.bin || (echo Backup failed - NOT flashing. & pause & exit /b 1)

echo.
echo === Check 3: flash descriptor of this board must match the image ===
powershell -NoProfile -Command "$a=[IO.File]::ReadAllBytes('backup_before_mod_full.bin')[0..4095];$b=[IO.File]::ReadAllBytes('%IMG%')[0..4095];if(@(Compare-Object $a $b -SyncWindow 0).Count){exit 1}" || (echo Flash descriptor differs from the image - wrong board or layout - NOT flashing. & pause & exit /b 1)
echo Descriptor matches.

echo.
echo Everything checks out. Press any key to write the BIOS (do not power off during writing),
echo or close this window to cancel.
pause >nul

echo === Step 2: writing %IMG% (full chip, verified by FPT) ===
FPTW64.exe -f %IMG% -rewrite || (echo FLASH REPORTED AN ERROR - do not reboot; keep this window open. & pause & exit /b 1)

echo.
echo Done. Shut down fully, switch the PSU off for ~10 seconds, then power on.
echo The first boot may take longer while memory is retrained. Then see INSTALL.md step 5 (ME update).
pause
