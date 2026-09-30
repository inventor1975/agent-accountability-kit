"""Many agents, no centre: every peer is its own judge.

Each peer is a ZTL judge node (ztljudgenode, vendored unchanged: hash-chained memory,
reproducible verdict hash, Ed25519-signed attestations). Peers sign STATEMENTS about facts
and send them to each other; messages arrive late, out of order, or not at all, and a peer
may be offline. Nobody collects or counts: every consumer decides for itself.

THE CUBE (from the ZTL swarm work; also the kit's journal cube):
each consumer keeps, for every signer it has heard, the outcomes of that signer's settled
statements. DELAYED TRUTH settles them: the true value of some facts becomes known later,
and every statement a consumer holds on such a fact is thereby confirmed or refuted.
Over the last WINDOW settled statements of a signer: any refuted -> F; else any
confirmed -> T; else Z. WINDOW clean ones forgive an F.

ADMISSION, per consumer, per fact: a statement from a T signer is a verified atom; from a
Z signer an UNVERIFIED atom (it may be true, it may be a lie); from an F signer nothing.
The consumer judges "the fact is true" as (s_1 | ... ) & ~(c_1 | ... ) over the statements
it holds (s = says true, c = says false), and the mirror for "false". ZTL makes this
zero-trust: an unverified contradiction keeps the claim OPEN, a verified one refutes it,
a missing message is simply absent. EARNED only when trusted support stands and no
statement it holds speaks against it.

PROOF-OF-FAULT: a peer may also publish a signed ATTESTATION of its verdict. Any peer
re-computes it from the snapshot the attestation carries (ztljudgenode.audit); a mismatch
is a signed proof, and the forger's mark goes to F at once, without waiting for truth.
"""
import collections
import hashlib
import itertools
import os
import random
import sys
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "core", "ztlcore"))
import ztljudgenode  # noqa: E402  the vendored judge node (ZTL da25c1a)
from ztljudgenode import Node, audit, _canon  # noqa: E402

WINDOW = 5
SPAN = 5
FORMULA_MAX = 8          # above this many supporters the verdict is counted (equal, tested)
# MIN_VOTES over public seats (the swarm's rule, taken as is: "a verdict needs >= 12 trusted
# votes"). Measured 30.09 on a holdout: at 40-50% message loss a judge got 5 statements of 81
# seats, all from colluders, 2 of them trusted - quorum 2 met, no contradiction, a false EARNED.
MIN_VOTES = 12


# ---- ZONES: a tree of triples (from the ZTL swarm work). Every fact gets SEATS drawn by
# public randomness (a liar cannot
# choose where to sit); a consumer fills each seat with g (a trusted seat-holder said true),
# b (said false) or r (nothing trusted heard: an empty seat is the mark Z), and folds the
# seats three by three, 2 of 3 at every level, up to one root. The triple's table is computed
# by ZTL itself: "at least two of three" judged over the marking g=T, b=F, r=Z.
def _triple_table():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "core", "ztlcore"))
    from ztljudge import judge
    f = "(a0 & a1) | (a0 & a2) | (a1 & a2)"
    tab = {}
    for us in itertools.product("gbr", repeat=3):
        m = {f"a{i}": {"g": "T", "b": "F", "r": "Z"}[u] for i, u in enumerate(us)}
        neg = {k: {"T": "F", "F": "T"}.get(v, v) for k, v in m.items()}
        tab[us] = ("g" if judge(f, m)["disposition"] == "EARNED" else
                   "b" if judge(f, neg)["disposition"] == "EARNED" else "r")
    return tab


T3 = _triple_table()
assert all(T3[u] == ("g" if u.count("g") >= 2 else "b" if u.count("b") >= 2 else "r") for u in T3)


def seats(fact, agents, depth=4):
    """The fact's 3**depth checkers, drawn by PUBLIC randomness (the fact's own hash): anyone
    can recompute them, nobody can choose them."""
    rng = random.Random(hashlib.sha256(str(fact).encode()).digest())
    return rng.sample(sorted(agents), min(3 ** depth, len(agents)))


def fold(units):
    """Fold a list of 3**k units (g/b/r) three by three to one root."""
    while len(units) > 1:
        units = [T3[tuple(units[i:i + 3])] for i in range(0, len(units), 3)]
    return units[0]


class Cube:
    """One consumer's trust in each signer, from delayed truth (and proofs of fault).

    FORGIVENESS IS NOT RETROACTIVE (measured 30.09, run_p2p seed 1: the only two false EARNED
    came from a 'reform' liar - lying in rounds 0-9, honest after - whose CURRENT mark T,
    earned by clean later rounds, was applied to his OLD lies of rounds 2 and 7). A statement
    is judged by the signer's record AROUND THE TIME IT WAS MADE: the settled outcomes of his
    statements within SPAN rounds of it. mark() - the latest WINDOW - stays for new words."""

    def __init__(self, window=WINDOW, span=SPAN):
        self.window, self.span = window, span
        self.hist = collections.defaultdict(list)     # signer -> [(round, ok), ...] in settle order

    def settle(self, signer, ok, rnd=None):
        self.hist[signer].append((rnd, bool(ok)))

    def mark(self, signer):
        last = [ok for _, ok in self.hist.get(signer, [])[-self.window:]]
        if not last:
            return "Z"
        return "F" if not all(last) else "T"

    def mark_at(self, signer, rnd):
        """The signer's record around round `rnd`; a proof of fault (round None) counts always."""
        near = [ok for r, ok in self.hist.get(signer, []) if r is None or abs(r - rnd) <= self.span]
        if not near:
            return "Z"
        return "F" if not all(near) else "T"


_SIG_OK = {}


def _verified(st):
    """Ed25519 check of a statement. Deterministic, so a stand may cache it across peers."""
    key = (st["sig"], st["signer"], st["fact"], st["value"], st["round"])
    if key not in _SIG_OK:
        body = {k: st[k] for k in ("signer", "fact", "value", "round")}
        try:
            pub = ztljudgenode.Ed25519PublicKey.from_public_bytes(bytes.fromhex(st["signer"]))
            pub.verify(bytes.fromhex(st["sig"]), _canon(body).encode())
            _SIG_OK[key] = True
        except Exception:
            _SIG_OK[key] = False
    return _SIG_OK[key]


class Peer:
    def __init__(self, pid, seed=None, use_cube=True, quorum=2):
        self.pid = pid
        self.node = Node(":memory:", seed=seed)
        self.id = self.node.node_id
        self.use_cube = use_cube
        # QUORUM (measured 30.09): at 45% liars and sparse observation all 35 false EARNED were
        # ONE trusted witness - a 'rare' liar (lies 1 in 10, record almost clean) - held alone.
        # No judge can tell one witness's lie from truth; quorum=2 asks two trusted supporters.
        self.quorum = quorum
        self.cube = Cube()
        self.held = collections.defaultdict(dict)     # fact -> {signer: value}
        self.said_at = {}                              # (fact, signer) -> round of the statement
        self.known = {}                                # fact -> true value (delayed truth)
        self.faults = []                               # signers proven wrong by audit
        self.formula = {}                              # fact -> the formula of its EARNED verdict

    # ---- saying
    def statement(self, fact, value, rnd):
        body = {"signer": self.id, "fact": fact, "value": bool(value), "round": rnd}
        return {**body, "sig": self.node._sign(_canon(body))}

    # ---- hearing
    def receive(self, st):
        if not _verified(st):
            return False                               # a bad signature is dropped
        if st["signer"] in self.held[st["fact"]]:
            return True                                # first word stands; a second is ignored
        self.held[st["fact"]][st["signer"]] = st["value"]
        self.said_at[(st["fact"], st["signer"])] = st["round"]
        if st["fact"] in self.known:                   # truth already out: settle on arrival
            self.cube.settle(st["signer"], st["value"] == self.known[st["fact"]], st["round"])
        return True

    def truth(self, fact, value):
        """Delayed truth reaches this peer: settle every statement it holds on the fact."""
        if fact in self.known:
            return
        self.known[fact] = value
        for signer, v in self.held.get(fact, {}).items():
            self.cube.settle(signer, v == value, self.said_at.get((fact, signer)))

    def check_attestation(self, att):
        r = audit(att)
        if r["result"] == "FAULT":
            self.cube.settle(att["node_id"], False)    # a signed proof: F now, no waiting
            self.faults.append(att["node_id"])
        return r["result"]

    # ---- judging
    def _mark(self, signer, fact=None):
        if not self.use_cube:
            return "T"
        rnd = self.said_at.get((fact, signer))
        return self.cube.mark_at(signer, rnd) if rnd is not None else self.cube.mark(signer)

    def verdict_tree(self, fact, fact_seats, unseat_known_liars=False):
        """The tree of triples over the fact's public seats -> (decision, disposition).
        unseat_known_liars: the swarm's rule 'known liars not seated' - seats whose holder
        is F (at that time) are dropped and the tree is folded over the rest."""
        if fact in self.known:
            return self.known[fact], "KNOWN"
        held = self.held.get(fact, {})
        if unseat_known_liars:
            fact_seats = [s for s in fact_seats if self._mark(s, fact) != "F"]
        units = []
        for s in fact_seats:
            if s in held and self._mark(s, fact) == "T":
                units.append("g" if held[s] else "b")
            else:
                units.append("r")                      # empty or untrusted seat: the mark Z
        n = 1
        while n < len(units):
            n *= 3
        units += ["r"] * (n - len(units))
        root = fold(units)
        return ({"g": (True, "EARNED"), "b": (False, "EARNED")}.get(root, (None, "OPEN")))

    def verdict_combined(self, fact, fact_seats):
        """The tree with known liars unseated, AND an alarm (the swarm's supermajority): the
        root's side must also hold at least 2/3 of the trusted seats that spoke."""
        dec, disp = self.verdict_tree(fact, fact_seats, unseat_known_liars=True)
        if disp != "EARNED":
            return dec, disp
        held = self.held.get(fact, {})
        votes = [held[s] for s in fact_seats if s in held and self._mark(s, fact) == "T"]
        pro, con = sum(v == dec for v in votes), sum(v != dec for v in votes)
        return (dec, "EARNED") if 3 * pro >= 2 * (pro + con) else (None, "OPEN")

    def verdict_either(self, fact, fact_seats):
        """Flat (any trusted contradiction blocks) OR combined tree; opposite decisions -> OPEN."""
        a = self.verdict(fact, only=set(fact_seats))
        b = self.verdict_combined(fact, fact_seats)
        decided = {d for d, disp in (a, b) if disp == "EARNED"}
        if len(decided) == 1:
            return decided.pop(), "EARNED"
        return None, "OPEN"

    def contested_share(self, fact, fact_seats):
        """Share of leaf triples that hold both a trusted 'true' and a trusted 'false'."""
        held = self.held.get(fact, {})
        units = [("g" if held[s] else "b") if (s in held and self._mark(s, fact) == "T") else "r"
                 for s in fact_seats]
        trip = [units[i:i + 3] for i in range(0, len(units), 3)]
        live = [x for x in trip if sum(u != "r" for u in x) >= 2]
        return (sum("g" in x and "b" in x for x in live) / len(live)) if live else 0.0

    def verdict_guarded(self, fact, fact_seats, tau=0.1):
        """The swarm's contested-block alarm, as a switch: when more than `tau` of the live leaf
        triples are contested, a coalition may be at work - decide by the flat rule only (any
        trusted contradiction blocks); otherwise by 'either'."""
        if self.contested_share(fact, fact_seats) > tau:
            return self.verdict(fact, only=set(fact_seats))
        return self.verdict_either(fact, fact_seats)

    def verdict(self, fact, only=None):
        """-> (decision, disposition): decision True / False / None (open). `only`: count only
        these signers (the fact's seats); over seats a decision also needs MIN_VOTES trusted
        supporters (few voices out of many seats is sparse evidence, not a verdict)."""
        if fact in self.known:
            return self.known[fact], "KNOWN"
        if only is not None and len(only) >= 3 * MIN_VOTES:
            held = self.held.get(fact, {})
            for side in (True, False):
                n = sum(1 for s, v in held.items() if s in only and v == side and self._mark(s, fact) == "T")
                if n >= MIN_VOTES:
                    break
            else:
                return None, "OPEN"
        s, c = [], []
        fid = zlib.crc32(str(fact).encode())           # stable across runs (hash() is salted)
        for signer, v in sorted(self.held.get(fact, {}).items()):
            if only is not None and signer not in only:
                continue
            m = self._mark(signer, fact)
            if m == "F":
                continue
            name = f"{'s' if v else 'c'}_{signer[:10]}_{fid}"
            self.node.assert_atom(name, "T" if m == "T" else "Z", "statement", signer[:12])
            (s if v else c).append(name)
        verified = {x for x in s + c if self.node.verdict_of(x) == "T"}
        for claim, yes, no in ((True, s, c), (False, c, s)):
            if not yes:
                continue
            if len(yes) > FORMULA_MAX:
                # THE SAME RULE BY COUNTING, for many supporters: the OR over all quorum-subsets
                # of k supporters has C(k, q) terms (81 seats: ~1,770 pairs) and overflows the
                # parser. Equal to the formula - tests/test_p2p.py checks both on every small
                # case: EARNED iff >= quorum supporters are verified and NOTHING speaks against
                # (a verified contradiction refutes, an unverified one keeps it open).
                if sum(x in verified for x in yes) >= self.quorum and not no:
                    return claim, "EARNED"
                continue
            if self.quorum > 1:
                import itertools
                groups = [" & ".join(g) for g in itertools.combinations(yes, self.quorum)]
                if not groups:
                    continue
                support = " | ".join(f"({g})" for g in groups)
            else:
                support = " | ".join(yes)
            f = "(" + support + ")" + (" & ~(" + " | ".join(no) + ")" if no else "")
            r = self.node.judge_claim(f)
            if r["disposition"] == "EARNED":
                self.formula[fact] = f
                return claim, "EARNED"
        return None, "OPEN"

    def attest(self, fact, forge=False):
        """A signed attestation of this peer's EARNED verdict on `fact`, for others to audit.
        forge=True: a Byzantine peer signs a verdict that does not follow (demo/stand only)."""
        dec, _ = self.verdict(fact)
        if dec is None or fact not in self.formula:
            return None
        f = self.formula[fact]
        return self.node.forge(f, "F", "REFUTED") if forge else self.node.attest(f)
