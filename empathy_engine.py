from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import pyttsx3
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


@dataclass
class EmotionResult:
    label: str
    intensity: float
    compound_score: float


class EmpathyEngine:
    """
    Detects emotion in text and synthesizes expressive speech.
    """

    def __init__(self) -> None:
        self.analyzer = SentimentIntensityAnalyzer()

    def detect_emotion(self, text: str) -> EmotionResult:
        if not text or not text.strip():
            return EmotionResult(label="neutral", intensity=0.0, compound_score=0.0)

        sentiment = self.analyzer.polarity_scores(text)
        compound = sentiment["compound"]
        intensity = min(1.0, abs(compound) + self._emphasis_boost(text))

        if compound >= 0.25:
            label = "positive"
        elif compound <= -0.25:
            label = "negative"
        else:
            label = "neutral"

        return EmotionResult(label=label, intensity=intensity, compound_score=compound)

    def voice_config_for_emotion(self, emotion: EmotionResult) -> Dict[str, float]:
        """
        Maps emotion + intensity to rate/volume.
        """
        base_rate = 170
        base_volume = 0.9

        intensity = emotion.intensity

        if emotion.label == "positive":
            rate = int(base_rate + 20 + 40 * intensity)
            volume = min(1.0, base_volume + 0.05 + 0.05 * intensity)
        elif emotion.label == "negative":
            rate = int(base_rate - 20 - 35 * intensity)
            volume = max(0.55, base_volume - 0.12 - 0.2 * intensity)
        else:
            rate = int(base_rate + 10 * (0.5 - intensity))
            volume = base_volume

        return {"rate": rate, "volume": volume}

    def synthesize_to_file(self, text: str, output_path: str | Path) -> EmotionResult:
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty.")

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        emotion = self.detect_emotion(text)
        config = self.voice_config_for_emotion(emotion)

        engine = pyttsx3.init()
        engine.setProperty("rate", config["rate"])
        engine.setProperty("volume", config["volume"])
        engine.save_to_file(text, str(output))
        engine.runAndWait()
        engine.stop()

        return emotion

    @staticmethod
    def _emphasis_boost(text: str) -> float:
        exclamation_count = text.count("!")
        question_count = text.count("?")
        uppercase_words = sum(1 for word in text.split() if len(word) > 2 and word.isupper())

        boost = min(0.35, exclamation_count * 0.04 + question_count * 0.02 + uppercase_words * 0.05)
        return boost
