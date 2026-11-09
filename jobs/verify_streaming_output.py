"""Check Hadoop Streaming output totals against the cleaned ride count."""
import argparse
import csv
import json
from pathlib import Path


def verify(output, expected_pickups):
    output = Path(output)
    parts = sorted(output.glob("part-*"))
    if not (output / "_SUCCESS").is_file() or not parts:
        raise RuntimeError(f"No successful Hadoop output found under {output}")
    groups = pickups = members = 0
    for part in parts:
        with part.open(encoding="utf-8") as stream:
            for line in stream:
                fields = next(csv.reader([line.rstrip("\r\n\t")]))
                if len(fields) != 5:
                    raise ValueError(f"Expected 5 output fields in {part}: {fields!r}")
                groups += 1
                pickups += int(fields[2])
                members += int(fields[4])
    report = {
        "engine": "Hadoop Streaming 3.3.6",
        "execution_mode": "local",
        "output_groups": groups,
        "pickup_total": pickups,
        "member_total": members,
        "reducer_parts": len(parts),
        "expected_pickups": expected_pickups,
        "pickup_total_matches_clean_rides": pickups == expected_pickups,
    }
    if pickups != expected_pickups:
        raise AssertionError(f"pickup total {pickups} != expected {expected_pickups}")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-pickups", type=int, required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    report = verify(args.output, args.expected_pickups)
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
