#!/usr/bin/env python3
"""
R06-T021 check.py
=================
Validates the prism exercise:
  - Copies the exercise to a temp dir, substituting the reference (example) solution
  - Runs: bin/validate_one_exercise exercises/practice/prism
  - Asserts the child exits zero
  - Asserts the test count equals the expected number of enabled cases
  - Records inputs, expected vs actual results, and tool versions

Exit codes:
  0  all assertions pass
  1  one or more assertions failed
  2  setup / invocation error
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Ensure Homebrew binaries (gawk, bats, bash 5+) are on PATH
os.environ["PATH"] = "/opt/homebrew/bin:" + os.environ.get("PATH", "")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EXERCISE_DIR = REPO_ROOT / "exercises" / "practice" / "prism"
CONFIG_JSON = EXERCISE_DIR / ".meta" / "config.json"
TESTS_TOML = EXERCISE_DIR / ".meta" / "tests.toml"
WORK_DIR = Path(__file__).resolve().parent

# Expected number of enabled (included) test cases.
# tests.toml has 14 entries, none with include = false → 14 enabled.
EXPECTED_ENABLED_CASES = 14

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def die(msg: str, code: int = 2) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)
    sys.exit(code)


def run(cmd, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


def tool_version(cmd: list[str]) -> str:
    r = run(cmd)
    return (r.stdout + r.stderr).strip().splitlines()[0] if (r.stdout + r.stderr).strip() else "(unavailable)"


def count_enabled_cases(toml_path: Path) -> int:
    """
    Count tests.toml entries that are effectively included.
    An entry is EXCLUDED only when it contains 'include = false'.
    """
    text = toml_path.read_text()
    # Split into sections by [uuid] headers
    sections = re.split(r'(?=^\[)', text, flags=re.MULTILINE)
    enabled = 0
    for section in sections:
        if not re.match(r'^\[[0-9a-f-]{36}\]', section):
            continue  # skip file header / comments
        if re.search(r'^\s*include\s*=\s*false', section, re.MULTILINE):
            continue
        enabled += 1
    return enabled


def count_bats_tests(bats_path: Path) -> int:
    """Count @test declarations in a .bats file."""
    text = bats_path.read_text()
    return len(re.findall(r'^@test\s+', text, re.MULTILINE))


def count_bats_output_tests(output: str) -> int:
    """Parse bats TAP output to count total tests run."""
    # bats TAP line: "1..N" at start
    m = re.search(r'^1\.\.(\d+)', output, re.MULTILINE)
    if m:
        return int(m.group(1))
    # fallback: count ok/not ok lines
    return len(re.findall(r'^(?:ok|not ok)\s+\d+', output, re.MULTILINE))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("R06-T021 prism exercise check")
    print("=" * 60)

    # 1. Verify exercise directory exists
    if not EXERCISE_DIR.is_dir():
        die(f"Exercise directory not found: {EXERCISE_DIR}")

    # 2. Read config.json to resolve file paths
    if not CONFIG_JSON.is_file():
        die(f"config.json not found: {CONFIG_JSON}")
    config = json.loads(CONFIG_JSON.read_text())
    solution_rel = config["files"]["solution"][0]   # e.g. "prism.awk"
    test_rel     = config["files"]["test"][0]        # e.g. "test-prism.bats"
    example_rel  = (config["files"].get("example") or config["files"].get("exemplar"))[0]
    # e.g. ".meta/example.awk"

    solution_src = EXERCISE_DIR / solution_rel
    test_src     = EXERCISE_DIR / test_rel
    example_src  = EXERCISE_DIR / example_rel

    for p in (solution_src, test_src, example_src):
        if not p.is_file():
            die(f"Required file missing: {p}")

    # 3. Count enabled cases from tests.toml
    if not TESTS_TOML.is_file():
        die(f"tests.toml not found: {TESTS_TOML}")
    enabled_in_toml = count_enabled_cases(TESTS_TOML)
    enabled_in_bats = count_bats_tests(test_src)
    print(f"\n[info] tests.toml: {enabled_in_toml} enabled cases")
    print(f"[info] test file:  {enabled_in_bats} @test blocks")

    # 4. Collect tool versions
    gawk_ver  = tool_version(["gawk", "--version"])
    bats_ver  = tool_version(["bats", "--version"])
    jq_ver    = tool_version(["jq", "--version"])
    py_ver    = tool_version([sys.executable, "--version"])
    print(f"\n[versions]")
    print(f"  gawk : {gawk_ver}")
    print(f"  bats : {bats_ver}")
    print(f"  jq   : {jq_ver}")
    print(f"  python: {py_ver}")

    # 5. Run validate_one_exercise via subprocess
    #    The script cd's into the exercise dir and uses mktemp internally;
    #    we just invoke it and capture output.
    validate_script = REPO_ROOT / "bin" / "validate_one_exercise"
    if not validate_script.is_file():
        die(f"validate_one_exercise not found: {validate_script}")

    print(f"\n[run] {validate_script} exercises/practice/prism")
    result = run(
        [str(validate_script), str(EXERCISE_DIR)],
        cwd=str(REPO_ROOT),
    )

    stdout = result.stdout
    stderr = result.stderr
    child_rc = result.returncode

    # 6. Record inputs / expected / actual
    record = {
        "tool_versions": {
            "gawk": gawk_ver,
            "bats": bats_ver,
            "jq": jq_ver,
            "python": py_ver,
        },
        "paths": {
            "exercise_dir": str(EXERCISE_DIR),
            "solution_stub": str(solution_src),
            "reference_solution": str(example_src),
            "test_file": str(test_src),
            "tests_toml": str(TESTS_TOML),
        },
        "enabled_cases": {
            "in_toml": enabled_in_toml,
            "in_bats_file": enabled_in_bats,
            "expected": EXPECTED_ENABLED_CASES,
        },
        "run": {
            "command": f"{validate_script} exercises/practice/prism",
            "returncode": child_rc,
            "stdout": stdout,
            "stderr": stderr,
        },
        "assertions": {},
    }

    tests_run = count_bats_output_tests(stdout)
    record["run"]["tests_counted"] = tests_run

    # 7. Assertions
    failures = []

    def assert_eq(name: str, expected, actual) -> None:
        ok = expected == actual
        record["assertions"][name] = {
            "expected": expected,
            "actual": actual,
            "pass": ok,
        }
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name}: expected={expected!r}, actual={actual!r}")
        if not ok:
            failures.append(name)

    print("\n[assertions]")
    assert_eq("child_returncode_is_zero", 0, child_rc)
    assert_eq("enabled_cases_in_toml",    EXPECTED_ENABLED_CASES, enabled_in_toml)
    assert_eq("bats_test_count",          EXPECTED_ENABLED_CASES, enabled_in_bats)
    assert_eq("tests_run_nonzero",        True, tests_run > 0)
    assert_eq("tests_run_count",          EXPECTED_ENABLED_CASES, tests_run)

    # 8. Write record
    record_path = WORK_DIR / "run_record.json"
    record_path.write_text(json.dumps(record, indent=2))
    print(f"\n[record] Written to {record_path}")

    # 9. Print bats output summary
    if stdout:
        print("\n[bats stdout]")
        print(stdout[-3000:] if len(stdout) > 3000 else stdout)
    if stderr:
        print("\n[bats stderr]")
        print(stderr[-1000:] if len(stderr) > 1000 else stderr)

    # 10. Final verdict
    print("\n" + "=" * 60)
    if failures:
        print(f"[FAIL] {len(failures)} assertion(s) failed: {failures}")
        sys.exit(1)
    else:
        print("[PASS] All assertions passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
