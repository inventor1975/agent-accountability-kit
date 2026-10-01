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

## Many agents, no centre (`aak/p2p.py`)

The gate above is one judge. `aak/p2p.py` removes the centre: **every agent is its own
judge** — a ZTL judge node (`ztljudgenode`, vendored unchanged from ZTL: hash-chained memory,
reproducible verdict hash, Ed25519-signed attestations). Agents sign statements about facts
and send them to each other; messages arrive late, out of order or not at all, and agents go
offline. Nobody collects or counts.

- **The cube.** Each agent keeps its own trust in every signer, from *delayed truth*: when the
  true value of a fact comes out, every statement it holds on that fact is confirmed or
  refuted. Last 5 settled: any refuted → **F**, else any confirmed → **T**, else **Z**.
- **Forgiveness is not retroactive.** A statement is judged by its signer's record *around the
  time it was made*, not by today's mark (found by the stand: a liar who reformed had his
  old lies admitted by his new, clean mark).
- **Zero-trust admission.** Statements from T signers are verified atoms, from Z signers
  unverified, from F signers nothing. "The fact is true" is judged by ZTL as
  *at least two trusted supporters* (quorum 2, adjustable) **and** no statement against:
  an unverified contradiction keeps it OPEN, a missing message is simply absent.
- **Proof-of-fault.** An agent may publish a signed attestation of its verdict; any other
  agent re-computes it from the snapshot it carries. A mismatch is a signed proof: the
  forger is F at once, without waiting for truth.

The stand (`python3 demo/run_p2p.py`): 30 agents, a third of them lying (always, silent,
sleeper, reform, forged attestations, rare — 1 lie in 10), 40 rounds, delays up to 3 rounds,
10% of messages lost, 10% of agents offline each round, the truth of half the facts published
a round later. Judged: the facts whose truth is **never** published, by every honest agent.

| 3 seeds | false EARNED | right EARNED |
|---|---|---|
| cube on, quorum 2 | 0, 0, 0 | 1351, 1551, 1590 of 1460, 1660, 1760 |
| cube off (everyone trusted), quorum 2 | 0, 0, 0 | 648, 636, 658 |

Across a grid (liars 20% / 33% / 45%, sparse or dense observation, 10% or 30% loss and
offline, 3 seeds each) the cube with quorum 2 gave **0 false EARNED in all 12 cells**; with
quorum 1, up to 35 of 3872 at 45% liars and sparse observation — all of them a single trusted
"rare" liar heard alone.

**Where the flat count alone breaks** (the zones and alarm below close it in the tested range). Liars who **collude** — lying rarely, but on the *same* facts — defeat any
count of witnesses: at a third of colluders and sparse observation, 15 false EARNED of 4980 with
quorum 2, 1 with quorum 3. No voting scheme can tell a coalition that looks honest from the
truth; only more ground truth, or a trace the consumer checks **itself** (the gate above),
can. And safety has a price in coverage when evidence is scarce: with sparse observation and
30% loss, quorum 2 decides 8% of facts (quorum 1: 36%) — the rest stay honestly OPEN.

### Zones: seats by public randomness, a tree of triples, regrouping per fact

With many agents a flat count is not enough. Following the ZTL swarm work, every fact gets
**81 seats drawn by public randomness** (the fact's own hash: anyone can recompute them, nobody
can choose them), and the seats are **re-drawn for every fact**. A consumer folds the seats
three by three, **2 of 3 at every level** (the triple's table is computed by ZTL itself), an
empty or untrusted seat counting as Z; known liars (F at that time) are unseated. An **alarm**
asks the root's side to hold 2/3 of the trusted seats that spoke. The default, `verdict_either`:
the flat rule (any trusted contradiction blocks) **or** the tree with the alarm — decided when one
of them decides and neither opposes.

The stand (`python3 demo/run_tree.py`): 243 agents, 81 seats, 30 rounds, 30 sampled honest
judges, delays up to 3 rounds, 10% loss and offline, 3 seeds per cell. Two kinds of liars: a
random third or 45% of all agents, and an **adaptive attacker** who corrupts 30 or 50 members
of the committee it can see (fixed seats). Four strategies each (always, rare, sleeper,
coalition = all lie on the same facts).

| | false EARNED | right EARNED (range over cells) |
|---|---|---|
| default (either), regrouping per fact | **0 in all 16 cells** | 37–98% |
| flat rule alone, regrouping | 0 | 9–92% |
| tree alone, **no** regrouping, attacker holds 50 of the committee, coalition | **74** (78 without unseating) | — |
| default, **no** regrouping, same attack | **4** | — |

Regrouping is what defeats an attacker who can see the committee; without it the tree can be
bought. The price of regrouping in this model: trust builds more slowly (each agent is seated in
about a third of the facts), so coverage is lower than with a fixed committee that nobody attacks.

**The tree's own bound, proved.** In Lean, on the empty axiom list (ZTL `lean/ZMajority.lean`,
commit a77727b): a tree of triples of depth d says "false" only if at least 2^d of its seats
lie, empty seats never help a lie, and 2^d is enough — there is a placement where 2^d liars,
every other seat honest, carry the verdict. At depth 4 that is **16 of 81 seats, about 20%**.
So the tree alone is *weaker* than a flat majority against an attacker who chooses where to sit;
what protects it is that nobody chooses — seats by public randomness, re-drawn per fact — and
the alarm. That part is measured by simulation above, not proved. The same file proves that
the triple's table is the ZTL judge's *disposition* of `(a&b)|(a&c)|(b&c)` (T exactly when
EARNED, F exactly when REFUTED), not the formula's value.

### Where it cracks and where it has reserve (stress map, 30 Sept)

Default rule now: `verdict_guarded` — the zones rule above, plus two rules taken from the ZTL
swarm work: an **alarm** (if more than 20% of the live seat triples hold both a trusted "true"
and a trusted "false", a coalition may be at work, and only the cautious flat rule may decide)
and a **minimum of 12 trusted voices** over a fact's seats. The alarm threshold was chosen on
seeds 0–4; the whole sweep was then re-run twice on fresh seeds (5–9, then 10–14).

Final check, seeds 10–14: 825 runs, 836,640 judgements, **1 false EARNED** — with only 27
seats and 45% liars (a pool that small can be captured: a coalition holding 45% of all
agents holds half of 27 random seats 30% of the time; of 81 seats, 18%; of 243, 6%).
With 81 or 243 seats: 0. Liars were always, rare, sleeper, coalition (all lie on the same facts)
and **cycle** (wash, earn trust, betray together — the attack that broke the swarm's
distributed newspaper).

| axis (others at base: liars 1/3, loss 10%, truth on 50% of facts, 81 seats) | decided correctly |
|---|---|
| liars 10% / 33% / 45% / 60% | 89.3% / 78.4% / 66.9% / 58.5% — **0 false even at 60%** |
| cycle attack, betray rate 0.05–0.5, liars up to 45% | 94.5–99.8% |
| message loss and offline 0% / 10% / 20% / 30% / 40% | 95.4% / 78.4% / 55.5% / 32.1% / 8.2% |
| share of facts whose truth comes out later 50% / 20% / 5% | 78.4% / 50.9% / 21.2% |
| seat fill (checkers who actually look) 90% / 70% / 50% / 30% | 78.4% / 57.2% / 47.2% / 11.4% |

**Full validation of the final rule** (then run on everything above again, and more):
3,550 runs, 3,775,500 judgements — the axes on seeds 0–9 (0 false EARNED of 1,640,010), a grid
of combinations — liars 20–55% × loss 0–30% × truth on 20% or 50% of facts, 10 seeds each
(0 of 1,865,430), and an attacker who corrupts 30, 50 or 70 members of the committee it can see:
**with regrouping 0 false EARNED at every budget; without it, 16 at 50 and 753 (1.65%) at 70.**
Re-drawing the checkers for every fact is load-bearing — do not turn it off.

**Reserve:** safety — liars up to 60%, colluding and cycling. **Cracks:** liveness, not
safety — the network (≥ 20% loss), scarce ground truth (≤ 20% of facts), sparse checkers, and
pools as small as 27. When evidence runs short the system stops deciding; it does not lie.

## Limits, said plainly

- The kit judges the **ground an agent lays**, not the meaning of its prose. A claim made in
  words and left off the ground is not seen; only numbers and commit hashes are checked for
  coverage mechanically.
- Traces prove what they check (a line, a count, a commit), not intent.
- A young journal shows a direction, not a rate: a record built from remembered errors
  over-weights them until correct claims are logged too.

## Where it comes from

Built in the ZTL project (https://github.com/inventor1975/ZTL). It generalises gates that ran
in that project on an AI assistant's own answers (29 Sept – 1 Oct 2026): they refused answers
whose premises failed their traces, including a wrong count and a mis-quoted file, before the
answers reached the human. They were then retired by the project's curator: of 295 checked
drafts, 87 were returned, mostly for bookkeeping (a number missing from the record), and the
real catches were few — they caught slips, not losses of meaning. The outward gates (push,
publish, deploy) stay. The ZTL kernel is vendored unchanged in `aak/core/` (see VENDORED.md).

## License and disclosure

Dual-licensed MIT OR Apache-2.0. Author: Vitaly Reznik. Designed and written with an AI assistant,
Claude (Anthropic, model Claude Opus 5.5), under the author's direction.
