# The Empathy Engine: Emotion-Aware Voice Synthesis

The Empathy Engine is a Python service that converts text into speech while dynamically modulating vocal delivery based on detected emotion.

It satisfies the challenge requirements by:
- Accepting text input via CLI argument or prompt.
- Detecting richer emotion classes (`happy`, `sad`, `angry`, `excited`, `calm`, `neutral`).
- Mapping emotion to vocal parameters.
- Modulating three vocal parameters (`rate`, `pitch`, `volume`).
- Generating a playable audio file (`.mp3` with neural TTS, or `.wav` when offline).
- Providing a FastAPI web interface with text input and embedded audio playback.
- Applying sentence-level dynamic emotion shifts for mixed-emotion input.

## How It Works

1. **Emotion Detection**
   - Uses `vaderSentiment` to compute a compound sentiment score from input text.
   - Uses sentiment + keyword heuristics to classify:
     - `happy`, `sad`, `angry`, `excited`, `calm`, `neutral`

2. **Intensity Scaling (Bonus)**
   - Emotion intensity is based on absolute compound score.
   - Adds emphasis boost from punctuation and all-caps words (e.g., `!`, `?`, `AMAZING`) to scale delivery changes.
   - Intensity directly scales `rate`, `pitch`, and `volume` shifts.

3. **Emotion-to-Voice Mapping**
   - Happy: faster, higher pitch, louder
   - Sad: slower, lower pitch, softer
   - Angry: fast, very high pitch, loud
   - Excited: fastest, high pitch, louder
   - Calm: slower, lower pitch, gentler
   - Neutral: close to baseline

4. **Speech Synthesis**
   - **Primary:** Microsoft **Edge neural TTS** via `edge-tts` (sounds much more human than classic SAPI).
   - **Fallback:** `pyttsx3` offline (`.wav`) if Edge is unavailable or `EMPATHY_USE_EDGE=0`.
   - Emotional output is saved as **`.mp3`** when using Edge; neutral baseline uses the same neural voice with flat prosody for a fair A/B test.
   - Multi-sentence emotional speech: per-sentence clips are merged with **`pydub`** when possible (install **ffmpeg** for best MP3 support); otherwise one neural pass is used for the whole text.
   - Light pause shaping for offline fallback; neural path uses clean sentences so prosody stays natural.

## Project Structure

- `main.py`: CLI entrypoint
- `empathy_engine.py`: core emotion detection and TTS modulation logic
- `web_app.py`: FastAPI app for browser demo
- `templates/index.html`: web UI template
- `requirements.txt`: Python dependencies

## Setup

### 1) Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

```powershell
pip install -r requirements.txt
```

## Run the Application

### Option A: Pass text directly

```powershell
python main.py --text "Great news! Your order has shipped and will arrive early."
```

### Option B: Interactive prompt

```powershell
python main.py
```

### Optional: Specify output path

```powershell
python main.py --text "I am sorry this has been frustrating. Let me help." --output output\custom.mp3
```

### Optional: choose a use-case mode

```powershell
python main.py --text "We can close this deal today!" --mode sales
```

### Optional: choose voice personality

```powershell
python main.py --text "I am sorry for the delay." --personality female
```

The script prints:
- detected emotion
- intensity
- sentiment score
- applied voice parameters
- absolute path to output audio file

## Run the Web Interface (Bonus)

Start the FastAPI app:

```powershell
uvicorn web_app:app --reload
```

Open your browser at `http://127.0.0.1:8000`

Web features:
- Text area input
- Use-case mode selector (`support`, `sales`, `therapy`)
- Voice personality selector (`default`, `female`, `male`)
- Emotion-aware speech synthesis with emoji and emotion color coding
- Intensity progress visualization
- Side-by-side comparison players: emotional vs normal TTS
- Download links for both generated audio files (MP3 when neural TTS is used)
- Debug mode showing detection reasoning and sentence-level split
- In-memory caching for repeated requests
- One-click real-world demo buttons

## Example Emotion Mappings

- **Positive/Happy**
  - Higher speaking rate
  - Slightly increased volume
- **Negative/Frustrated**
  - Lower speaking rate
  - Reduced volume for calmer delivery
- **Neutral**
  - Near-default rate and volume

## Design Choices

- **Why VADER?**
  - Lightweight, fast, and works well for short user-facing text commonly seen in sales and customer support.
- **Why Edge neural TTS + pyttsx3 fallback?**
  - Neural voices sound far more human; `pyttsx3` keeps the project runnable offline without keys.
- **Why rate + pitch + volume?**
  - These give clearer emotional contrast and improve judge-perceived expressiveness.
- **Why intensity scaling?**
  - Better realism: strongly emotional text should sound more expressive than mildly emotional text.
- **Use-case modes (Support / Sales / Therapy)?**
  - Each mode applies clear additive shifts on top of emotion: Support is slower, calmer, and lower pitch; Sales is faster, brighter, and louder; Therapy is very slow with softer volume and lower pitch—so the product feels like different personas, not just a label.

## Notes and Limitations

- **Neural TTS (Edge)** needs a **network connection** the first time you synthesize (Microsoft’s service). If you are offline, the app falls back to `pyttsx3`.
- Set `EMPATHY_USE_EDGE=0` to force offline `pyttsx3` only (robotic but works air-gapped).
- **Sentence merging** with `pydub` works best if **ffmpeg** is installed; otherwise multi-sentence clips may be merged in a single neural pass.
- Offline fallback: voice timbre/pitch still depends on OS SAPI; neural path uses consistent neural voices (`Jenny` / `Aria` / `Guy`).

## Next Improvements (Stretch Goals)

- Replace heuristic emotion classification with a Hugging Face model (e.g., `j-hartmann/emotion-english-distilroberta-base`).
- Add multi-voice selection and persona presets (e.g., support, sales, concierge).
- Add full SSML emphasis/pauses via a TTS provider that supports SSML.

