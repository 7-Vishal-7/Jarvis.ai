"""
clap.py — double-clap detector via microphone
"""

import threading, time

try:
    import pyaudio, numpy as np
    AUDIO_OK = True
except ImportError:
    AUDIO_OK = False

CLAP_THRESHOLD     = 2500
DOUBLE_CLAP_WINDOW = 0.6
COOLDOWN_SECONDS   = 5.0

def clap_listener(launch_fn):
    """
    Listens for double-clap and calls launch_fn() when detected.
    Pass launch_workspace as launch_fn.
    """
    if not AUDIO_OK:
        print("[JARVIS] PyAudio not found — clap detection disabled")
        print("[JARVIS] Run: pip install pyaudio numpy")
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
                    last_launch = now
                    last_clap   = 0
                    threading.Thread(target=launch_fn, daemon=True).start()
                else:
                    print(f"[JARVIS] Clap 1 (amp={amp:.0f}) — waiting...")
                    last_clap = now
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()