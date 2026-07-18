"""Run the same bond scenario in Python and Java and print a comparison table."""

from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

from bond_pricing import BondSpec, duration_convexity, price_bond_dirty, yield_to_maturity_from_price


ROOT = Path(__file__).resolve().parent
JAVA_ROOT = ROOT / "java-version"
JAVA_SOURCE = JAVA_ROOT / "src" / "main" / "java"
def _compile_java(output_dir: Path) -> None:
    sources = [str(path) for path in JAVA_SOURCE.rglob("*.java")]
    subprocess.run(["javac", "-encoding", "UTF-8", "-d", str(output_dir), *sources], check=True)


def _java_results() -> dict[str, float]:
    with tempfile.TemporaryDirectory(prefix="bond-java-") as temporary_dir:
        classes = Path(temporary_dir)
        _compile_java(classes)
        completed = subprocess.run(
            ["java", "-cp", str(classes), "com.example.bondpricing.Main"],
            check=True,
            capture_output=True,
            text=True,
        )
    labels = {
        "Dirty price": "price",
        "Implied YTM": "ytm_percent",
        "Macaulay duration": "macaulay_duration",
        "Modified duration": "modified_duration",
        "Convexity": "convexity",
        "DV01": "dv01",
    }
    results: dict[str, float] = {}
    for line in completed.stdout.splitlines():
        for label, key in labels.items():
            if line.startswith(label):
                number = re.search(r"([-+]?\d[\d,.]*)%?\s*$", line)
                if number:
                    results[key] = float(number.group(1).replace(",", ""))
    return results


def main() -> None:
    spec = BondSpec(face_value=10_000, coupon_rate=0.035, maturity_years=3, coupon_frequency=2)
    input_ytm = 0.038
    price = price_bond_dirty(spec, input_ytm)
    risk = duration_convexity(spec, input_ytm)
    python_results = {
        "price": price,
        "ytm_percent": yield_to_maturity_from_price(spec, price) * 100,
        **{key: risk[key] for key in ("macaulay_duration", "modified_duration", "convexity", "dv01")},
    }
    java_results = _java_results()

    print("\nPython vs Java bond calculation")
    print("=" * 78)
    print(f"{'Metric':<22} {'Python':>16} {'Java':>16} {'Abs. difference':>18}")
    print("-" * 78)
    labels = {
        "price": "Bond price",
        "ytm_percent": "Implied YTM (%)",
        "macaulay_duration": "Macaulay duration",
        "modified_duration": "Modified duration",
        "convexity": "Convexity",
        "dv01": "DV01",
    }
    for key, label in labels.items():
        python_value = python_results[key]
        java_value = java_results[key]
        print(f"{label:<22} {python_value:>16.8f} {java_value:>16.8f} {abs(python_value-java_value):>18.10f}")
    print("-" * 78)
    print("Result: MATCH" if all(abs(python_results[k] - java_results[k]) < 1e-6 for k in labels) else "Result: DIFFERENCE FOUND")


if __name__ == "__main__":
    main()
