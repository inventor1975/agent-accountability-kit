"""The no-centre stand: many agents, a third of them lying, over an unreliable network.

Every round a few facts happen; each agent observes some of them and signs statements;
statements travel to every peer with a random delay (out of order), some are lost, some
peers are offline for a round (they neither send nor receive). Later the truth of a part of
the facts is published (DELAYED TRUTH) and every peer settles what it holds - the cube.
Liars (a third) follow one of five strategies: always (flip), silent (say nothing),
sleeper (honest, then flip), reform (flip, then honest), forge (honest statements, forged
verdict attestations). Every peer judges alone; nobody counts.

Measured on the facts whose truth is NEVER published, by every honest peer, after all
messages have landed: false EARNED (the dangerous number), correct EARNED, OPEN.
Arms: the cube ON, and the cube OFF (every signer trusted). Deterministic by seed.

Usage: python3 demo/run_p2p.py [--seeds 3] [--n 30] [--rounds 40]
"""
import argparse
import json
import zlib
import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from aak.p2p import Peer  # noqa: E402

STRATEGIES = ["always", "silent", "sleeper", "reform", "forge", "rare"]


def lies(strategy, rnd, rng, fact=""):
    """'rare' lies on one statement in ten and keeps an almost clean record. 'coalition':
    all such liars lie on the SAME facts (one in ten, chosen by the fact's name) - collusion,
    which no quorum of independent witnesses is built to stop."""
    return (strategy == "always" or (strategy == "sleeper" and rnd >= 15)
            or (strategy == "reform" and rnd < 10) or (strategy == "rare" and rng.random() < 0.1)
            or (strategy == "coalition" and zlib.crc32(fact.encode()) % 10 == 0))


def run(seed, strategies=None, n=30, rounds=40, facts_per_round=4, observe=0.3, liar_frac=1 / 3, max_delay=3,
        drop=0.1, offline=0.1, reveal=0.5, attest_every=5, use_cube=True, explain=False, quorum=2):
    rng = random.Random(f"p2p:{seed}")           # the world: facts, observers, network, truth
    arng = random.Random(f"p2p-att:{seed}")      # attestations only: both arms see ONE world
    peers = [Peer(i, seed=rng.randbytes(32), use_cube=use_cube, quorum=quorum) for i in range(n)]
    liars = set(rng.sample(range(n), round(n * liar_frac)))
    pool = strategies or STRATEGIES
    strat = {p: pool[k % len(pool)] for k, p in enumerate(sorted(liars))}
    honest = [p for p in range(n) if p not in liars]
    inbox = {}                                    # round -> [(to, kind, message)]
    truth, revealed, hidden = {}, set(), []
    proofs = 0
    t0 = time.time()
    last = rounds + max_delay + 1
    for r in range(last + 1):
        down = {p for p in range(n) if rng.random() < offline} if r < rounds else set()
        if r < rounds:                            # facts happen, statements go out
            for k in range(facts_per_round):
                f = f"r{r}f{k}"
                truth[f] = rng.random() < 0.5
                for p in range(n):
                    if p in down or rng.random() >= observe:
                        continue
                    s = strat.get(p)
                    if s == "silent":
                        continue
                    val = (not truth[f]) if (s and lies(s, r, rng, f)) else truth[f]
                    st = peers[p].statement(f, val, r)
                    for q in range(n):
                        if q != p and rng.random() >= drop:
                            inbox.setdefault(r + rng.randint(0, max_delay), []).append((q, "st", st))
                    peers[p].receive(st)          # it holds its own word
            if r % attest_every == attest_every - 1:     # verdict attestations, for audit
                for p in range(n):
                    if p in down:
                        continue
                    for f in arng.sample([x for x in truth if x not in revealed], 2):
                        att = peers[p].attest(f, forge=(strat.get(p) == "forge"))
                        if att is None:
                            continue
                        for q in arng.sample(range(n), 3):
                            if q != p:
                                inbox.setdefault(r + arng.randint(0, max_delay), []).append((q, "att", att))
        for q, kind, msg in inbox.pop(r, []):     # deliver (offline peers lose what arrives)
            if q in down:
                continue
            if kind == "st":
                peers[q].receive(msg)
            elif peers[q].check_attestation(msg) == "FAULT":
                proofs += 1
        if 1 <= r <= rounds:                      # delayed truth of the previous round
            for k in range(facts_per_round):
                f = f"r{r - 1}f{k}"
                if rng.random() < reveal:
                    revealed.add(f)
                    for p in range(n):
                        if p not in down:
                            peers[p].truth(f, truth[f])
                else:
                    hidden.append(f)
    res = {"false_earned": 0, "right_earned": 0, "open": 0}
    who = {peers[i].id: i for i in range(n)}
    why = []
    for p in honest:
        for f in hidden:
            dec, disp = peers[p].verdict(f)
            if disp == "EARNED":
                res["right_earned" if dec == truth[f] else "false_earned"] += 1
                if explain and dec != truth[f]:
                    why.append({"peer": p, "fact": f, "truth": truth[f], "held": [
                        (who[s], strat.get(who[s], "honest"), v, peers[p]._mark(s, f))
                        for s, v in sorted(peers[p].held[f].items(), key=lambda x: who[x[0]])]})
            else:
                res["open"] += 1
    res.update(seed=seed, cube=use_cube, quorum=quorum, judged=len(honest) * len(hidden), proofs_of_fault=proofs,
               seconds=round(time.time() - t0, 1))
    if explain:
        res["why"] = why
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--rounds", type=int, default=40)
    ap.add_argument("--quorum", type=int, default=2)
    a = ap.parse_args()
    for seed in range(a.seeds):
        for cube in (True, False):
            print(json.dumps(run(seed, n=a.n, rounds=a.rounds, use_cube=cube, quorum=a.quorum)), flush=True)
