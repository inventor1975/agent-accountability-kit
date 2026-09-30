"""Stand for aak/p2p.py: every promise in its header is a check here."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "demo"))
from aak.p2p import Peer  # noqa: E402

OK = FAIL = 0


def check(name, got, want):
    global OK, FAIL
    good = got == want
    OK += good
    FAIL += not good
    print(("  OK   " if good else "  FAIL ") + name + ("" if good else f"   got {got!r}, want {want!r}"))


def trusted(consumer, signer, rnd=0):
    """Make `signer` T at `consumer` around round `rnd`: one confirmed statement then."""
    f = f"seed-{rnd}-{signer.pid}"
    consumer.truth(f, True)
    consumer.receive(signer.statement(f, True, rnd))


print("p2p — admission and the zero-trust verdict")
a, b, c, d = Peer("a"), Peer("b", quorum=1), Peer("c"), Peer("d")
b.receive(a.statement("f1", True, 0))
check("a statement from an unknown (Z) signer is not EARNED", b.verdict("f1"), (None, "OPEN"))
trusted(b, a)
check("a trusted signer's statement is EARNED", b.verdict("f1"), (True, "EARNED"))
b.receive(c.statement("f1", False, 0))
check("an unverified contradiction keeps it OPEN", b.verdict("f1"), (None, "OPEN"))
trusted(b, c)
check("a trusted contradiction leaves neither side EARNED", b.verdict("f1")[1], "OPEN")
forged = dict(a.statement("f2", True, 0), value=False)
check("a statement with a bad signature is dropped", b.receive(forged), False)

print("p2p — the cube: delayed truth settles, proofs of fault act at once")
e = Peer("e", quorum=1)
e.truth("g1", True)
e.receive(a.statement("g1", False, 1))
check("a refuted statement makes its signer F", e.cube.mark(a.id), "F")
x = Peer("x", quorum=1)
trusted(x, d)
x.receive(d.statement("h1", True, 0))
auditor = Peer("auditor")
check("an honest attestation audits CONFIRMED", auditor.check_attestation(x.attest("h1")), "CONFIRMED")
check("a forged attestation audits FAULT", auditor.check_attestation(x.attest("h1", forge=True)), "FAULT")
check("the forger is F at once, no truth needed", auditor.cube.mark(x.id), "F")

print("p2p — forgiveness is not retroactive")
liar, judge = Peer("liar"), Peer("judge", quorum=1)
judge.truth("old-rev", True)
judge.receive(liar.statement("old-rev", False, 2))           # a lie of round 2, refuted
for r in range(20, 26):                                     # six clean rounds later
    judge.truth(f"new-rev{r}", True)
    judge.receive(liar.statement(f"new-rev{r}", True, r))
judge.receive(liar.statement("old-hidden", False, 3))       # another word of that time
judge.receive(liar.statement("new-hidden", True, 26))
check("the current mark is T again (forgiven)", judge.cube.mark(liar.id), "T")
check("a word of the lying time stays excluded", judge.verdict("old-hidden"), (None, "OPEN"))
check("a word of the clean time is EARNED", judge.verdict("new-hidden"), (True, "EARNED"))

print("p2p — quorum (default 2)")
check("the default quorum is 2", Peer("dflt").quorum, 2)
q2, w1, w2 = Peer("q2", quorum=2), Peer("w1"), Peer("w2")
trusted(q2, w1)
trusted(q2, w2)
q2.receive(w1.statement("k1", True, 0))
check("one trusted witness is not EARNED under quorum 2", q2.verdict("k1"), (None, "OPEN"))
q2.receive(w2.statement("k1", True, 0))
check("two trusted witnesses are EARNED", q2.verdict("k1"), (True, "EARNED"))

print("p2p — counting equals the ZTL formula (the fallback for many supporters)")
import itertools, random as _r  # noqa: E401,E402
import aak.p2p as P  # noqa: E402
rng = _r.Random(7)
same = total = 0
for trial in range(300):
    q = rng.choice([1, 2, 3])
    k_yes, k_no = rng.randint(1, 5), rng.randint(0, 3)
    peer = Peer(f"eq{trial}", quorum=q)
    signers = [Peer(f"sg{trial}_{i}") for i in range(k_yes + k_no)]
    for i, sg in enumerate(signers):
        if rng.random() < 0.6:
            trusted(peer, sg)
        peer.receive(sg.statement("fx", i < k_yes, 0))
    P.FORMULA_MAX = 99
    by_formula = peer.verdict("fx")
    P.FORMULA_MAX = 0
    by_count = peer.verdict("fx")
    P.FORMULA_MAX = 8
    same += by_formula == by_count
    total += 1
check(f"counting == formula on {total} random small cases", same, total)

print("p2p — zones: public seats, the tree of triples (ZTL table), the alarm, either")
from aak.p2p import seats, fold, T3  # noqa: E402
check("the triple table (by ZTL) is 2-of-3 on all 27", all(
    T3[u] == ("g" if u.count("g") >= 2 else "b" if u.count("b") >= 2 else "r") for u in T3), True)
pool = [f"id{i:03d}" for i in range(243)]
check("seats are public: the same fact, the same seats", seats("fz", pool) == seats("fz", pool), True)
check("seats regroup: another fact, other seats", seats("fz", pool) != seats("fy", pool), True)
check("a full tree of g folds to g", fold(["g"] * 81), "g")
check("two of three triples g, one b -> g", fold(list("ggg" "ggg" "bbb")), "g")
check("empty seats (r) do not vote: mostly empty -> r", fold(list("grr" "rrr" "rrr")), "r")
jz = Peer("jz", quorum=2)
sig = [Peer(f"s{i}") for i in range(9)]
for sg in sig:
    trusted(jz, sg)
st_seats = [sg.id for sg in sig]
for i, sg in enumerate(sig):
    jz.receive(sg.statement("fz9", i != 0, 0))              # 8 say true, 1 says false
check("flat: one trusted contradiction blocks", jz.verdict("fz9", only=set(st_seats)), (None, "OPEN"))
check("tree + alarm: 8 of 9 decide", jz.verdict_combined("fz9", st_seats), (True, "EARNED"))
check("either: decides when one rule does and none opposes", jz.verdict_either("fz9", st_seats), (True, "EARNED"))

print("p2p — the stand (regression, small and deterministic)")
import run_p2p as R  # noqa: E402
r = R.run(0, n=12, rounds=12, use_cube=True)
check("stand, cube on: no false EARNED", r["false_earned"], 0)
r2 = R.run(0, n=12, rounds=12, use_cube=True)
check("stand is deterministic by seed", (r2["right_earned"], r2["open"]), (r["right_earned"], r["open"]))

print(f"\nP2P {'GREEN' if not FAIL else 'RED'}: {OK} OK, {FAIL} FAIL")
sys.exit(1 if FAIL else 0)
