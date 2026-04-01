from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from empathy_engine import EmpathyEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Empathy Engine: emotion-aware text-to-speech synthesis"
    )
    parser.add_argument(
        "--text",
        type=str,
        help="Input text to synthesize. If omitted, an interactive prompt is shown.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output audio file path. Defaults to output/empathy_<timestamp>.wav",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    text = args.text if args.text else input("Enter text to synthesize: ").strip()
    if not text:
        raise SystemExit("No input text provided.")

    output_path = args.output
    if not output_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(Path("output") / f"empathy_{timestamp}.wav")

    engine = EmpathyEngine()
    emotion = engine.synthesize_to_file(text=text, output_path=output_path)
    config = engine.voice_config_for_emotion(emotion)

    print("Synthesis complete.")
    print(f"Detected emotion: {emotion.label}")
    print(f"Emotion intensity: {emotion.intensity:.2f}")
    print(f"Compound sentiment score: {emotion.compound_score:.3f}")
    print(f"Applied rate: {config['rate']}")
    print(f"Applied volume: {config['volume']:.2f}")
    print(f"Audio file: {Path(output_path).resolve()}")


if __name__ == "__main__":
    main()
