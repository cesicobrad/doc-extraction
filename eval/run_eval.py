"""Score extractions against hand-written expected values.

    python eval/run_eval.py            # call Claude on every sample, then score
    python eval/run_eval.py --rescore  # score the outputs saved by the last run (no API calls)

Each key in eval/expected/<sample>.json is one check. Dotted keys reach into
nested fields ("issuer.name"); "line_items.<field>" compares that field across
all line items as an unordered list.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

from extractor import MODEL, extract_file  # noqa: E402

EXPECTED = ROOT / "eval" / "expected"
OUTPUTS = ROOT / "eval" / "outputs"
SAMPLES = ROOT / "samples"
PASS_THRESHOLD = 0.95
# Names and addresses pass if the expected text appears in the extracted value,
# so "Vrhovec Electrical" matches "Vrhovec Electrical s.p.".
CONTAINS_FIELDS = {"issuer.name", "recipient.name", "delivery_address"}


def norm(s) -> str:
    return re.sub(r"[^0-9a-z]", "", str(s).casefold())


def get(data: dict, key: str):
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
        return actual is None
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected) or None in actual:
            return False
        return all(same_number(a, b) for a, b in zip(sorted(expected), sorted(actual)))
    if isinstance(expected, (int, float)):
        return same_number(expected, actual)
    if actual is None:
        return False
    if key in CONTAINS_FIELDS:
        return norm(expected) in norm(actual)
    return norm(expected) == norm(actual)


def sample_for(name: str) -> Path:
    return next(SAMPLES.glob(f"{name}.*"))


def run_extractions(names: list[str]) -> None:
    OUTPUTS.mkdir(exist_ok=True)

    def one(name: str):
        result = extract_file(sample_for(name))
        (OUTPUTS / f"{name}.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
        print(f"  extracted {name}")

    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(one, names))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rescore", action="store_true", help="score saved outputs without calling the API")
    args = parser.parse_args()

    names = sorted(p.stem for p in EXPECTED.glob("*.json"))
    if not args.rescore:
        load_dotenv(ROOT / ".env")
        print(f"Extracting {len(names)} samples with {MODEL}...")
        run_extractions(names)

    total = passed = 0
    print()
    for name in names:
        expected = json.loads((EXPECTED / f"{name}.json").read_text(encoding="utf-8"))
        actual = json.loads((OUTPUTS / f"{name}.json").read_text(encoding="utf-8"))
        failures = []
        for key, want in expected.items():
            got = get(actual, key)
            if check(key, want, got):
                passed += 1
            else:
                failures.append(f"    {key}: expected {want!r}, got {got!r}")
            total += 1
        ok = len(expected) - len(failures)
        print(f"{name:<28} {ok:>2}/{len(expected)}")
        for line in failures:
            print(line)

    score = passed / total
    print(f"\nScore: {passed}/{total} fields correct ({score:.0%})")
    print("PASS" if score >= PASS_THRESHOLD else f"FAIL (threshold {PASS_THRESHOLD:.0%})")
    return 0 if score >= PASS_THRESHOLD else 1


if __name__ == "__main__":
    sys.exit(main())
