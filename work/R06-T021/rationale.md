# UUID Rationale — prism exercise (R06-T021)

## Context

The `tests.toml` file for the **prism** exercise contains **14 canonical cases**
and **0 explicit exclusions** (`include = false`).  All 14 entries carry only
`description` (and no `include` key), which per the TOML contract means
`include = true` for every entry.

The test file `test-prism.bats` reflects this: it contains exactly 14 `@test`
blocks.  The first block ("zero prisms") has its `skip` directive commented out
so it runs for the learner immediately; the remaining 13 blocks have an active
`skip` that the learner uncomments one at a time.  When the validator runs with
`BATS_RUN_SKIPPED=true`, **all 14 tests execute and must pass**.

---

## UUID: ec65d3b3-f7bf-4015-8156-0609c141c4c4 — "zero prisms"

**Test input / expected output**

```
start: x=0, y=0, angle=0
prisms: (none)
expected sequence: []  →  empty string
```

**Generated BATS block**

```bash
@test "zero prisms" {
    # [[ $BATS_RUN_SKIPPED == "true" ]] || skip   ← skip commented out (first test)
    run gawk -f prism.awk <<EOF
0 0 0
EOF
    assert_success
    assert_output ""
}
```

**AWK behaviour**

The AWK `END` rule is entered with `NR == 1` (only the start line was read).
The `prisms` array is empty, so the `for (id in prisms)` loop body never
executes, `found` stays 0, and the `do … while (found == 1)` loop exits
immediately.  The `if (count)` guard is false, so nothing is printed and
`gawk` exits 0.  `assert_output ""` therefore matches.

**Rationale**

This case is **fully supported** by both AWK and the reference implementation.
It is included (`include` key absent ≡ `true`) and is the **first (active) test**
that every learner sees.  No exclusion is warranted; no change needed.

---

## UUID: ec0ca17c-0c5f-44fb-89ba-b76395bdaf1c — "one prism one hit"

**Test input / expected output**

```
start: x=0, y=0, angle=0
prisms: id=1, x=10, y=0, angle=0
expected sequence: [1]  →  "1"
```

**Generated BATS block**

```bash
@test "one prism one hit" {
    [[ $BATS_RUN_SKIPPED == "true" ]] || skip
    run gawk -f prism.awk <<EOF
0 0 0
1 10 0 0
EOF
    assert_success
    assert_output "1"
}
```

**AWK behaviour**

The beam starts at (0, 0) travelling at 0° (along the positive x-axis).
In the `END` rule:

```
dx = 10 - 0 = 10;  dy = 0 - 0 = 0;  r = 10
hx = |cos(0°) × 10 - 10| = |10 - 10| = 0  < 0.1  ✓
hy = |sin(0°) × 10 - 0|  = |0  - 0|  = 0  < 0.1  ✓
```

Prism 1 is a hit, `out[0] = 1`.  After refraction, angle stays 0° and position
moves to (10, 0).  On the next iteration the only prism is at the current
position, so `continue` skips it and `found` remains 0.  Output: `"1"`.

**Rationale**

This case exercises the fundamental single-hit path and is **fully supported**.
It is included and **correctly skipped for the learner** (second test); the
validator runs it via `BATS_RUN_SKIPPED=true`.  No exclusion is warranted; no
change needed.

---

## UUID: 0db955f2-0a27-4c82-ba67-197bd6202069 — "one prism zero hits"

**Test input / expected output**

```
start: x=0, y=0, angle=0
prisms: id=1, x=-10, y=0, angle=0
expected sequence: []  →  empty string
```

**Generated BATS block**

```bash
@test "one prism zero hits" {
    [[ $BATS_RUN_SKIPPED == "true" ]] || skip
    run gawk -f prism.awk <<EOF
0 0 0
1 -10 0 0
EOF
    assert_success
    assert_output ""
}
```

**AWK behaviour**

The beam travels at 0° (positive x-direction) from origin.  The prism is
at x = −10, behind the start:

```
dx = -10 - 0 = -10;  dy = 0 - 0 = 0;  r = 10
hx = |cos(0°) × 10 - (-10)| = |10 + 10| = 20  ≥ 0.1  ✗
```

The directional check fails because `cos(0°) × r` projects the ray forward
(+x) but the prism is in the −x direction.  The 0.1-unit proximity threshold
is not satisfied, so `found` stays 0 and nothing is printed.  Output: `""`.

**Rationale**

This case verifies that **behind-origin prisms are correctly rejected**.  The
AWK proximity check (`hx < 0.1 && hy < 0.1`) naturally handles this because
it compares `cos(a)*r` and `sin(a)*r` against the actual dx/dy; a backward
prism produces a large residual.  The case is **fully supported**, correctly
included, and passes against the reference implementation.  No exclusion is
warranted; no change needed.

---

## Counts (before / after)

| Metric | Before | After |
|--------|--------|-------|
| `tests.toml` entries | 14 | 14 |
| `include = false` entries | 0 | 0 |
| Enabled entries | 14 | 14 |
| `@test` blocks in BATS | 14 | 14 |
| Tests passing (reference) | 14 | 14 |

No `include` values were changed.  All 14 cases pass against
`.meta/example.awk`.
