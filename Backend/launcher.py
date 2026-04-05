"""
launcher.py — 4-app workspace launch sequence
"""

import subprocess, time, os

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.05
    GUI_OK = True
except ImportError:
    GUI_OK = False

from utils import (
    ps, get_all_brave_handles, wait_for_new_brave_handle,
    wait_for_process, focus_by_handle, focus_process
)

# ══════════════════════════════════
# CONFIG
# ══════════════════════════════════

BRAVE       = r"C:\Users\VISHAL B\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"
VSCODE      = os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe")
YTMUSIC_URL = "https://www.youtube.com/watch?v=EfmVRQjoNcY&autoplay=1"

# ══════════════════════════════════
# SNAP
# ══════════════════════════════════

def snap(position: str):
    if not GUI_OK:
        print("[JARVIS] pyautogui missing — cannot snap")
        return
    time.sleep(0.3)
    moves = {
        "top-left":     [("win", "left"), ("win", "up")],
        "top-right":    [("win", "right"), ("win", "up")],
        "bottom-left":  [("win", "left"), ("win", "down")],
        "bottom-right": [("win", "right"), ("win", "down")],
    }
    for keys in moves.get(position, []):
        pyautogui.hotkey(*keys)
        time.sleep(0.4)

# ══════════════════════════════════
# LAUNCH SEQUENCE
# ══════════════════════════════════

_launching = False

def launch_workspace():
    global _launching
    if _launching:
        return
    _launching = True

    try:
        print("\n[JARVIS] ══════ PROTOCOL STARK ══════")

        # ── [1/4] VS Code → TOP LEFT ──────────────────────────
        print("[JARVIS] [1/4] VS Code...")
        try:
            subprocess.Popen([os.path.expandvars(VSCODE)])
        except FileNotFoundError:
            subprocess.Popen(["code"])

        if wait_for_process("Code", 8):
            time.sleep(0.4)
            focus_process("Code")
            time.sleep(0.3)
            snap("top-left")
            print("[JARVIS] VS Code → top-left ✓")
        else:
            print("[JARVIS] VS Code timeout")
        time.sleep(0.3)

        # ── [2/4] YouTube in Brave → TOP RIGHT ────────────────
        print("[JARVIS] [2/4] YouTube (Brave)...")
        handles_before = get_all_brave_handles()
        try:
            subprocess.Popen([BRAVE, "--new-window", "--no-restore", YTMUSIC_URL])
        except FileNotFoundError:
            print("[JARVIS] Brave not found — check BRAVE path in config")

        new_handle = wait_for_new_brave_handle(handles_before, 12)
        if new_handle:
            time.sleep(0.5)
            focus_by_handle(new_handle)
            time.sleep(0.3)
            snap("top-right")
            print("[JARVIS] YouTube → top-right ✓")
        else:
            print("[JARVIS] Brave timeout")
        time.sleep(0.3)

        # ── [3/4] Claude App → BOTTOM LEFT ───────────────────
        print("[JARVIS] [3/4] Claude app...")
        ps('Start-Process "claude"')

        if wait_for_process("claude", 8):
            time.sleep(0.4)
            focus_process("claude")
            time.sleep(0.3)
            snap("bottom-left")
            print("[JARVIS] Claude → bottom-left ✓")
        else:
            print("[JARVIS] Claude timeout")
        time.sleep(0.3)

        # ── [4/4] ChatGPT App → BOTTOM RIGHT ─────────────────
        print("[JARVIS] [4/4] ChatGPT app...")
        ps('Start-Process "ChatGPT"')

        if wait_for_process("ChatGPT", 8):
            time.sleep(0.4)
            focus_process("ChatGPT")
            time.sleep(0.3)
            snap("bottom-right")
            print("[JARVIS] ChatGPT → bottom-right ✓")
        else:
            print("[JARVIS] ChatGPT timeout")

        print("\n[JARVIS] ══════ ALL SYSTEMS ONLINE. GOOD EVENING, SIR. ══════\n")

    finally:
        time.sleep(5.0)
        _launching = False