"""The outcome journal and the trust cube.

One line per claim, appended, never rewritten: agent, kind (fact | measurement | new |
cause | done | ...), claim, ref, outcome (open | confirmed | refuted), by (what settled it).
Settling appends a new line for the same id; the latest line wins.

The cube, per (agent, kind), over the last WINDOW settled claims: a refuted one -> F;
confirmed and clean -> T; nothing settled -> Z. WINDOW clean confirmations forgive an F.
Humans are agents here too — but only their FACTUAL claims; a decision is not true or false.
"""
import datetime
import json
import pathlib
import uuid

WINDOW = 5


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


class Journal:
    def __init__(self, path):
        self.path = pathlib.Path(path)

    def _append(self, rec):
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def load(self):
        latest, order = {}, []
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    r = json.loads(line)
                    if r["id"] not in latest:
                        order.append(r["id"])
                    latest[r["id"]] = r
        return [latest[i] for i in order]

    def add(self, agent, kind, claim, ref="", outcome="open", by="", at=None):
        if outcome not in ("open", "confirmed", "refuted"):
            raise ValueError("outcome: open | confirmed | refuted")
        if outcome != "open" and not by:
            raise ValueError("a settled claim needs `by`: what settled it")
        at = at or _now()
        rec = {"id": uuid.uuid4().hex[:8], "at": at, "agent": agent, "kind": kind, "claim": claim,
               "ref": ref, "outcome": outcome, "by": by, "settled_at": at if outcome != "open" else ""}
        self._append(rec)
        return rec

    def settle(self, cid, outcome, by, at=None):
        if outcome not in ("confirmed", "refuted") or not by:
            raise ValueError("settle to confirmed | refuted, with `by`")
        cur = {r["id"]: r for r in self.load()}[cid]
        rec = dict(cur, outcome=outcome, by=by, settled_at=at or _now())
        self._append(rec)
        return rec

    def find_open(self, agent, text):
        return [r for r in self.load() if r["agent"] == agent and r["outcome"] == "open" and r["claim"] == text]

    def cube(self, window=WINDOW):
        """{(agent, kind): {"mark", "window": (conf, ref), "all_time": (conf, ref), "open"}}"""
        groups = {}
        for r in self.load():
            groups.setdefault((r["agent"], r["kind"]), []).append(r)
        out = {}
        for key, rs in groups.items():
            settled = sorted((r for r in rs if r["outcome"] != "open"), key=lambda r: r["settled_at"])
            win = settled[-window:]
            ref = sum(r["outcome"] == "refuted" for r in win)
            con = sum(r["outcome"] == "confirmed" for r in win)
            out[key] = {"mark": "F" if ref else ("T" if con else "Z"), "window": (con, ref),
                        "all_time": (sum(r["outcome"] == "confirmed" for r in settled),
                                     sum(r["outcome"] == "refuted" for r in settled)),
                        "open": sum(r["outcome"] == "open" for r in rs)}
        return out

    def mark(self, agent, kind):
        return self.cube().get((agent, kind), {"mark": "Z"})["mark"]
