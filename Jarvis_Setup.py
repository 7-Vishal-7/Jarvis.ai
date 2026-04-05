"""
JARVIS CLAP LAUNCHER
====================
Detects double-clap via microphone → launches:
  1. VS Code
  2. YT Music (Iron Man theme in Chrome)
  3. New Chrome window
  4. Claude.ai
  All arranged in a 4-way split layout (Windows)

Requirements:
    pip install pyaudio numpy

On Windows, also install:
    pip install pywin32  (for window arrangement)

Run: python jarvis_launcher.py
"""

import pyaudio
import numpy as np
import subprocess
import threading
import time
import sys
import os

# ─────────────────────────────────────────────
# CONFIG — tweak these to match your system
# ─────────────────────────────────────────────

# Clap detection
CLAP_THRESHOLD       = 2500   # amplitude threshold (raise if false triggers)
DOUBLE_CLAP_WINDOW   = 0.6    # seconds between two claps to count as "double clap"
COOLDOWN_SECONDS     = 3.0    # seconds to ignore after launch (prevents re-trigger)

# Apps — update paths to match your machine
VSCODE_PATH = r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

# URLs
YTMUSIC_IRONMAN_URL = (
    "https://music.youtube.com/watch?v=mR3YFHRfCcE"   # Iron Man - Black Sabbath
    # Replace with your preferred Iron Man theme track
)
CLAUDE_URL  = "https://claude.ai"

# Audio
SAMPLE_RATE  = 44100
CHUNK_SIZE   = 1024
CHANNELS     = 1

# ─────────────────────────────────────────────
# COLORS (terminal output)
# ─────────────────────────────────────────────

CYAN   = "\033[96m"
GOLD   = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def jarvis_print(msg, color=CYAN):
    print(f"{color}{BOLD}[J.A.R.V.I.S]{RESET} {color}{msg}{RESET}")

# ─────────────────────────────────────────────
# WINDOW ARRANGER (Windows only via PowerShell)
# ─────────────────────────────────────────────

ARRANGE_SCRIPT = r"""
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32 {
    [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
    [DllImport("user32.dll")] public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern int GetSystemMetrics(int nIndex);
}
"@

Start-Sleep -Seconds 4   # wait for apps to open

$sw = [Win32]::GetSystemMetrics(0)   # screen width
$sh = [Win32]::GetSystemMetrics(1)   # screen height
$hw = [int]($sw / 2)
$hh = [int]($sh / 2)

# Find windows by partial title (adjust if needed)
$procs = @{
    "Code"   = Get-Process "Code"   -ErrorAction SilentlyContinue | Select-Object -First 1
    "Chrome" = Get-Process "chrome" -ErrorAction SilentlyContinue | Select-Object -First 4
}

# VS Code → top-left
$vscode = (Get-Process "Code" -ErrorAction SilentlyContinue | Select-Object -First 1).MainWindowHandle
if ($vscode) { [Win32]::MoveWindow($vscode, 0, 0, $hw, $hh, $true) }

# Chrome windows → grab up to 3 (YT Music, Claude, new tab)
$chromes = (Get-Process "chrome" -ErrorAction SilentlyContinue | Where-Object {$_.MainWindowHandle -ne 0})

$positions = @(
    @{x=$hw; y=0;   w=$hw; h=$hh},   # top-right
    @{x=0;   y=$hh; w=$hw; h=$hh},   # bottom-left
    @{x=$hw; y=$hh; w=$hw; h=$hh}    # bottom-right
)

$i = 0
foreach ($c in $chromes) {
    if ($i -ge 3) { break }
    $hwnd = $c.MainWindowHandle
    if ($hwnd -ne 0) {
        $p = $positions[$i]
        [Win32]::MoveWindow($hwnd, $p.x, $p.y, $p.w, $p.h, $true)
        $i++
    }
}

Write-Host "JARVIS: Window arrangement complete."
"""

def arrange_windows():
    """Run PowerShell script to tile windows in 4-way split."""
    jarvis_print("Arranging windows in 4-way split...", GOLD)
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", ARRANGE_SCRIPT],
            creationflags=subprocess.CREATE_NO_WINDOW
        )
    except Exception as e:
        jarvis_print(f"Window arranger skipped (non-Windows or error): {e}", RED)

# ─────────────────────────────────────────────
# LAUNCHER
# ─────────────────────────────────────────────

def launch_all():
    jarvis_print("ACTIVATING PROTOCOL STARK...", GOLD)

    chrome = CHROME_PATH

    # 1. VS Code
    try:
        subprocess.Popen([os.path.expandvars(VSCODE_PATH)])
        jarvis_print("VS Code → launched ✓")
    except FileNotFoundError:
        # Try PATH fallback
        try:
            subprocess.Popen(["code"])
            jarvis_print("VS Code (PATH) → launched ✓")
        except Exception as e:
            jarvis_print(f"VS Code launch failed: {e}", RED)

    time.sleep(0.5)

    # 2. YT Music - Iron Man theme (new Chrome window)
    try:
        subprocess.Popen([chrome, "--new-window", YTMUSIC_IRONMAN_URL])
        jarvis_print("YT Music (Iron Man theme) → launched ✓")
    except Exception as e:
        jarvis_print(f"YT Music launch failed: {e}", RED)

    time.sleep(0.5)

    # 3. Claude.ai (new Chrome window)
    try:
        subprocess.Popen([chrome, "--new-window", CLAUDE_URL])
        jarvis_print("Claude.ai → launched ✓")
    except Exception as e:
        jarvis_print(f"Claude launch failed: {e}", RED)

    time.sleep(0.5)

    # 4. New blank Chrome window
    try:
        subprocess.Popen([chrome, "--new-window", "about:newtab"])
        jarvis_print("Chrome (new window) → launched ✓")
    except Exception as e:
        jarvis_print(f"Chrome launch failed: {e}", RED)

    # 5. Arrange all windows
    threading.Thread(target=arrange_windows, daemon=True).start()

    jarvis_print("All systems online. Good evening, sir.", GOLD)

# ─────────────────────────────────────────────
# CLAP DETECTOR
# ─────────────────────────────────────────────

class ClapDetector:
    def __init__(self):
        self.last_clap_time = 0
        self.last_launch_time = 0
        self.running = True

    def detect(self, audio_chunk):
        amplitude = np.abs(np.frombuffer(audio_chunk, dtype=np.int16)).mean()
        now = time.time()

        # Ignore during cooldown
        if now - self.last_launch_time < COOLDOWN_SECONDS:
            return

        if amplitude > CLAP_THRESHOLD:
            gap = now - self.last_clap_time
            if 0.1 < gap < DOUBLE_CLAP_WINDOW:
                jarvis_print("Double clap detected! 👏👏", GOLD)
                self.last_launch_time = now
                threading.Thread(target=launch_all, daemon=True).start()
                self.last_clap_time = 0   # reset
            else:
                jarvis_print(f"Clap 1 detected... waiting for clap 2 (amplitude: {amplitude:.0f})")
                self.last_clap_time = now

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    print(f"""
{CYAN}{BOLD}
   ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
   ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
   ██║███████║██████╔╝██║   ██║██║███████╗
██ ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
{RESET}
{GOLD}  Just A Rather Very Intelligent System
  Clap TWICE to activate Protocol Stark{RESET}
{CYAN}  ─────────────────────────────────────────{RESET}
    """)

    pa = pyaudio.PyAudio()
    detector = ClapDetector()

    stream = pa.open(
        format=pyaudio.paInt16,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK_SIZE
    )

    jarvis_print("Microphone active. Listening for double clap...")

    try:
        while detector.running:
            data = stream.read(CHUNK_SIZE, exception_on_overflow=False)
            detector.detect(data)
    except KeyboardInterrupt:
        jarvis_print("Shutting down. Goodbye, sir.", GOLD)
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()

if __name__ == "__main__":
    main()