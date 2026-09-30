"""A deterministic demo: two agents and a human; the kit decides what may leave.
No model and no network are needed — the agents are scripted, so every run is the same.
    python3 demo/run_demo.py
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from aak import Gate, Journal  # noqa: E402

W = pathlib.Path(tempfile.mkdtemp(prefix="aak-demo-"))
(W / "report.txt").write_text("intro\nERROR: unit mismatch\nok\nERROR: missing ref\nERROR: off-by-one\n")
(W / "deploy.log").write_text("build ok\ntests ok\nupload failed: 403\n")
(W / "dataset.csv").write_text("id,value\n" + "".join(f"{i},{i * 2}\n" for i in range(998)))

journal = Journal(W / "outcomes.jsonl")
# history: the builder twice said "done" when it was not
for i in (1, 2):
    journal.add("builder", "done", f"old release {i} is deployed", outcome="refuted",
                by="the release log showed a failure", at=f"2026-09-2{i}T10:00:00")
gate = Gate(journal)


def row(name, means, kind, status="verified"):
    return {"name": name, "means": means, "status": status, "kind": kind}


def say(agent, text, doc, turn):
    d = gate.submit(agent, text, doc, turn=turn)
    tag = "RELEASED" if d["released"] and not d["marked_unearned"] else (
        "RELEASED, MARKED UNEARNED" if d["released"] else "RETURNED")
    print(f"  [{agent}] {text}\n      -> {tag}" + ("" if not d["reasons"] else "  " + "; ".join(d["reasons"])))
    return d


print("ROUND 1\n")
print("1. The reviewer counts errors and lets the kit recount.")
say("reviewer", "The report has 3 errors.",
    {"rows": [row("errs", "report.txt has 3 ERROR lines", "measurement")], "claim": "errs",
     "traces": {"errs": {"kind": "count", "path": str(W / "report.txt"), "pattern": "ERROR", "equals": 3}}}, "r1")

print("\n2. The builder says 'done' on its own word — its record on 'done' is F.")
say("builder", "Deployment is done.",
    {"rows": [row("done", "the release is deployed", "done")], "claim": "done",
     "traces": {"done": {"kind": "self", "reason": "I ran the script"}}}, "b1")
print("   It attaches a log line that is not there:")
say("builder", "Deployment is done.",
    {"rows": [row("done", "the release is deployed", "done")], "claim": "done",
     "traces": {"done": {"kind": "file", "path": str(W / "deploy.log"), "contains": "deployed"}}}, "b1")
print("   It revises the ANSWER, not the record:")
say("builder", "Deployment is NOT done: the upload failed with 403.",
    {"rows": [row("failed", "deploy.log says upload failed: 403", "fact")], "claim": "failed",
     "traces": {"failed": {"kind": "file", "path": str(W / "deploy.log"), "contains": "upload failed: 403"}}}, "b1")

print("\n3. The human states a fact on their own word; no history yet, so it goes out as SELF,")
print("   and is registered OPEN in the journal.")
say("human", "The dataset has 1000 rows.",
    {"rows": [row("rows", "dataset.csv has 1000 rows", "measurement")], "claim": "rows",
     "traces": {"rows": {"kind": "self", "reason": "I remember exporting it"}}}, "h1")

print("\nLATER TRUTH\n")
n = sum(1 for _ in open(W / "dataset.csv")) - 1
open_claim = journal.find_open("human", "dataset.csv has 1000 rows")[0]
journal.settle(open_claim["id"], "refuted", f"recount: dataset.csv has {n} data rows")
print(f"  a recount finds {n} rows; the human's claim is settled REFUTED.")

print("\nROUND 2\n")
print("4. The same rule applies to the human: their word on measurements is now F.")
say("human", "The cleaned dataset has 998 rows.",
    {"rows": [row("rows2", "the cleaned dataset has 998 rows", "measurement")], "claim": "rows2",
     "traces": {"rows2": {"kind": "self", "reason": "trust me"}}}, "h2")
print("   Not a veto — with evidence it goes through:")
say("human", "The cleaned dataset has 998 rows.",
    {"rows": [row("rows2", "the cleaned dataset has 998 rows", "measurement")], "claim": "rows2",
     "traces": {"rows2": {"kind": "count", "path": str(W / "dataset.csv"), "pattern": r"^\d+,",
                                "regex": True, "equals": 998}}}, "h2")

print("\n5. An agent that never fixes its answer cannot stall the system: after 3 returns")
print("   its answer leaves, MARKED unearned, for a human to see.")
stub = {"rows": [row("x", "all tests pass", "done", status="unverified")], "claim": "x", "traces": {}}
for _ in range(4):
    say("stubborn", "All tests pass.", stub, "s1")

print("\nTRUST CUBE (last 5 settled | all time | open)\n")
for (agent, kind), c in sorted(journal.cube().items()):
    print(f"  {agent:9} {kind:12} {c['mark']}   window {c['window']}   all-time {c['all_time']}   open {c['open']}")
print(f"\nworkspace: {W}")
