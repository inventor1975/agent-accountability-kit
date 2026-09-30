# Agent Accountability Kit

An answer from an AI agent — or a human — leaves only when a zero-trust judge says it is **earned**.

Most oversight of AI agents checks *what tool is called*. This kit checks *what is claimed*,
and keeps a record of how each agent's claims turned out. It is small, local and deterministic:
no model and no network are needed to run it.

## How it works

1. **Lay.** The agent lays its answer out as premises and a conclusion, in ZFL (the table
   language of the ZTL judge). Each premise says what it rests on — a *trace*.
2. **Check.** The kit checks every trace itself: the file contains the line, the recount
   gives the number, the commit exists, the URL says so. An agent may *propose* that a premise
   is verified; only a trace that holds here makes it so. A failed trace sends the premise back
   to *unverified*.
3. **Judge.** The ZTL kernel (three-valued zero-trust logic, machine-checked in Lean upstream)
   gives the verdict. The gate releases the answer only if the conclusion is **EARNED** and every
   number and commit hash the answer states stands in its ground. Otherwise the answer goes back
   to the agent with the reasons — at most 3 times; then it leaves, **marked unearned**, so a
   human sees it. A gate that can silence an agent forever is not a safety feature.
4. **Learn.** An append-only *outcome journal* records what each claim turned out to be. A
   *trust cube* per (agent, kind of claim) — the last 5 settled claims: any refuted → **F**,
   confirmed and clean → **T**, nothing settled → **Z** — takes an agent's *bare word* away
   where its record is F. Five clean claims in a row forgive an F; the all-time tally stays.
   Humans are in the journal too, for their **factual** claims — never as a veto on their
   decisions: with evidence, their word goes through like anyone's.

## Run the demo

```
python3 demo/run_demo.py
python3 tests/test_kit.py
```

What the demo shows (abridged; the full output is deterministic):

```
[builder] Deployment is done.
    -> RETURNED  not earned (Z OPEN); unverified: done — SELF refused: builder's record on 'done' claims is F
[builder] Deployment is done.
    -> RETURNED  not earned (Z OPEN); unverified: done — file deploy.log lacks 'deployed'
[builder] Deployment is NOT done: the upload failed with 403.
    -> RELEASED
...
a recount finds 998 rows; the human's claim is settled REFUTED.
[human] The cleaned dataset has 998 rows.
    -> RETURNED  not earned (Z OPEN); unverified: rows2 — SELF refused: human's record on 'measurement' claims is F
[human] The cleaned dataset has 998 rows.        (with a recount as the trace)
    -> RELEASED
```

## Use it

```python
from aak import Gate, Journal
gate = Gate(Journal("outcomes.jsonl"))
decision = gate.submit("builder", "Deployment is NOT done: the upload failed with 403.", {
    "rows":   [{"name": "failed", "means": "deploy.log says upload failed: 403", "status": "verified", "kind": "fact"}],
    "claim":  "failed",
    "traces": {"failed": {"kind": "file", "path": "deploy.log", "contains": "upload failed: 403"}},
})
decision["released"], decision["reasons"]
```

Trace kinds: `file(path[, contains])` · `count(path, pattern[, regex], equals)` ·
`url(url[, contains])` · `commit(repo, rev)` · `self(reason)` (the agent's own word — counted,
shown, and refused where its record is F; kind `evident` is exempt, for what is true by the very
act, like "doubting is thinking").

## Limits, said plainly

- The kit judges the **ground an agent lays**, not the meaning of its prose. A claim made in
  words and left off the ground is not seen; only numbers and commit hashes are checked for
  coverage mechanically.
- Traces prove what they check (a line, a count, a commit), not intent.
- A young journal shows a direction, not a rate: a record built from remembered errors
  over-weights them until correct claims are logged too.

## Where it comes from

Built in the ZTL project (https://github.com/inventor1975/ZTL). It generalises gates that run
daily in that project on an AI assistant's own answers: in its first days they refused answers
whose premises failed their traces, including a wrong count and a mis-quoted file, before the
answers reached the human. The ZTL kernel is vendored unchanged in `aak/core/` (see VENDORED.md).

## License and disclosure

Dual-licensed MIT OR Apache-2.0. Author: Vitaly Reznik. Designed and written with an AI assistant,
Claude (Anthropic, model Claude Opus 5.5), under the author's direction.
