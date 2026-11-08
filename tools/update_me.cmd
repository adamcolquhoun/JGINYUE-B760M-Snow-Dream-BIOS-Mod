@echo off
:: Update Intel CSME (consumer 16.1) to 16.1.42.2872 with Intel's FWUpdLcl64.
:: Put FWUpdLcl64.exe and 16.1.42.2872.bin (see INSTALL.md) in this folder.
:: Run as Administrator, only AFTER flash_bios.cmd and a full power cycle - never in the same Windows session.
setlocal
cd /d "%~dp0"
net session >nul 2>&1 || (echo Run this as Administrator. & pause & exit /b 1)
if not exist FWUpdLcl64.exe (echo FWUpdLcl64.exe not found - see INSTALL.md. & pause & exit /b 1)
if not exist 16.1.42.2872.bin (echo 16.1.42.2872.bin not found - see INSTALL.md. & pause & exit /b 1)
for /f "tokens=* delims=" %%v in ('powershell -NoProfile -Command "(Get-CimInstance Win32_BIOS).SMBIOSBIOSVersion"') do set BIOSVER=%%v
if /i not "%BIOSVER:~0,5%"=="JYRPL" (echo This PC is not running a Snow Dream BIOS ^(%BIOSVER%^) - stopping. & pause & exit /b 1)
FWUpdLcl64.exe -ALLOWSV -F 16.1.42.2872.bin
echo.
echo If it reported success, shut down fully and power on again.
pause
