"""Reviewed semantic suggestions using the pinned MiniLM ONNX export."""

from functools import lru_cache
from pathlib import Path
import hashlib
import json
import unicodedata
import re
import numpy as np
from rapidfuzz import fuzz
from ..config import get_settings
from .common import add, stamp, require, get, operator, planner, audit


def normalize(value):
    return re.sub(r"[^\w\s]", " ", unicodedata.normalize("NFKC", value).casefold()).strip()


class Matcher:
    def __init__(self):
        import onnxruntime as ort
        from tokenizers import Tokenizer

        path = Path(get_settings().embedding_model_path)
        if not path.is_absolute():
            path = Path(__file__).resolve().parents[2] / path
        self.manifest = json.loads((path / "manifest.json").read_text())
        for name, expected in self.manifest["files"].items():
            if hashlib.sha256((path / name).read_bytes()).hexdigest() != expected:
                raise RuntimeError(f"Embedding artifact checksum failed: {name}")
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        self.session = ort.InferenceSession(
            str(path / "model.onnx"), sess_options=options, providers=["CPUExecutionProvider"]
        )
        self.tokenizer = Tokenizer.from_file(str(path / "tokenizer.json"))
        self.tokenizer.enable_padding()
        self.tokenizer.enable_truncation(max_length=256)
        self.version = self.manifest["model"] + "@" + self.manifest["revision"]

    @lru_cache(maxsize=512)
    def encode(self, texts):
        enc = self.tokenizer.encode_batch(list(texts))
        inputs = {
            "input_ids": np.array([e.ids for e in enc], dtype=np.int64),
            "attention_mask": np.array([e.attention_mask for e in enc], dtype=np.int64),
            "token_type_ids": np.array([e.type_ids for e in enc], dtype=np.int64),
        }
        out = self.session.run(None, {i.name: inputs[i.name] for i in self.session.get_inputs()})[0]
        mask = inputs["attention_mask"][:, :, None]
        vectors = (out * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1)
        return vectors / np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-12)

    def suggest(self, s, kind, text, zone=None, ownership=None):
        records = list(s["services" if kind == "service" else "facilities"].values())
        query = normalize(text)
        q = self.encode((query,))[0]
        candidates = []
        for r in records:
            terms = [r["name"]] + r.get("aliases", [])
            if kind == "facility" and r.get("directory_context"):
                terms.append(r["directory_context"]["name"])
            semantic = float(max(self.encode(tuple(normalize(t) for t in terms)) @ q))
            exact = query in [normalize(t) for t in terms]
            fuzzy = max(fuzz.ratio(query, normalize(t)) / 100 for t in terms)
            locality = not zone or r.get("zone") == zone
            type_match = not ownership or r.get("ownership") == ownership
            score = 1.0 if exact else 0.8 * semantic + 0.2 * fuzzy
            if kind == "facility" and (not locality or not type_match):
                score *= 0.7
            candidates.append(
                {
                    "id": r["id"],
                    "name": r["name"],
                    "score": round(score, 4),
                    "semantic": round(semantic, 4),
                    "exact_alias": exact,
                    "locality_match": locality,
                    "type_match": type_match,
                }
            )
        candidates.sort(key=lambda c: (-c["score"], c["id"]))
        best = candidates[0]["score"] if candidates else 0
        ambiguous = len(candidates) > 1 and best - candidates[1]["score"] < 0.05
        locality_ok = bool(candidates and candidates[0]["locality_match"])
        return {
            "kind": kind,
            "input_text": text,
            "normalized_text": query,
            "candidates": candidates[:3],
            "status": "NEEDS_REVIEW"
            if best >= get_settings().match_review_threshold and locality_ok
            else "NO_SUPPORTED_MATCH",
            "ambiguous": ambiguous,
            "model_version": self.version,
            "threshold": get_settings().match_review_threshold,
            "created_at": stamp(),
            "score_note": "Similarity is not a calibrated probability; human review is mandatory.",
        }


@lru_cache
def matcher():
    return Matcher()


def review(s, u, data):
    m = get(s, "matches", data["match_id"])
    require(
        m["actor"] == u["id"] or u["role"] == "planner",
        "ROLE_FORBIDDEN",
        "Review belongs to another operator",
        403,
    )
    candidate = data.get("candidate_id")
    decision = data["decision"]
    require(
        decision in ["ACCEPT", "CORRECT", "DECLINE"],
        "INVALID_REVIEW",
        "Choose accept, correct or decline",
        422,
    )
    if decision != "DECLINE":
        require(candidate is not None, "INVALID_REVIEW", "Select a canonical record", 422)
        get(s, "services" if m["kind"] == "service" else "facilities", candidate)
    r = add(
        s,
        "reviews",
        {
            **data,
            "kind": m["kind"],
            "input_text": m["input_text"],
            "candidates": m["candidates"],
            "model_version": m["model_version"],
            "actor": u["id"],
            "created_at": stamp(),
        },
    )
    if data.get("record_id"):
        if m["kind"] == "facility":
            planner(u)
            original = get(s, "facilities", data["record_id"])
            if decision != "DECLINE":
                original["canonical_id"] = candidate
                original["version"] += 1
                # Identity link only: never transfer requests, quotas, permissions or reservations.
        else:
            request = get(s, "requests", data["record_id"])
            operator(u, request["source_facility_id"])
            require(
                request["original_text"] == m["input_text"],
                "SERVICE_REVIEW_REQUIRED",
                "Match must use the original request description",
                422,
            )
            require(
                request["status"] in ["OPEN", "UNRESOLVED", "OUT_OF_SCOPE"],
                "INVALID_TRANSITION",
                "Cannot revise an accommodated request",
            )
            request["service_id"] = candidate if decision != "DECLINE" else None
            request["service_reviewed"] = decision != "DECLINE"
            request["review_id"] = r["id"]
            request["status"] = "OPEN" if request["suitable"] and decision != "DECLINE" else "UNRESOLVED"
            request["version"] += 1
    audit(s, u, "MATCH_REVIEW", r["id"], after=r)
    return r
