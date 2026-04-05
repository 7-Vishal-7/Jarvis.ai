"""
J.A.R.V.I.S — app.py (Last Working Version)

Layout:
  [VS Code    ] [YouTube/Brave]
  [Claude App ] [ChatGPT App  ]

Trigger: double-clap OR http://127.0.0.1:5000/launch
"""

from flask import Flask, jsonify
import subprocess, threading, time, os

try:
    import pyaudio, numpy as np
    AUDIO_OK = True
except ImportError:
    AUDIO_OK = False

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.05
    GUI_OK = True
except ImportError:
    GUI_OK = False

app = Flask(__name__)

# ══════════════════════════════════
# CONFIG
# ══════════════════════════════════
BRAVE       = r"C:\Users\VISHAL B\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"
VSCODE      = os.path.expandvars(r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe")
YTMUSIC_URL = "https://www.youtube.com/watch?v=EfmVRQjoNcY&autoplay=1"

CLAP_THRESHOLD     = 2500
DOUBLE_CLAP_WINDOW = 0.6
COOLDOWN_SECONDS   = 5.0

# ══════════════════════════════════
# POWERSHELL RUNNER
# ══════════════════════════════════

def ps(script: str, timeout: int = 10) -> str:
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=timeout
        )
        return r.stdout.strip()
    except Exception:
        return ""

# ══════════════════════════════════
# WINDOW HELPERS
# ══════════════════════════════════

def get_all_brave_handles() -> list:
    out = ps(
        "(Get-Process 'brave' -EA SilentlyContinue | "
        "Where-Object {$_.MainWindowHandle -ne 0} | "
        "Select-Object -ExpandProperty MainWindowHandle) -join ','"
    )
    if not out:
        return []
    return [x.strip() for x in out.split(",") if x.strip().isdigit() and x.strip() != "0"]

def wait_for_new_brave_handle(known_handles: list, timeout: int = 12) -> str:
    known_set = set(known_handles)
    end = time.time() + timeout
    while time.time() < end:
        current = get_all_brave_handles()
        new = [h for h in current if h not in known_set]
        if new:
            return new[0]
        time.sleep(0.3)
    return ""

def wait_for_process(proc: str, timeout: int = 8) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        out = ps(
            f"(Get-Process '{proc}' -EA SilentlyContinue | "
            f"Where-Object {{$_.MainWindowHandle -ne 0}} | Select -First 1).Id"
        )
        if out.isdigit():
            return True
        time.sleep(0.3)
    return False

def focus_by_handle(handle: str):
    if not handle:
        return
    ps(f"""
Add-Type @"
using System; using System.Runtime.InteropServices;
public class FH {{
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
    [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
}}
"@
$h = [IntPtr][long]{handle}
[FH]::ShowWindow($h, 9)
Start-Sleep -Milliseconds 250
[FH]::SetForegroundWindow($h)
[FH]::BringWindowToTop($h)
""")

def focus_process(proc: str):
    ps(f"""
Add-Type @"
using System; using System.Runtime.InteropServices;
public class FP {{
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
}}
"@
$p = Get-Process "{proc}" -EA SilentlyContinue |
     Where-Object {{$_.MainWindowHandle -ne 0}} | Select -First 1
if($p){{[FP]::ShowWindow($p.MainWindowHandle,9);Start-Sleep -ms 200;[FP]::SetForegroundWindow($p.MainWindowHandle)}}
""")

# ══════════════════════════════════
# WIN+ARROW SNAP
# ══════════════════════════════════

def snap(position: str):
    if not GUI_OK:
        return
    time.sleep(0.3)
    moves = {
        "top-left":     [("win","left"), ("win","up")],
        "top-right":    [("win","right"),("win","up")],
        "bottom-left":  [("win","left"), ("win","down")],
        "bottom-right": [("win","right"),("win","down")],
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
            print(f"[JARVIS] Brave not found — check BRAVE path in config")

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
        time.sleep(COOLDOWN_SECONDS)
        _launching = False

# ══════════════════════════════════
# FLASK
# ══════════════════════════════════

@app.route("/")
def index():
    return jsonify({"jarvis": "online", "version": "Mark XXVI"})

@app.route("/launch")
def route_launch():
    threading.Thread(target=launch_workspace, daemon=True).start()
    return jsonify({"status": "launching"})

@app.route("/health")
def health():
    return jsonify({"audio": AUDIO_OK, "gui": GUI_OK})

# ══════════════════════════════════
# CLAP DETECTOR
# ══════════════════════════════════

def clap_listener():
    if not AUDIO_OK:
        print("[JARVIS] PyAudio not found — clap detection disabled")
        return
    pa     = pyaudio.PyAudio()
    stream = pa.open(format=pyaudio.paInt16, channels=1,
                     rate=44100, input=True, frames_per_buffer=1024)
    last_clap = last_launch = 0
    print("[JARVIS] Mic active — double-clap to launch")
    try:
        while True:
            data = stream.read(1024, exception_on_overflow=False)
            amp  = np.abs(np.frombuffer(data, dtype=np.int16)).mean()
            now  = time.time()
            if now - last_launch < COOLDOWN_SECONDS:
                continue
            if amp > CLAP_THRESHOLD:
                gap = now - last_clap
                if 0.08 < gap < DOUBLE_CLAP_WINDOW:
                    print("\n[JARVIS] 👏👏 Double clap!")
                    last_launch = now; last_clap = 0
                    threading.Thread(target=launch_workspace, daemon=True).start()
                else:
                    print(f"[JARVIS] Clap 1 (amp={amp:.0f})...")
                    last_clap = now
    finally:
        stream.stop_stream(); stream.close(); pa.terminate()

# ══════════════════════════════════
# MAIN
# ══════════════════════════════════

if __name__ == "__main__":
    print("""
   ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗  Mark XXVI
   ██║██╔══██╗██╔══██╗╚██╗ ██╔╝██║██╔════╝
   ██║███████║██████╔╝ ╚████╔╝ ██║███████╗  /launch  or
   ██║██╔══██║██╔══██╗  ╚██╔╝  ██║╚════██║  clap twice
   ██║██║  ██║██║  ██║   ██║   ██║███████║
   ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝╚══════╝
    """)

    if not GUI_OK:
        print("[JARVIS] ⚠  pip install pyautogui  ← needed for snapping!\n")
    if AUDIO_OK:
        threading.Thread(target=clap_listener, daemon=True).start()

    app.run(host="127.0.0.1", port=5000, debug=False)