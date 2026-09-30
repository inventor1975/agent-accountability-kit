"""Stand for the kit.  python3 tests/test_kit.py  ->  KIT GREEN"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from aak import Gate, Journal, judge  # noqa: E402

W = pathlib.Path(tempfile.mkdtemp())
(W / "f.txt").write_text("a\nERROR x\nERROR y\n")
OK = FAIL = 0


def check(name, got, want):
    global OK, FAIL
    if got == want:
        OK += 1; print("  OK  ", name)
    else:
        FAIL += 1; print("  FAIL", name, "got", got, "want", want)


def doc(trace, kind="fact", status="verified"):
    return {"rows": [{"name": "p", "means": "p holds", "status": status, "kind": kind}], "claim": "p",
            "traces": {"p": trace} if trace else {}}


print("traces are checked by the kit, not taken on the word")
check("a file that says so -> EARNED", judge(doc({"kind": "file", "path": str(W / "f.txt"), "contains": "ERROR x"}))["disposition"], "EARNED")
check("a file that does not -> not earned", judge(doc({"kind": "file", "path": str(W / "f.txt"), "contains": "OK"}))["disposition"] == "EARNED", False)
check("the kit recounts", judge(doc({"kind": "count", "path": str(W / "f.txt"), "pattern": "ERROR", "equals": 2}))["disposition"], "EARNED")
check("a wrong count -> not earned", judge(doc({"kind": "count", "path": str(W / "f.txt"), "pattern": "ERROR", "equals": 3}))["disposition"] == "EARNED", False)
check("no trace -> not earned", judge(doc(None))["disposition"] == "EARNED", False)

print("the journal takes an agent's bare word away where its record is F")
j = Journal(W / "o.jsonl")
j.add("a", "done", "old", outcome="refuted", by="log")
self_t = {"kind": "self", "reason": "my word"}
check("SELF on an F kind is refused", judge(doc(self_t, "done"), agent="a", journal=j)["disposition"] == "EARNED", False)
check("'evident' is exempt", judge(doc(self_t, "evident"), agent="a", journal=j)["disposition"], "EARNED")
check("SELF on a kind with no history stands", judge(doc(self_t, "fact"), agent="a", journal=j)["disposition"], "EARNED")
check("...and is registered OPEN", bool(j.find_open("a", "p holds")), True)
judge(doc(self_t, "fact"), agent="a", journal=j)
check("...not twice", len(j.find_open("a", "p holds")), 1)
for i in range(5):
    j.add("a", "done", f"c{i}", outcome="confirmed", by="log", at=f"2099-01-0{i + 1}T00:00:00")
check("5 clean after an F forgive it", j.mark("a", "done"), "T")
check("the all-time tally remembers", j.cube()[("a", "done")]["all_time"], (5, 1))

print("the gate")
g = Gate(Journal(W / "g.jsonl"))
ev = {"kind": "file", "path": str(W / "f.txt"), "contains": "ERROR x"}
check("earned and covered -> released", g.submit("b", "done", doc(ev))["released"], True)
check("a number not on the ground -> returned", g.submit("b", "there are 7", doc(ev), turn="n")["released"], False)
d = [g.submit("c", "all good", doc(None), turn="t") for _ in range(4)]
check("returns at most 3 times, then released MARKED", [(x["released"], x["marked_unearned"]) for x in d],
      [(False, False)] * 3 + [(True, True)])

print(f"\nKIT {'GREEN' if not FAIL else 'RED'}: {OK} OK, {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
