"""Score extractions against hand-written expected values.

    python eval/run_eval.py                              # call Claude on every sample, then score
    python eval/run_eval.py --model claude-haiku-5-5     # same, with another model
    python eval/run_eval.py --rescore                    # score saved outputs (no API calls)
    python eval/run_eval.py --compare                    # table of all saved model runs

Each key in eval/expected/<sample>.json is one check. Dotted keys reach into
nested fields ("issuer.name"); "line_items.<field>" compares that field across
all line items as an unordered list; "_arithmetic_flagged" checks whether
extractor.arithmetic_checks finds a problem in the extracted figures.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

from extractor import MODEL, Extraction, arithmetic_checks, content_from_file, extract_response  # noqa: E402

EXPECTED = ROOT / "eval" / "expected"
OUTPUTS = ROOT / "eval" / "outputs"
SAMPLES = ROOT / "samples"
PASS_THRESHOLD = 0.95
# Names and addresses pass if the expected text appears in the extracted value,
# so "Vrhovec Electrical" matches "Vrhovec Electrical s.p.".
CONTAINS_FIELDS = {"issuer.name", "recipient.name", "delivery_address"}
# USD per million input / output tokens (standard API rates, prompts under 100K tokens).
PRICES = {
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
}


def norm(s) -> str:
    return re.sub(r"[^0-9a-z]", "", str(s).casefold())


def get(data: dict, key: str):
    if key == "_arithmetic_flagged":
        return bool(arithmetic_checks(Extraction.model_validate(data)))
    if key.startswith("line_items."):
        field = key.split(".", 1)[1]
        return [item.get(field) for item in data.get("line_items", [])]
    for part in key.split("."):
        data = data.get(part) if isinstance(data, dict) else None
    return data


def same_number(a, b) -> bool:
    return a is not None and b is not None and abs(float(a) - float(b)) <= 0.01


def check(key: str, expected, actual) -> bool:
    if expected is None:
        return actual in (None, "")
    if isinstance(expected, bool):
        return actual is expected
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected) or None in actual:
            return False
        return all(same_number(a, b) for a, b in zip(sorted(expected), sorted(actual)))
    if isinstance(expected, (int, float)):
        return same_number(expected, actual)
    if not actual:
        return False
    if key in CONTAINS_FIELDS:
        return norm(expected) in norm(actual)
    return norm(expected) == norm(actual)


def score(expected: dict, actual: dict) -> list[str]:
    """Return one failure message per check that does not pass."""
    failures = []
    for key, want in expected.items():
        got = get(actual, key)
        if not check(key, want, got):
            failures.append(f"{key}: expected {want!r}, got {got!r}")
    return failures


def sample_for(name: str) -> Path:
    return next(SAMPLES.glob(f"{name}.*"))


def run_extractions(names: list[str], model: str, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    stats = {}

    def one(name: str):
        path = sample_for(name)
        start = time.perf_counter()
        response = extract_response(content_from_file(path.name, path.read_bytes()), model=model)
        seconds = time.perf_counter() - start
        (out / f"{name}.json").write_text(response.parsed_output.model_dump_json(indent=2), encoding="utf-8")
        stats[name] = {"seconds": round(seconds, 1), "input_tokens": response.usage.input_tokens,
                       "output_tokens": response.usage.output_tokens}
        print(f"  extracted {name} ({seconds:.1f}s)")

    # Sequential, so the timings reflect a single request rather than parallel load.
    for name in names:
        one(name)
    (out / "_run.json").write_text(json.dumps({"model": model, "documents": stats}, indent=2), encoding="utf-8")


def run_summary(model: str, out: Path, names: list[str]) -> dict:
    passed = total = 0
    for name in names:
        expected = json.loads((EXPECTED / f"{name}.json").read_text(encoding="utf-8"))
        actual = json.loads((out / f"{name}.json").read_text(encoding="utf-8"))
        total += len(expected)
        passed += len(expected) - len(score(expected, actual))
    summary = {"model": model, "passed": passed, "total": total}
    run_file = out / "_run.json"
    if run_file.exists():
        docs = json.loads(run_file.read_text(encoding="utf-8"))["documents"].values()
        price_in, price_out = PRICES.get(model, (0, 0))
        summary["avg_seconds"] = sum(d["seconds"] for d in docs) / len(docs)
        summary["avg_cost"] = sum(
            d["input_tokens"] * price_in / 1e6 + d["output_tokens"] * price_out / 1e6 for d in docs
        ) / len(docs)
    return summary


def compare(names: list[str]) -> None:
    print(f"{'Model':<20} {'Accuracy':>16} {'Avg time':>10} {'Cost/doc':>10}")
    for out in sorted(p for p in OUTPUTS.iterdir() if p.is_dir()):
        s = run_summary(out.name, out, names)
        acc = f"{s['passed']}/{s['total']} ({s['passed'] / s['total']:.0%})"
        t = f"{s['avg_seconds']:.1f}s" if "avg_seconds" in s else "-"
        c = f"${s['avg_cost']:.4f}" if "avg_cost" in s else "-"
        print(f"{out.name:<20} {acc:>16} {t:>10} {c:>10}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=MODEL, help=f"model to evaluate (default {MODEL}, or EXTRACTION_MODEL)")
    parser.add_argument("--rescore", action="store_true", help="score saved outputs without calling the API")
    parser.add_argument("--compare", action="store_true", help="summarise every saved model run")
    args = parser.parse_args()

    names = sorted(p.stem for p in EXPECTED.glob("*.json"))
    if args.compare:
        compare(names)
        return 0

    out = OUTPUTS / args.model
    if not args.rescore:
        load_dotenv(ROOT / ".env")
        print(f"Extracting {len(names)} samples with {args.model}...")
        run_extractions(names, args.model, out)

    total = passed = 0
    print(f"\nModel: {args.model}")
    for name in names:
        expected = json.loads((EXPECTED / f"{name}.json").read_text(encoding="utf-8"))
        actual = json.loads((out / f"{name}.json").read_text(encoding="utf-8"))
        failures = score(expected, actual)
        total += len(expected)
        passed += len(expected) - len(failures)
        print(f"{name:<38} {len(expected) - len(failures):>2}/{len(expected)}")
        for line in failures:
            print(f"    {line}")

    result = passed / total
    print(f"\nScore: {passed}/{total} fields correct ({result:.0%})")
    print("PASS" if result >= PASS_THRESHOLD else f"FAIL (threshold {PASS_THRESHOLD:.0%})")
    return 0 if result >= PASS_THRESHOLD else 1


if __name__ == "__main__":
    sys.exit(main())
