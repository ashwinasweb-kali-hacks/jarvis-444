@echo off
setlocal
echo ======================================================================
echo           JARVIS-OS -- Tony Stark Workshop Graphical Desktop
echo ======================================================================
echo.

set "QEMU=C:\Program Files\qemu\qemu-system-x86_64.exe"
set "ISO=%~dp0JARVIS-OS.iso"

if not exist "%QEMU%" (
    echo [ERROR] QEMU executable not found at: "%QEMU%"
    pause
    exit /b 1
)

if not exist "%ISO%" (
    echo [ERROR] Bootable ISO not found at: "%ISO%"
    pause
    exit /b 1
)

echo [BOOT] Initializing JARVIS-OS in QEMU...
echo - Multi-threaded TCG acceleration enabled (-smp 4).
echo - Video Mode: 1280x720 DRM/KMS VirtIO Framebuffer.
echo - Full Mouse and Physical Keyboard input enabled.
echo - Audio: Intel HDA Duplex sound subsystem.
echo.
echo TIP: Click inside the QEMU window to grab the mouse.
echo      Press Ctrl+Alt+G to release the mouse cursor.
echo.

"%QEMU%" ^
    -name "JARVIS-OS Tony Stark Workshop" ^
    -m 2048 ^
    -smp 4 ^
    -accel tcg,thread=multi ^
    -cdrom "%ISO%" ^
    -boot d ^
    -vga none ^
    -device virtio-vga,xres=1280,yres=720 ^
    -display sdl ^
    -usb ^
    -device usb-tablet ^
    -audiodev dsound,id=snd0 ^
    -device intel-hda ^
    -device hda-duplex,audiodev=snd0

echo.
echo QEMU session terminated.
pause
