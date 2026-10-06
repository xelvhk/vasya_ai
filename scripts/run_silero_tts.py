"""Render a local Silero model to WAV in an optional PyTorch environment."""

from __future__ import annotations

import argparse
import json
import sys
import wave

import numpy as np
import torch


def render(model: object, text: str, output_path: str) -> None:
    samples = model.apply_tts(text=text, speaker="aidar", sample_rate=48000)
    pcm = (samples.detach().cpu().numpy().clip(-1, 1) * 32767).astype(np.int16)
    with wave.open(output_path, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(48000)
        output.writeframes(pcm.tobytes())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--text")
    parser.add_argument("--output")
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()

    torch.set_num_threads(4)
    model = torch.package.PackageImporter(args.model).load_pickle("tts_models", "model")
    model.to(torch.device("cpu"))
    if args.serve:
        print(json.dumps({"ready": True}), flush=True)
        for line in sys.stdin:
            try:
                request = json.loads(line)
                render(model, request["text"], request["output"])
                print(json.dumps({"ok": True}), flush=True)
            except Exception as exc:
                print(json.dumps({"error": str(exc)}), flush=True)
        return
    if not args.text or not args.output:
        parser.error("--text and --output are required outside --serve")
    render(model, args.text, args.output)


if __name__ == "__main__":
    main()
