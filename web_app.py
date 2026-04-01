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
CACHE: dict[tuple[str, str, str], dict] = {}
EMOTION_META = {
    "happy": {"emoji": "😊", "color": "#16a34a"},
    "sad": {"emoji": "😔", "color": "#2563eb"},
    "angry": {"emoji": "😡", "color": "#dc2626"},
    "excited": {"emoji": "🤩", "color": "#f59e0b"},
    "calm": {"emoji": "😌", "color": "#14b8a6"},
    "concerned": {"emoji": "😟", "color": "#7c3aed"},
    "confident": {"emoji": "😎", "color": "#0f766e"},
    "apologetic": {"emoji": "🙇", "color": "#475569"},
    "inquisitive": {"emoji": "🤔", "color": "#0891b2"},
    "neutral": {"emoji": "😐", "color": "#6b7280"},
}
MODES = ["support", "sales", "therapy"]
PERSONALITIES = ["default", "female", "male"]


@app.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "text": "",
            "mode": "support",
            "personality": "default",
            "error": None,
            "audio_url": None,
            "audio_url_normal": None,
            "emotion": None,
            "emoji": None,
            "emotion_color": "#6b7280",
            "intensity": None,
            "intensity_bar": None,
            "intensity_pct": 0,
            "compound_score": None,
            "rate": None,
            "pitch": None,
            "volume": None,
            "modes": MODES,
            "personalities": PERSONALITIES,
            "debug": False,
            "debug_reasons": [],
            "debug_sentences": "",
            "explain_tip": "",
            "from_cache": False,
        },
    )


@app.get("/synthesize")
def synthesize_get() -> RedirectResponse:
    return RedirectResponse(url="/", status_code=307)


@app.post("/synthesize", response_class=HTMLResponse)
def synthesize(
    request: Request,
    text: str = Form(...),
    mode: str = Form("support"),
    personality: str = Form("default"),
    debug: str | None = Form(None),
) -> HTMLResponse:
    clean_text = text.strip()
    selected_mode = mode if mode in MODES else "support"
    selected_personality = personality if personality in PERSONALITIES else "default"
    debug_enabled = bool(debug)
    if not clean_text:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "text": text,
                "mode": selected_mode,
                "personality": selected_personality,
                "error": "Please enter some text before synthesizing.",
                "audio_url": None,
                "audio_url_normal": None,
                "emotion": None,
                "emoji": None,
                "emotion_color": "#6b7280",
                "intensity": None,
                "intensity_bar": None,
                "intensity_pct": 0,
                "compound_score": None,
                "rate": None,
                "pitch": None,
                "volume": None,
                "modes": MODES,
                "personalities": PERSONALITIES,
                "debug": debug_enabled,
                "debug_reasons": [],
                "debug_sentences": "",
                "explain_tip": "",
                "from_cache": False,
            },
        )

    cache_key = (clean_text, selected_mode, selected_personality)
    if cache_key in CACHE:
        payload = CACHE[cache_key]
        payload.update(
            {
                "text": clean_text,
                "mode": selected_mode,
                "personality": selected_personality,
                "modes": MODES,
                "personalities": PERSONALITIES,
                "debug": debug_enabled,
                "from_cache": True,
            }
        )
        if not debug_enabled:
            payload["debug_reasons"] = []
            payload["debug_sentences"] = ""
        return templates.TemplateResponse(request=request, name="index.html", context=payload)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output_file_emotional = OUTPUT_DIR / f"empathy_web_{stamp}.mp3"
    output_file_normal = OUTPUT_DIR / f"normal_web_{stamp}.mp3"

    emotion, fname_emotional = engine.synthesize_dynamic_to_file(
        clean_text, output_file_emotional, mode=selected_mode, personality=selected_personality
    )
    fname_normal = engine.synthesize_neutral_to_file(
        clean_text, output_file_normal, personality=selected_personality
    )
    config = engine.voice_config_for_emotion(emotion, mode=selected_mode)
    meta = EMOTION_META.get(emotion.label, EMOTION_META["neutral"])
    intensity_blocks = int(round(emotion.intensity * 10))
    intensity_bar = ("█" * intensity_blocks) + ("░" * (10 - intensity_blocks))
    intensity_pct = int(round(emotion.intensity * 100))

    payload = {
        "text": clean_text,
        "mode": selected_mode,
        "personality": selected_personality,
        "error": None,
        "audio_url": f"/output/{fname_emotional}",
        "audio_url_normal": f"/output/{fname_normal}",
        "emotion": emotion.label,
        "emoji": meta["emoji"],
        "emotion_color": meta["color"],
        "intensity": f"{emotion.intensity:.2f}",
        "intensity_bar": intensity_bar,
        "intensity_pct": intensity_pct,
        "compound_score": f"{emotion.compound_score:.3f}",
        "rate": config["rate"],
        "pitch": config["pitch"],
        "volume": f"{config['volume']:.2f}",
        "modes": MODES,
        "personalities": PERSONALITIES,
        "debug": debug_enabled,
        "debug_reasons": emotion.reasons if debug_enabled else [],
        "debug_sentences": " | ".join(engine.split_sentences(clean_text)) if debug_enabled else "",
        "explain_tip": "Detected from sentiment score, intensity, punctuation, and keywords.",
        "from_cache": False,
    }
    CACHE[cache_key] = dict(payload)
    return templates.TemplateResponse(request=request, name="index.html", context=payload)
