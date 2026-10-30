"""Re-verify the Python practice bank by running it in the isolated runner.  Usage (from backend/):

    python -m tools.verify_python_bank            # check only
    python -m tools.verify_python_bank --write    # check, then refresh content/verified.json (only if everything passes)
"""

from __future__ import annotations

import sys

from app.services.python_practice import bank, verify
from app.services.python_practice.sandbox import runner


def main(argv: list[str]) -> int:
    caps = runner.capabilities()
    if not caps["available"]:
        print(f"The code runner is unavailable, so execution cannot be verified: {caps['reason']}")
        return 2
    result = verify.verify_all(write="--write" in argv)
    print(f"Executed: {result['checked']}")
    for line in result["failures"]:
        print("  FAIL", line)
    valid, rejected = bank.build_valid_seed_bank()
    print(f"Seeds accepted by the validation gate: {len(valid)}; rejected: {len(rejected)}")
    for r in rejected[:40]:
        print("  REJECTED", r["question_id"], r["statement"], "->", "; ".join(r["problems"])[:200])
    if result["written"]:
        print(f"Wrote {result['manifest_entries']} entries to content/verified.json")
    return 1 if result["failures"] or rejected else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
