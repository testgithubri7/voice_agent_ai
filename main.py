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
        help="Output audio file path. Defaults to output/empathy_<timestamp>.mp3 (neural) or .wav if offline fallback.",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="support",
        choices=["support", "sales", "therapy"],
        help="Use-case preset that adjusts delivery style.",
    )
    parser.add_argument(
        "--personality",
        type=str,
        default="default",
        choices=["default", "female", "male"],
        help="Voice personality selector.",
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
        output_path = str(Path("output") / f"empathy_{timestamp}.mp3")

    engine = EmpathyEngine()
    emotion, out_name = engine.synthesize_dynamic_to_file(
        text=text,
        output_path=output_path,
        mode=args.mode,
        personality=args.personality,
    )
    config = engine.voice_config_for_emotion(emotion, mode=args.mode)

    print("Synthesis complete.")
    print(f"Mode: {args.mode}")
    print(f"Personality: {args.personality}")
    print(f"Detected emotion: {emotion.label}")
    print(f"Emotion intensity: {emotion.intensity:.2f}")
    print(f"Compound sentiment score: {emotion.compound_score:.3f}")
    print(f"Applied rate: {config['rate']}")
    print(f"Applied pitch: {config['pitch']}")
    print(f"Applied volume: {config['volume']:.2f}")
    print(f"Reasoning: {', '.join(emotion.reasons)}")
    out_dir = Path(output_path).resolve().parent
    print(f"Audio file: {(out_dir / out_name).resolve()}")


if __name__ == "__main__":
    main()
