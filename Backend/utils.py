"""
utils.py — PowerShell runner + window helpers
"""

import subprocess, time

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
# BRAVE WINDOW HELPERS
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

# ══════════════════════════════════
# FOCUS HELPERS
# ══════════════════════════════════

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