"""Small held-out matching evaluation. No clinical quality claims."""

from pathlib import Path
import sys
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.mvp.matching import matcher  # noqa: E402
from app.mvp.seed import make_seed  # noqa: E402
from app.config import get_settings  # noqa: E402


def evaluate():
    labels = json.loads(
        (ROOT.parent / "data/evaluation/matching_labels.json").read_text(encoding="utf-8-sig")
    )
    state = make_seed()
    model = matcher()

    def score(row):
        result = model.suggest(state, row["kind"], row["text"], row.get("zone"))
        candidate = result["candidates"][0]
        return {
            **row,
            "top_id": candidate["id"],
            "score": candidate["score"],
            "exact_alias": candidate["exact_alias"],
            "locality_match": candidate["locality_match"],
            "model_status": result["status"],
            "model_ambiguous": result["ambiguous"],
        }

    dev = [score(r) for r in labels if r["split"] == "development"]
    thresholds = [round(0.35 + i * 0.01, 2) for i in range(51)]
    threshold = max(thresholds, key=lambda t: (sum((r["score"] >= t) == bool(r["expected"]) for r in dev), t))
    test = [score(r) for r in labels if r["split"] == "evaluation"]
    for r in test:
        r["suggested"] = r["score"] >= threshold and r["locality_match"] and not r["model_ambiguous"]
        r["correct_candidate"] = r["expected"] is not None and r["top_id"] == r["expected"]
    supported = [r for r in test if r["expected"]]
    suggested = [r for r in test if r["suggested"]]
    unsupported = [r for r in test if not r["expected"]]
    result = {
        "model": model.version,
        "threshold_selected_on_development": threshold,
        "configured_threshold": get_settings().match_review_threshold,
        "development_size": len(dev),
        "evaluation_size": len(test),
        "candidate_retrieval_success": sum(r["correct_candidate"] for r in supported) / len(supported),
        "exact_alias_retrieval_success": sum(r["exact_alias"] and r["correct_candidate"] for r in supported)
        / len(supported),
        "suggestion_precision": sum(r["correct_candidate"] for r in suggested) / len(suggested)
        if suggested
        else None,
        "false_match_rate": sum(r["suggested"] for r in unsupported) / len(unsupported),
        "abstention_frequency": sum(not r["suggested"] for r in test) / len(test),
        "manual_review_required": len(test),
        "limitations": [
            "Small synthetic labelled sample; not a population estimate",
            "No model suggestion automatically accepted",
            "Review decisions require a human; suggestion precision is not human-review accuracy",
        ],
        "development": dev,
        "evaluation": test,
    }
    dest = ROOT.parent / "outputs"
    dest.mkdir(exist_ok=True)
    (dest / "matching-results.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({k: v for k, v in result.items() if k not in ["development", "evaluation"]}, indent=2))
    return result


if __name__ == "__main__":
    evaluate()
