"""
app.py — J.A.R.V.I.S Flask entry point

Run: python app.py
  → http://127.0.0.1:5000/launch   (or double-clap)

File structure:
  backend/
    app.py        ← you are here (Flask + main)
    launcher.py   ← 4-app launch sequence
    clap.py       ← microphone double-clap detector
    utils.py      ← PowerShell runner + window helpers
"""

from flask import Flask, jsonify
import threading

from launcher import launch_workspace, GUI_OK
from clap import clap_listener, AUDIO_OK

app = Flask(__name__)

# ══════════════════════════════════
# ROUTES
# ══════════════════════════════════

@app.route("/")
def index():
    return jsonify({
        "jarvis":  "online",
        "version": "Mark XXVI",
        "audio":   AUDIO_OK,
        "gui":     GUI_OK,
    })

@app.route("/launch")
def route_launch():
    threading.Thread(target=launch_workspace, daemon=True).start()
    return jsonify({"status": "launching", "message": "Protocol Stark activated"})

@app.route("/health")
def health():
    return jsonify({"audio": AUDIO_OK, "gui": GUI_OK})

# ══════════════════════════════════
# MAIN
# ══════════════════════════════════

if __name__ == "__main__":
    print("""
   ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗  Mark XXVI
   ██║██╔══██╗██╔══██╗╚██╗ ██╔╝██║██╔════╝
   ██║███████║██████╔╝ ╚████╔╝ ██║███████╗  /launch  or
   ██║██╔══██║██╔══██╗  ╚██╔╝  ██║╚════██║  double-clap
   ██║██║  ██║██║  ██║   ██║   ██║███████║
   ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚═╝╚══════╝
    """)

    if not GUI_OK:
        print("[JARVIS] ⚠  pip install pyautogui  ← needed for window snapping!\n")

    # Start clap listener in background
    if AUDIO_OK:
        threading.Thread(
            target=clap_listener,
            args=(launch_workspace,),   # pass the function to call on clap
            daemon=True
        ).start()
    else:
        print("[JARVIS] pip install pyaudio numpy  ← for clap detection\n")

    app.run(host="127.0.0.1", port=5000, debug=False)