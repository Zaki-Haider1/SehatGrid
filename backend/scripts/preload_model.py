from pathlib import Path
import hashlib
import json
import urllib.request

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
DEST = Path(__file__).resolve().parents[1] / "models" / "all-MiniLM-L6-v2"

if __name__ == "__main__":
    DEST.mkdir(parents=True, exist_ok=True)
    manifest = {"model": MODEL, "revision": REVISION, "pooling": "attention-mask mean + L2", "files": {}}
    for remote, name in [
        ("onnx/model.onnx", "model.onnx"),
        ("tokenizer.json", "tokenizer.json"),
        ("README.md", "MODEL_CARD.md"),
    ]:
        target = DEST / name
        if not target.exists():
            print("Downloading", remote, flush=True)
            urllib.request.urlretrieve(f"https://huggingface.co/{MODEL}/resolve/{REVISION}/{remote}", target)
        manifest["files"][name] = hashlib.sha256(target.read_bytes()).hexdigest()
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
