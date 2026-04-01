from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from empathy_engine import EmpathyEngine


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
TEMPLATES_DIR = BASE_DIR / "templates"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Empathy Engine")
app.mount("/output", StaticFiles(directory=str(OUTPUT_DIR)), name="output")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

engine = EmpathyEngine()


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "text": "",
            "error": None,
            "audio_url": None,
            "emotion": None,
            "intensity": None,
            "compound_score": None,
            "rate": None,
            "volume": None,
        },
    )


@app.get("/synthesize")
def synthesize_get() -> RedirectResponse:
    return RedirectResponse(url="/", status_code=307)


@app.post("/synthesize", response_class=HTMLResponse)
def synthesize(request: Request, text: str = Form(...)) -> HTMLResponse:
    clean_text = text.strip()
    if not clean_text:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "text": text,
                "error": "Please enter some text before synthesizing.",
                "audio_url": None,
                "emotion": None,
                "intensity": None,
                "compound_score": None,
                "rate": None,
                "volume": None,
            },
        )

    filename = f"empathy_web_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.wav"
    output_file = OUTPUT_DIR / filename

    emotion = engine.synthesize_to_file(clean_text, output_file)
    config = engine.voice_config_for_emotion(emotion)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "text": clean_text,
            "error": None,
            "audio_url": f"/output/{filename}",
            "emotion": emotion.label,
            "intensity": f"{emotion.intensity:.2f}",
            "compound_score": f"{emotion.compound_score:.3f}",
            "rate": config["rate"],
            "volume": f"{config['volume']:.2f}",
        },
    )
