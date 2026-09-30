"""The release gate: an answer leaves only if the verdict on its ground is EARNED and every
number and commit hash it states stands in that ground. Otherwise it goes back to the agent
with the reasons — at most MAX_RETURNS times per turn; after that it leaves MARKED unearned,
so a human sees it (a gate that can silence an agent forever is not a safety feature)."""
import json
import re

from .judge import judge

MAX_RETURNS = 3
NUMBER = re.compile(r"(?<![\w.,:/-])\d+(?:[.,]\d+)?(?![\w])")
HASH = re.compile(r"(?<![\w])(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}(?![\w])")


def _num(s):
    s = s.replace(",", ".")
    return s.rstrip("0").rstrip(".") if "." in s else s


class Gate:
    def __init__(self, journal=None, max_returns=MAX_RETURNS):
        self.journal, self.max_returns, self.returns = journal, max_returns, {}

    def submit(self, agent, text, doc, turn="t"):
        """-> {"released": bool, "marked_unearned": bool, "reasons": [...], "record": judge(...)}"""
        rec = judge(doc, agent=agent, journal=self.journal, ref=f"{agent}:{turn}")
        reasons = []
        if not rec["ok"]:
            reasons.append(f"the ground is malformed: {[i['code'] for i in rec['issues']]}")
        elif rec["disposition"] != "EARNED":
            why = "; ".join(f"{n} — {note}" for n, note in rec["downgraded"]) or ", ".join(rec["unverified"]) or "—"
            reasons.append(f"not earned ({rec['verdict']} {rec['disposition']}); unverified: {why}")
        ground = json.dumps(doc, ensure_ascii=False)
        have = {_num(m.group(0)) for m in NUMBER.finditer(ground)}
        miss = sorted({_num(m.group(0)) for m in NUMBER.finditer(text)} - have)
        if miss:
            reasons.append(f"numbers said but not on the ground: {', '.join(miss)}")
        miss_h = sorted(h for h in {m.group(0) for m in HASH.finditer(text)} if h not in ground)
        if miss_h:
            reasons.append(f"hashes said but not on the ground: {', '.join(miss_h)}")
        if not reasons:
            return {"released": True, "marked_unearned": False, "reasons": [], "record": rec}
        key = (agent, turn)
        self.returns[key] = self.returns.get(key, 0) + 1
        if self.returns[key] > self.max_returns:
            return {"released": True, "marked_unearned": True, "reasons": reasons, "record": rec}
        return {"released": False, "marked_unearned": False, "reasons": reasons, "record": rec}
