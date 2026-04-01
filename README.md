# The Empathy Engine: Emotion-Aware Voice Synthesis

The Empathy Engine is a Python service that converts text into speech while dynamically modulating vocal delivery based on detected emotion.

It satisfies the challenge requirements by:
- Accepting text input via CLI argument or prompt.
- Detecting emotion using sentiment analysis (`positive`, `negative`, `neutral`).
- Mapping emotion to vocal parameters.
- Modulating at least two voice parameters (`rate` and `volume`).
- Generating a playable audio file (`.wav`).
- Providing a FastAPI web interface with text input and embedded audio playback.

## How It Works

1. **Emotion Detection**
   - Uses `vaderSentiment` to compute a compound sentiment score from input text.
   - Classifies emotion:
     - `positive` if compound >= `0.25`
     - `negative` if compound <= `-0.25`
     - `neutral` otherwise

2. **Intensity Scaling (Bonus)**
   - Emotion intensity is based on absolute compound score.
   - Adds emphasis boost from punctuation and all-caps words (e.g., `!`, `?`, `AMAZING`) to scale delivery changes.

3. **Emotion-to-Voice Mapping**
   - Positive: faster + slightly louder
   - Negative: slower + softer
   - Neutral: close to baseline

4. **Speech Synthesis**
   - Uses `pyttsx3` to create offline TTS output.
   - Saves spoken text to a `.wav` file.

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
python main.py --text "I am sorry this has been frustrating. Let me help." --output output\custom.wav
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
- Emotion-aware speech synthesis
- Embedded audio player
- Download link for generated `.wav`

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
- **Why pyttsx3?**
  - Offline-friendly and simple to prototype quickly without API keys.
- **Why rate + volume?**
  - Reliable cross-platform control with `pyttsx3`, enabling immediate emotional modulation.
- **Why intensity scaling?**
  - Better realism: strongly emotional text should sound more expressive than mildly emotional text.

## Notes and Limitations

- Voice timbre/pitch control depends on platform-specific TTS drivers. This implementation guarantees modulation of `rate` and `volume`.
- If your platform's TTS backend is missing audio voices, install a system voice pack and retry.

## Next Improvements (Stretch Goals)

- Add nuanced emotion labels (e.g., `concerned`, `excited`, `inquisitive`) using a Transformer model.
- Add multi-voice selection and persona presets (e.g., support, sales, concierge).
- Add SSML-style emphasis and pause controls (with a provider that supports SSML).

