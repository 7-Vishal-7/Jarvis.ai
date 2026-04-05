"""
J.A.R.V.I.S — app.py (Chrome-Kill + Fresh Launch Fix)

Root cause of timeouts:
  Chrome was already running → --new-window opens a TAB not a new process
  → No new PID → wait_for_new_chrome() times out every time
  → Windows never get snapped

Fix:
  1. Kill ALL Chrome processes first (clean slate)
  2. Launch each Chrome window with a delay between them
  3. Detect windows by title (not PID) — more reliable
  4. Snap using Win+Arrow via pyautogui
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
CHROME      = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BRAVE       = r"C:\Users\VISHAL B\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe"
VSCODE      = os.path.expandvars(
    r"C:\Users\%USERNAME%\AppData\Local\Programs\Microsoft VS Code\Code.exe")

# Brave — YT video that starts playing immediately
YTMUSIC_URL = "https://www.youtube.com/watch?v=EfmVRQjoNcY&autoplay=1"
# Claude and ChatGPT launched by app name via PowerShell (no hardcoded path needed)

CLAP_THRESHOLD     = 2500
DOUBLE_CLAP_WINDOW = 0.6
COOLDOWN_SECONDS   = 5.0

# ══════════════════════════════════
# POWERSHELL RUNNER
# ══════════════════════════════════

def ps(script: str, timeout: int = 15) -> str:
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=timeout
        )
        return r.stdout.strip()
    except Exception as e:
        return ""

# ══════════════════════════════════
# CHROME KILL
# ══════════════════════════════════

# ══════════════════════════════════
# WINDOW DETECTION BY HANDLE COUNT
# ══════════════════════════════════

def get_all_brave_handles() -> list:
    """Get all brave MainWindowHandles that are non-zero."""
    out = ps(
        "(Get-Process 'brave' -EA SilentlyContinue | "
        "Where-Object {$_.MainWindowHandle -ne 0} | "
        "Select-Object -ExpandProperty MainWindowHandle) -join ','"
    )
    if not out:
        return []
    return [x.strip() for x in out.split(",") if x.strip().isdigit() and x.strip() != "0"]

def wait_for_new_brave_handle(known_handles: list, timeout: int = 20) -> str:
    """Wait until a Brave window handle appears that wasn't in known_handles."""
    known_set = set(known_handles)
    end = time.time() + timeout
    while time.time() < end:
        current = get_all_brave_handles()
        new = [h for h in current if h not in known_set]
        if new:
            return new[0]
        time.sleep(0.4)
    return ""

def wait_for_process(proc: str, timeout: int = 15) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        out = ps(
            f"(Get-Process | Where-Object {{$_.MainWindowHandle -ne 0 -and "
            f"$_.ProcessName -like '*{proc}*'}} | Select -First 1).Id"
        )
        if out.strip().isdigit():
            return True
        time.sleep(0.3)
    return False

def focus_process(proc: str):
    ps(f"""
Add-Type @"
using System; using System.Runtime.InteropServices;
public class FP {{
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
}}
"@
$p = Get-Process | Where-Object {{$_.MainWindowHandle -ne 0 -and $_.ProcessName -like '*{proc}*'}} | Select -First 1
if($p){{[FP]::ShowWindow($p.MainWindowHandle,9);Start-Sleep -ms 200;[FP]::SetForegroundWindow($p.MainWindowHandle)}}
""")

# ══════════════════════════════════
# FOCUS BY HANDLE
# ══════════════════════════════════

FOCUS_BY_HANDLE_PS = """
param([string]$handle)
Add-Type @"
using System; using System.Runtime.InteropServices;
public class FH {{
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
    [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
}}
"@
$h = [IntPtr][long]$handle
[FH]::ShowWindow($h, 9)
Start-Sleep -Milliseconds 300
[FH]::SetForegroundWindow($h)
[FH]::BringWindowToTop($h)
"""

def focus_by_handle(handle: str):
    if not handle:
        return
    ps(f"""
Add-Type @"
using System; using System.Runtime.InteropServices;
public class FH2 {{
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
    [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
}}
"@
$h = [IntPtr][long]{handle}
[FH2]::ShowWindow($h, 9)
Start-Sleep -Milliseconds 350
[FH2]::SetForegroundWindow($h)
[FH2]::BringWindowToTop($h)
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
$p = Get-Process | Where-Object {{$_.MainWindowHandle -ne 0 -and $_.ProcessName -like '*{proc}*'}} | Select -First 1
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
        time.sleep(0.35)

# ══════════════════════════════════
# MAIN LAUNCH SEQUENCE
# ══════════════════════════════════

_launching = False

def launch_workspace():
    global _launching
    if _launching:
        return
    _launching = True

    try:
        print("\n[JARVIS] ══════ PROTOCOL STARK ══════")

        # Snapshot Brave handles BEFORE launching anything
        handles_before = get_all_brave_handles()
        _brave_handle  = [None]   # shared across threads

        # ── Per-app launch / wait / focus functions ──────────────

        def launch_vscode():
            try:    subprocess.Popen([os.path.expandvars(VSCODE)])
            except: subprocess.Popen(["code"])

        def launch_brave():
            subprocess.Popen([BRAVE, "--new-window", "--no-restore", YTMUSIC_URL])

        def wait_brave(t):
            h = wait_for_new_brave_handle(handles_before, t)
            _brave_handle[0] = h
            return bool(h)

        def focus_brave():
            if _brave_handle[0]: focus_by_handle(_brave_handle[0])

        # ── Snap is Win+Arrow — must NOT run in parallel (OS focus clash)
        # Solution: each thread waits for its own staggered snap slot.
        # All 4 apps launch simultaneously at t=0.
        # Snaps fire at t=0.6, 1.2, 1.8, 2.4 (staggered 0.6s apart).

        STAGGER = 0.5   # seconds between each snap

        def run(name, launch_fn, wait_fn, focus_fn, position, snap_slot):
            launch_fn()
            if wait_fn(6):                 # 6s per-app timeout
                time.sleep(snap_slot)
                focus_fn()
                time.sleep(0.15)
                snap(position)
                print(f"[JARVIS] {name} → {position} ✓")
            else:
                print(f"[JARVIS] {name} timed out")

        tasks = [
            ("VS Code", launch_vscode, lambda t: wait_for_process("Code",    t), lambda: focus_process("Code"),    "top-left",     STAGGER * 0),
            ("YouTube", launch_brave,  wait_brave,                                focus_brave,                      "top-right",    STAGGER * 1),
            ("Claude",  lambda: ps('Start-Process "claude"'),   lambda t: wait_for_process("claude",  t), lambda: focus_process("claude"),  "bottom-left",  STAGGER * 2),
            ("ChatGPT", lambda: ps('Start-Process "ChatGPT"'),  lambda t: wait_for_process("ChatGPT", t), lambda: focus_process("ChatGPT"), "bottom-right", STAGGER * 3),
        ]

        threads = [
            threading.Thread(target=run, args=(n, lf, wf, ff, pos, slot), daemon=True)
            for n, lf, wf, ff, pos, slot in tasks
        ]

        t0 = time.time()
        for t in threads: t.start()
        for t in threads: t.join(timeout=9)

        print(f"\n[JARVIS] ══ ALL SYSTEMS ONLINE in {time.time()-t0:.1f}s. GOOD EVENING, SIR. ══\n")

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
   ██║██╔══██╗██╔══██╗╚██╗ ██╔╝██║██╔════╝  Chrome-Kill Fix
   ██║███████║██████╔╝ ╚████╔╝ ██║███████╗
   ██║██╔══██║██╔══██╗  ╚██╔╝  ██║╚════██║  /launch or clap
   ██║██║  ██║██║  ██║   ██║   ██║███████║
   ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝╚══════╝
    """)

    if not GUI_OK:
        print("[JARVIS] ⚠  pip install pyautogui  ← needed for snapping!\n")
    if AUDIO_OK:
        threading.Thread(target=clap_listener, daemon=True).start()

    app.run(host="127.0.0.1", port=5000, debug=False)
