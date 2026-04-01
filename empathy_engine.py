from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from typing import Dict, List, Tuple

import wave

import pyttsx3
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

try:
    import edge_tts
except ImportError:
    edge_tts = None

try:
    from pydub import AudioSegment
except ImportError:
    AudioSegment = None  # type: ignore[misc, assignment]


@dataclass
class EmotionResult:
    label: str
    intensity: float
    compound_score: float
    reasons: List[str]


class EmpathyEngine:
    """
    Detects emotion in text and synthesizes expressive speech.
    """

    def __init__(self) -> None:
        self.analyzer = SentimentIntensityAnalyzer()
        # Use-case presets: applied on top of emotion (clear SaaS-style differentiation).
        # Support  = slower, calmer, lower pitch
        # Sales    = faster, brighter, louder
        # Therapy  = very slow, soft, warm (low pitch)
        self.mode_profiles: Dict[str, Dict[str, float]] = {
            "support": {"rate_delta": -22, "pitch_delta": -5, "volume_delta": -0.05},
            "sales": {"rate_delta": 26, "pitch_delta": 8, "volume_delta": 0.07},
            "therapy": {"rate_delta": -38, "pitch_delta": -8, "volume_delta": -0.14},
        }
        self.use_edge = os.environ.get("EMPATHY_USE_EDGE", "1").strip().lower() not in (
            "0",
            "false",
            "no",
            "off",
        )

    def detect_emotion(self, text: str) -> EmotionResult:
        if not text or not text.strip():
            return EmotionResult(label="neutral", intensity=0.0, compound_score=0.0, reasons=["Empty text"])

        lower = text.lower()
        sentiment = self.analyzer.polarity_scores(text)
        compound = sentiment["compound"]
        intensity = min(1.0, abs(compound) + self._emphasis_boost(text))
        reasons: List[str] = [f"compound={compound:.3f}", f"intensity={intensity:.2f}"]

        angry_words = {"angry", "furious", "annoyed", "upset", "mad", "outraged", "frustrated"}
        sad_words = {"sad", "disappointed", "unhappy", "down", "depressed", "heartbroken"}
        calm_words = {"calm", "steady", "relaxed", "peaceful", "gentle", "patient"}
        excited_words = {"excited", "thrilled", "amazing", "awesome", "fantastic", "best"}
        happy_words = {"happy", "glad", "great", "good", "delighted", "wonderful", "pleased"}
        concerned_words = {"concerned", "worried", "issue", "problem", "risk", "trouble"}
        apologetic_words = {"sorry", "apologize", "apologies", "regret"}
        confident_words = {"confident", "definitely", "absolutely", "certain", "guarantee"}

        if self._contains_any(lower, apologetic_words):
            label = "apologetic"
            reasons.append("apology keyword")
        elif "?" in text and -0.2 <= compound <= 0.35:
            label = "inquisitive"
            reasons.append("question pattern")
        elif self._contains_any(lower, concerned_words):
            label = "concerned"
            reasons.append("concern keyword")
        elif self._contains_any(lower, confident_words) or compound >= 0.7:
            label = "confident"
            reasons.append("confidence keyword/very positive score")
        elif self._contains_any(lower, angry_words) or compound <= -0.55:
            label = "angry"
            reasons.append("anger signal")
        elif self._contains_any(lower, sad_words) or compound <= -0.2:
            label = "sad"
            reasons.append("sad signal")
        elif self._contains_any(lower, excited_words) or (compound > 0.55 and intensity > 0.55):
            label = "excited"
            reasons.append("high positive + high intensity")
        elif self._contains_any(lower, happy_words) or compound > 0.2:
            label = "happy"
            reasons.append("positive signal")
        elif self._contains_any(lower, calm_words):
            label = "calm"
            reasons.append("calm keyword")
        else:
            label = "neutral"
            reasons.append("no strong emotion markers")

        return EmotionResult(label=label, intensity=intensity, compound_score=compound, reasons=reasons)

    def voice_config_for_emotion(self, emotion: EmotionResult, mode: str = "support") -> Dict[str, float]:
        """
        Maps emotion + intensity to rate/pitch/volume.
        """
        base_rate = 170
        base_pitch = 50
        base_volume = 0.9

        intensity = emotion.intensity

        if emotion.label == "happy":
            rate = int(base_rate + 28 + 70 * intensity)
            pitch = int(base_pitch + 14 + 36 * intensity)
            volume = min(1.0, base_volume + 0.08 + 0.18 * intensity)
        elif emotion.label == "sad":
            rate = int(base_rate - 36 - 82 * intensity)
            pitch = int(base_pitch - 18 - 42 * intensity)
            volume = max(0.42, base_volume - 0.14 - 0.34 * intensity)
        elif emotion.label == "angry":
            rate = int(base_rate + 30 + 76 * intensity)
            pitch = int(base_pitch + 16 + 40 * intensity)
            volume = min(1.0, base_volume + 0.14 + 0.2 * intensity)
        elif emotion.label == "excited":
            rate = int(base_rate + 34 + 80 * intensity)
            pitch = int(base_pitch + 18 + 42 * intensity)
            volume = min(1.0, base_volume + 0.16 + 0.22 * intensity)
        elif emotion.label == "calm":
            rate = int(base_rate - 16 - 38 * intensity)
            pitch = int(base_pitch - 8 - 20 * intensity)
            volume = max(0.58, base_volume - 0.05 - 0.14 * intensity)
        elif emotion.label == "concerned":
            rate = int(base_rate - 10 - 30 * intensity)
            pitch = int(base_pitch - 3 - 14 * intensity)
            volume = max(0.6, base_volume - 0.05 - 0.12 * intensity)
        elif emotion.label == "confident":
            rate = int(base_rate + 12 + 40 * intensity)
            pitch = int(base_pitch + 6 + 20 * intensity)
            volume = min(1.0, base_volume + 0.06 + 0.12 * intensity)
        elif emotion.label == "apologetic":
            rate = int(base_rate - 14 - 34 * intensity)
            pitch = int(base_pitch - 6 - 18 * intensity)
            volume = max(0.56, base_volume - 0.08 - 0.14 * intensity)
        elif emotion.label == "inquisitive":
            rate = int(base_rate + 2 + 18 * intensity)
            pitch = int(base_pitch + 6 + 24 * intensity)
            volume = min(1.0, base_volume + 0.02 + 0.08 * intensity)
        else:
            rate = int(base_rate + 10 * (0.5 - intensity))
            pitch = base_pitch
            volume = base_volume

        profile = self.mode_profiles.get(
            mode, {"rate_delta": 0.0, "pitch_delta": 0.0, "volume_delta": 0.0}
        )
        rate = int(rate + profile["rate_delta"])
        pitch = int(pitch + profile["pitch_delta"])
        volume = max(0.0, min(1.0, volume + profile["volume_delta"]))
        # Natural bounds: avoid extreme chipmunk/robot edges.
        rate = max(95, min(320, rate))
        pitch = max(0, min(100, pitch))

        return {"rate": rate, "pitch": pitch, "volume": volume}

    @staticmethod
    def _edge_voice_id(personality: str) -> str:
        if personality == "male":
            return "en-US-GuyNeural"
        if personality == "female":
            return "en-US-AriaNeural"
        return "en-US-JennyNeural"

    @staticmethod
    def _config_to_edge_strings(rate: int, pitch: int, volume: float) -> tuple[str, str, str]:
        """Map numeric pyttsx3-style config to Edge TTS prosody strings."""
        pct = (rate - 170) / 170 * 100
        pct = max(-50.0, min(50.0, pct))
        rate_s = f"{pct:+.0f}%"
        hz = (pitch - 50) * 0.55
        hz = max(-20.0, min(20.0, hz))
        pitch_s = f"{hz:+.0f}Hz"
        vol = (volume - 0.9) * 100
        vol = max(-25.0, min(25.0, vol))
        vol_s = f"{vol:+.0f}%"
        return rate_s, pitch_s, vol_s

    def _run_edge_save(
        self,
        text: str,
        out: Path,
        voice: str,
        rate_s: str,
        pitch_s: str,
        vol_s: str,
    ) -> None:
        if not edge_tts:
            raise RuntimeError("edge-tts not installed")

        async def _go() -> None:
            communicate = edge_tts.Communicate(
                text,
                voice=voice,
                rate=rate_s,
                pitch=pitch_s,
                volume=vol_s,
            )
            await communicate.save(str(out))

        asyncio.run(_go())

    def synthesize_to_file(self, text: str, output_path: str | Path, mode: str = "support") -> EmotionResult:
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty.")

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        emotion = self.detect_emotion(text)
        config = self.voice_config_for_emotion(emotion, mode=mode)
        processed_text = self.prepare_text_for_expression(text, emotion)

        engine = pyttsx3.init()
        engine.setProperty("rate", config["rate"])
        # Some engines may ignore this property; we still set it for compatible drivers.
        engine.setProperty("pitch", config["pitch"])
        engine.setProperty("volume", config["volume"])
        engine.save_to_file(processed_text, str(output))
        engine.runAndWait()
        engine.stop()

        return emotion

    def synthesize_dynamic_to_file(
        self,
        text: str,
        output_path: str | Path,
        mode: str = "support",
        personality: str = "default",
    ) -> Tuple[EmotionResult, str]:
        """
        Emotional TTS: prefer Microsoft Edge neural voices (human-like), else pyttsx3.
        Returns (emotion, output filename basename).
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.suffix.lower() != ".mp3":
            output = output.with_suffix(".mp3")

        sentences = self.split_sentences(text)
        if not sentences:
            raise ValueError("Input text cannot be empty.")

        if self.use_edge and edge_tts:
            try:
                return self._synthesize_dynamic_edge(text, output, mode, personality, sentences)
            except Exception:
                pass

        return self._synthesize_dynamic_pyttsx3(output, mode, personality, sentences)

    def _synthesize_dynamic_edge(
        self,
        text: str,
        out: Path,
        mode: str,
        personality: str,
        sentences: List[str],
    ) -> Tuple[EmotionResult, str]:
        voice = self._edge_voice_id(personality)

        if len(sentences) > 1 and AudioSegment is None:
            emotion = self.detect_emotion(text)
            cfg = self.voice_config_for_emotion(emotion, mode=mode)
            r_s, p_s, v_s = self._config_to_edge_strings(cfg["rate"], cfg["pitch"], cfg["volume"])
            self._run_edge_save(text.strip(), out, voice, r_s, p_s, v_s)
            return emotion, out.name

        if len(sentences) == 1:
            emotion = self.detect_emotion(sentences[0])
            cfg = self.voice_config_for_emotion(emotion, mode=mode)
            r_s, p_s, v_s = self._config_to_edge_strings(cfg["rate"], cfg["pitch"], cfg["volume"])
            self._run_edge_save(sentences[0].strip(), out, voice, r_s, p_s, v_s)
            return emotion, out.name

        mp3_parts: List[Path] = []
        first_emotion: EmotionResult | None = None
        with TemporaryDirectory() as tmp:
            for idx, sentence in enumerate(sentences):
                emotion = self.detect_emotion(sentence)
                if first_emotion is None:
                    first_emotion = emotion
                cfg = self.voice_config_for_emotion(emotion, mode=mode)
                r_s, p_s, v_s = self._config_to_edge_strings(cfg["rate"], cfg["pitch"], cfg["volume"])
                part = Path(tmp) / f"part_{idx}.mp3"
                self._run_edge_save(sentence.strip(), part, voice, r_s, p_s, v_s)
                mp3_parts.append(part)

            if AudioSegment is not None:
                try:
                    merged = AudioSegment.empty()
                    for pth in mp3_parts:
                        merged += AudioSegment.from_mp3(str(pth))
                    merged.export(str(out), format="mp3")
                    return (
                        first_emotion
                        if first_emotion
                        else EmotionResult(
                            label="neutral",
                            intensity=0.0,
                            compound_score=0.0,
                            reasons=["fallback"],
                        ),
                        out.name,
                    )
                except Exception:
                    pass

        emotion = self.detect_emotion(text)
        cfg = self.voice_config_for_emotion(emotion, mode=mode)
        r_s, p_s, v_s = self._config_to_edge_strings(cfg["rate"], cfg["pitch"], cfg["volume"])
        self._run_edge_save(text.strip(), out, voice, r_s, p_s, v_s)
        return emotion, out.name

    def _synthesize_dynamic_pyttsx3(
        self,
        output: Path,
        mode: str,
        personality: str,
        sentences: List[str],
    ) -> Tuple[EmotionResult, str]:
        wav_out = output.with_suffix(".wav")
        with TemporaryDirectory() as tmp_dir:
            tmp_paths: List[Path] = []
            first_emotion: EmotionResult | None = None
            for idx, sentence in enumerate(sentences):
                emotion = self.detect_emotion(sentence)
                if first_emotion is None:
                    first_emotion = emotion
                cfg = self.voice_config_for_emotion(emotion, mode=mode)
                processed = self.prepare_text_for_expression(sentence, emotion)
                temp_path = Path(tmp_dir) / f"part_{idx}.wav"
                self._save_with_config(processed, temp_path, cfg, personality=personality)
                tmp_paths.append(temp_path)

            self._concat_wav_files(tmp_paths, wav_out)

        emotion = first_emotion or EmotionResult(
            label="neutral", intensity=0.0, compound_score=0.0, reasons=["fallback"]
        )
        return emotion, wav_out.name

    def synthesize_neutral_to_file(
        self, text: str, output_path: str | Path, personality: str = "default"
    ) -> str:
        """Baseline TTS for A/B: same neural voice, flat prosody (or pyttsx3 fallback)."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.suffix.lower() != ".mp3":
            output = output.with_suffix(".mp3")

        voice = self._edge_voice_id(personality)
        if self.use_edge and edge_tts:
            try:
                self._run_edge_save(text.strip(), output, voice, "+0%", "+0Hz", "+0%")
                return output.name
            except Exception:
                pass

        wav_out = output.with_suffix(".wav")
        engine = pyttsx3.init()
        self._apply_personality_voice(engine, personality)
        engine.setProperty("rate", 170)
        engine.setProperty("pitch", 50)
        engine.setProperty("volume", 0.9)
        engine.save_to_file(text, str(wav_out))
        engine.runAndWait()
        engine.stop()
        return wav_out.name

    def prepare_text_for_expression(self, text: str, emotion: EmotionResult) -> str:
        # Light breaths only—heavy "..." after every comma sounds robotic on SAPI.
        # Sentence boundaries get a short pause; commas stay natural.
        paused = re.sub(r"([.!?])\s+", r"\1 .. ", text.strip())
        paused = re.sub(r"([;:])\s*", r"\1 .. ", paused)
        return paused

    @staticmethod
    def split_sentences(text: str) -> List[str]:
        parts = re.split(r"(?<=[.!?])\s+", text.strip())
        return [p.strip() for p in parts if p.strip()]

    def _save_with_config(
        self, text: str, output_path: Path, config: Dict[str, float], personality: str = "default"
    ) -> None:
        engine = pyttsx3.init()
        self._apply_personality_voice(engine, personality)
        engine.setProperty("rate", config["rate"])
        engine.setProperty("pitch", config["pitch"])
        engine.setProperty("volume", config["volume"])
        engine.save_to_file(text, str(output_path))
        engine.runAndWait()
        engine.stop()

    @staticmethod
    def _concat_wav_files(parts: List[Path], output: Path) -> None:
        first = wave.open(str(parts[0]), "rb")
        params = first.getparams()
        frames = [first.readframes(first.getnframes())]
        first.close()

        for p in parts[1:]:
            wf = wave.open(str(p), "rb")
            if wf.getparams()[:3] != params[:3]:
                wf.close()
                continue
            frames.append(wf.readframes(wf.getnframes()))
            wf.close()

        out = wave.open(str(output), "wb")
        out.setparams(params)
        for frame in frames:
            out.writeframes(frame)
        out.close()

    @staticmethod
    def _apply_personality_voice(engine: pyttsx3.Engine, personality: str) -> None:
        voices = engine.getProperty("voices")
        if not voices:
            return
        if personality == "male":
            for v in voices:
                name = (getattr(v, "name", "") or "").lower()
                if "male" in name or "david" in name:
                    engine.setProperty("voice", v.id)
                    return
        elif personality == "female":
            for v in voices:
                name = (getattr(v, "name", "") or "").lower()
                if "female" in name or "zira" in name or "hazel" in name:
                    engine.setProperty("voice", v.id)
                    return

    @staticmethod
    def _emphasis_boost(text: str) -> float:
        exclamation_count = text.count("!")
        question_count = text.count("?")
        uppercase_words = sum(1 for word in text.split() if len(word) > 2 and word.isupper())

        boost = min(0.35, exclamation_count * 0.04 + question_count * 0.02 + uppercase_words * 0.05)
        return boost

    @staticmethod
    def _contains_any(text: str, words: set[str]) -> bool:
        return any(word in text for word in words)
