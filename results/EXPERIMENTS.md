# Optimisation experiments (A/B tests)

Two follow-up experiments run with the same harness and method as the main benchmark
(script + layout time, median of 20 samples per cell, Chromium 141 headless, 1× CPU),
each comparing the submitted app against a single-change variant. The variants were
throw-away builds and are not part of the repo; the change is described exactly so it
can be reproduced.

## 1. React: what `React.memo` on `TaskRow` is worth

Variant: `const TaskRow = memo(function TaskRow(...))` → `const TaskRow = function TaskRow(...)`.
Without `memo`, every state change re-renders all rows; React then diffs 1000 rows
even though only 50 changed.

| Scenario | With `memo` (submitted) | Without `memo` | Change |
|---|---:|---:|---:|
| Cold · render 1000 | 127.6 ms | 132.8 ms | +4% |
| Cold · update 50 of 1000 | 15.9 ms | 32.2 ms | **+102%** |
| Cold · delete 50 of 1000 | 11.4 ms | 35.3 ms | **+210%** |
| Warm · update 50 of 1000 | 7.7 ms | 15.5 ms | **+103%** |
| Warm · delete 50 of 1000 | 4.5 ms | 13.4 ms | **+196%** |

Memoising rows (plus stable `useCallback` handlers, so the memo is not defeated by new
function props) is what makes React competitive on updates and deletions.

## 2. Svelte: do whitespace text nodes slow it down?

Svelte keeps the whitespace between elements in a template as text nodes, so the Svelte
list has ~14,150 DOM nodes for 1000 tasks versus ~9,090 in React and Vue (Angular adds
two comment anchors per row for `*ngFor` / `*ngIf`, ~11,100 nodes). Variant: the same
templates with all inter-tag whitespace removed (11,001 nodes).

| Scenario | Default (submitted) | No whitespace | Change |
|---|---:|---:|---:|
| Cold · render 1000 | 197.7 ms | 198.3 ms | +0% |
| Cold · update 50 of 1000 | 10.8 ms | 11.6 ms | +7% |
| Cold · delete 50 of 1000 | 14.4 ms | 14.3 ms | −1% |
| Warm · render 1000 | 88.8 ms | 94.3 ms | +6% |

No meaningful difference (all within run-to-run noise). Svelte builds each row by cloning
a pre-parsed `<template>`, so the extra text nodes cost almost nothing — the readable,
indented markup was kept.
