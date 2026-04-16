"""
tts_server.py — Lokaler TTS-Server für TTS Studio
==================================================
Unterstützt: Piper TTS, Pocket TTS
Start:       python tts_server.py
Port:        7734 (http://localhost:7734)

Abhängigkeiten:
    pip install flask flask-cors piper-tts

Für Pocket TTS zusätzlich:
    pip install pocket-tts

Für WAV→MP3-Konvertierung (optional, empfohlen):
    apt install ffmpeg   # Linux/Mac
    # oder: choco install ffmpeg  (Windows)
"""

import os
import io
import subprocess
import tempfile
import threading
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Erlaubt Anfragen vom Browser (localhost:file://)

# ── KONFIGURATION ──────────────────────────────────────────────────────────────

# Piper: Verzeichnis in dem die .onnx Modell-Dateien liegen
PIPER_MODELS_DIR = os.path.join(os.path.dirname(__file__), "piper_voices")

# Verfügbare Piper-Stimmen: { "voice_id": "pfad/zur/datei.onnx" }
# Ergänze hier deine heruntergeladenen Piper-Modelle.
# Download: https://huggingface.co/rhasspy/piper-voices
PIPER_VOICES = {
    "de_DE-thorsten-high":  os.path.join(PIPER_MODELS_DIR, "de_DE-thorsten-high.onnx"),
    "en_US-lessac-high":    os.path.join(PIPER_MODELS_DIR, "en_US-lessac-high.onnx"),
    "en_US-ryan-high":      os.path.join(PIPER_MODELS_DIR, "en_US-ryan-high.onnx"),
    "en_GB-cori-high":      os.path.join(PIPER_MODELS_DIR, "en_GB-cori-high.onnx"),
}

# Pocket TTS: verfügbare Stimmen (Namen so wie pocket-tts sie kennt)
POCKET_VOICES = ["alba", "marius", "javert", "jean", "fantine", "cosette", "eponine", "azelma"]

# Standard-Engine wenn keine angegeben
DEFAULT_ENGINE = "piper"   # "piper" oder "pocket"

# ── HILFSFUNKTIONEN ────────────────────────────────────────────────────────────

def wav_bytes_to_mp3_bytes(wav_data: bytes, bitrate: str = "128k") -> bytes:
    """Konvertiert WAV-Bytes zu MP3-Bytes via ffmpeg (falls installiert)."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-i", "pipe:0", "-b:a", bitrate, "-f", "mp3", "pipe:1"],
            input=wav_data, capture_output=True, timeout=60
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return wav_data  # Fallback: WAV zurückgeben wenn ffmpeg nicht verfügbar


def synthesize_piper(text: str, voice_id: str) -> bytes:
    """Synthetisiert Text mit Piper TTS, gibt WAV-Bytes zurück."""
    onnx_path = PIPER_VOICES.get(voice_id)
    if not onnx_path:
        raise ValueError(f"Piper-Stimme '{voice_id}' nicht konfiguriert.")
    if not os.path.exists(onnx_path):
        raise FileNotFoundError(
            f"Piper-Modell nicht gefunden: {onnx_path}\n"
            f"Download: https://huggingface.co/rhasspy/piper-voices"
        )

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        proc = subprocess.Popen(
            ["piper", "-m", onnx_path, "-f", tmp_path],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True
        )
        _, err = proc.communicate(text, timeout=120)
        if proc.returncode != 0:
            raise RuntimeError(f"Piper fehlgeschlagen: {err[-2000:]}")
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


def synthesize_pocket(text: str, voice_id: str) -> bytes:
    """Synthetisiert Text mit Pocket TTS, gibt WAV-Bytes zurück."""
    if voice_id not in POCKET_VOICES:
        raise ValueError(f"Pocket-Stimme '{voice_id}' nicht bekannt. Verfügbar: {POCKET_VOICES}")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            ["pocket-tts", "generate", "--voice", voice_id,
             "--text", text, "--output-path", tmp_path],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            raise RuntimeError(f"Pocket TTS fehlgeschlagen: {result.stderr[-2000:]}")
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


# ── ROUTEN ──────────────────────────────────────────────────────────────────────

@app.route("/ping", methods=["GET"])
def ping():
    """Health-Check — TTS Studio prüft hiermit ob der Server läuft."""
    piper_available = any(os.path.exists(p) for p in PIPER_VOICES.values())
    return jsonify({
        "status":  "ok",
        "engine":  DEFAULT_ENGINE,
        "piper_voices":  list(PIPER_VOICES.keys()),
        "pocket_voices": POCKET_VOICES,
        "piper_models_available": piper_available,
    })


@app.route("/tts", methods=["POST"])
def tts():
    """
    Hauptendpunkt für TTS-Synthese.
    Body (JSON):
        text    (str, Pflicht)
        voice   (str, Pflicht) — voice_id aus dem Plugin-JSON
        format  (str, optional) — "mp3" oder "wav", default "mp3"
        speed   (float, optional) — wird aktuell ignoriert (Piper/Pocket unterstützen kein Realtime-Speed)
        engine  (str, optional) — "piper" oder "pocket", überschreibt DEFAULT_ENGINE
    """
    data = request.get_json(force=True, silent=True) or {}

    text    = (data.get("text") or "").strip()
    voice   = (data.get("voice") or "").strip()
    fmt     = (data.get("format") or "mp3").lower()
    engine  = (data.get("engine") or DEFAULT_ENGINE).lower()

    if not text:
        return jsonify({"error": "Kein Text angegeben."}), 400
    if not voice:
        return jsonify({"error": "Keine Stimme angegeben."}), 400

    try:
        # Synthese
        if engine == "pocket":
            wav_data = synthesize_pocket(text, voice)
        else:
            wav_data = synthesize_piper(text, voice)

        # Format
        if fmt == "mp3":
            audio_data  = wav_bytes_to_mp3_bytes(wav_data)
            mimetype    = "audio/mpeg"
            filename    = "output.mp3"
        else:
            audio_data  = wav_data
            mimetype    = "audio/wav"
            filename    = "output.wav"

        return send_file(
            io.BytesIO(audio_data),
            mimetype=mimetype,
            as_attachment=False,
            download_name=filename,
        )

    except (ValueError, FileNotFoundError) as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Synthese fehlgeschlagen: {str(e)}"}), 500


@app.route("/voices", methods=["GET"])
def list_voices():
    """Gibt alle konfigurierten Stimmen zurück (nützlich für Debugging)."""
    voices = []
    for vid, path in PIPER_VOICES.items():
        voices.append({
            "id":       vid,
            "engine":   "piper",
            "available": os.path.exists(path),
            "model_path": path,
        })
    for vid in POCKET_VOICES:
        voices.append({
            "id":     vid,
            "engine": "pocket",
        })
    return jsonify({"voices": voices})


# ── START ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("TTS_PORT", 7734))
    print(f"\n{'='*54}")
    print(f"  TTS Studio — Lokaler Server")
    print(f"  http://localhost:{port}")
    print(f"{'='*54}")
    print(f"  Piper-Stimmen konfiguriert: {len(PIPER_VOICES)}")
    for vid, path in PIPER_VOICES.items():
        status = "✓" if os.path.exists(path) else "✗ (Modell fehlt)"
        print(f"    {status}  {vid}")
    print(f"  Pocket TTS Stimmen: {', '.join(POCKET_VOICES)}")
    print(f"  Modell-Ordner: {PIPER_MODELS_DIR}")
    print(f"{'='*54}\n")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
