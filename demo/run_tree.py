"""The zones stand: the swarm's tree of triples against a flat quorum, on one world.

N agents sign; every fact gets 3**depth SEATS by public randomness (the fact's hash), and only
seat-holders' statements count. A seated agent observes the fact unless it is offline or misses
it; its signed statement travels to every consumer with a random delay, or is lost. Delayed
truth on part of the facts builds each consumer's cube (time-indexed trust). Liars (a fraction)
follow one strategy; 'coalition' liars all lie on the SAME facts (1 in 10) - the case that
broke the flat quorum.

A consumer's view does not depend on other consumers (no relaying in this model), so the stand
keeps full state only for a sample of honest consumers; all agents still sign and are seated.
Judged: the facts whose truth is never published, by each sampled honest consumer, after all
messages land. Arms on the same world: tree (2 of 3 at every level, ZTL table) and flat quorum 2
over the same seats.

Usage: python3 demo/run_tree.py [--seeds 3] [--n 243] [--depth 4] [--liars 0.33] [--strategy coalition]
"""
import argparse
import json
import os
import random
import sys
import time
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from aak.p2p import Peer, seats  # noqa: E402


def lies(strategy, rnd, rng, fact, p_betray=0.25):
    """'cycle' - wash, earn, betray, in collusion (the attack that broke the swarm's newspaper
    arm): all cycle liars are honest for 8 rounds (earning trust), then betray for 2 rounds on
    the SAME facts (one shared coin per fact, probability p_betray), then wash again."""
    coin = (zlib.crc32(fact.encode()) % 1000) / 1000.0
    return (strategy == "always" or (strategy == "sleeper" and rnd >= 12)
            or (strategy == "reform" and rnd < 8) or (strategy == "rare" and rng.random() < 0.1)
            or (strategy == "coalition" and zlib.crc32(fact.encode()) % 10 == 0)
            or (strategy == "cycle" and rnd % 10 >= 8 and coin < p_betray))


def run(seed, n=243, depth=4, rounds=30, facts_per_round=2, observe=0.9, liars=1 / 3,
        strategy="coalition", max_delay=3, drop=0.1, offline=0.1, reveal=0.5, consumers=30,
        regroup=True, target=0, p_betray=0.25, explain=False):
    rng = random.Random(f"tree:{seed}")
    agents = [Peer(i, seed=rng.randbytes(32)) for i in range(n)]
    ids0 = [a.id for a in agents]
    if target:
        # AN ADAPTIVE ATTACKER with a budget of `target` agents: it corrupts members of the
        # committee it can SEE - the fixed seats - first. Against regrouping per fact there is no
        # fixed committee to see; the same agents are then seated only in some facts.
        committee = seats("fixed", ids0, depth)
        liar = {ids0.index(s) for s in committee[:target]}
    else:
        liar = set(rng.sample(range(n), round(n * liars)))
    honest = [i for i in range(n) if i not in liar]
    judges = {i: Peer(f"judge{i}", quorum=2) for i in rng.sample(honest, min(consumers, len(honest)))}
    ids = [a.id for a in agents]
    inbox, truth, hidden, seat_of = {}, {}, [], {}
    t0 = time.time()
    last = rounds + max_delay + 1
    for r in range(last + 1):
        down = {i for i in range(n) if rng.random() < offline} if r < rounds else set()
        jdown = {j for j in judges if rng.random() < offline} if r < rounds else set()
        if r < rounds:
            for k in range(facts_per_round):
                f = f"r{r}f{k}"
                truth[f] = rng.random() < 0.5
                # regroup=False: the SAME seats in the same triples for every fact (no regrouping)
                seat_of[f] = seats(f if regroup else "fixed", ids, depth)
                for sid in seat_of[f]:
                    i = ids.index(sid)
                    if i in down or rng.random() >= observe:
                        continue
                    val = (not truth[f]) if (i in liar and lies(strategy, r, rng, f, p_betray)) else truth[f]
                    st = agents[i].statement(f, val, r)
                    for j in judges:
                        if rng.random() >= drop:
                            inbox.setdefault(r + rng.randint(0, max_delay), []).append((j, st))
        for j, st in inbox.pop(r, []):
            if j not in jdown:
                judges[j].receive(st)
        if 1 <= r <= rounds:
            for k in range(facts_per_round):
                f = f"r{r - 1}f{k}"
                if rng.random() < reveal:
                    for j in judges:
                        if j not in jdown:
                            judges[j].truth(f, truth[f])
                else:
                    hidden.append(f)
    res = {}
    warm = [f for f in hidden if int(f[1:].split("f")[0]) >= 5]      # after the warm-up rounds 0-4
    for arm in ("tree", "treeF", "combined", "either", "flat", "g05", "g10", "g20"):
        c = {"false_earned": 0, "right_earned": 0, "open": 0, "right_after_warmup": 0}
        for j, p in judges.items():
            for f in hidden:
                dec, disp = (p.verdict_tree(f, seat_of[f]) if arm == "tree" else
                             p.verdict_tree(f, seat_of[f], unseat_known_liars=True) if arm == "treeF" else
                             p.verdict_combined(f, seat_of[f]) if arm == "combined" else
                             p.verdict_either(f, seat_of[f]) if arm == "either" else
                             p.verdict_guarded(f, seat_of[f], tau={"g05": 0.05, "g10": 0.1, "g20": 0.2}[arm]) if arm.startswith("g")
                             else p.verdict(f, only=set(seat_of[f])))
                if disp == "EARNED":
                    c["right_earned" if dec == truth[f] else "false_earned"] += 1
                    if explain and arm == "flat" and dec != truth[f]:
                        held = p.held.get(f, {})
                        res.setdefault("_why", []).append({"fact": f, "truth": truth[f], "seats": len(seat_of[f]),
                            "held": sorted((("liar" if ids.index(s) in liar else "honest"), v, p._mark(s, f))
                                           for s, v in held.items() if s in set(seat_of[f]))})
                    c["right_after_warmup"] += (dec == truth[f]) and f in warm
                else:
                    c["open"] += 1
        res[arm] = c
    why = res.pop("_why", [])
    return {"why": why, "seed": seed, "n": n, "seats": 3 ** depth, "regroup": regroup, "p_betray": p_betray,
            "drop": drop, "reveal": reveal, "liars": round(liars, 2), "strategy": strategy,
            "judged": len(judges) * len(hidden), "judged_after_warmup": len(judges) * len(warm), **{f"{a}_{k}": v for a in res for k, v in res[a].items()},
            "seconds": round(time.time() - t0, 1)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--n", type=int, default=243)
    ap.add_argument("--depth", type=int, default=4)
    ap.add_argument("--liars", type=float, default=1 / 3)
    ap.add_argument("--strategy", default="coalition")
    a = ap.parse_args()
    for seed in range(a.seeds):
        print(json.dumps(run(seed, n=a.n, depth=a.depth, liars=a.liars, strategy=a.strategy)), flush=True)
