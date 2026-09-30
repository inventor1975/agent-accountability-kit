"""Lay -> check -> judge. The agent chooses WHAT goes on the ground; it never decides WHETHER
a premise is verified. A verified row must carry a trace that holds (traces.py); if not, it
falls to unverified. A SELF trace (the agent's own word) is refused where the journal's
mark for (agent, kind) is F — except kind "evident" (true by the very act, like doubting).
Every SELF premise that stands is registered OPEN in the journal, to be settled later."""
import os
import sys

from . import traces

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "core"))
import zfl  # noqa: E402  the vendored ZTL kernel


def judge(doc, agent="agent", journal=None, ref=""):
    """doc = {"rows": [{"name", "means", "status", "kind"?}], "claim": formula, "traces": {name: trace}}.
    Returns {"ok", "verdict", "disposition", "unverified", "downgraded", "self", "issues"}."""
    tr = doc.get("traces") or {}
    rows, downgraded, selfs, self_claims = [], [], [], []
    for row in doc.get("rows", []):
        row = dict(row)
        kind = row.pop("kind", "fact")
        if row.get("status") == "verified":
            t = tr.get(row["name"])
            ok, note = traces.check(t)
            if ok and t.get("kind") == "self":
                if journal is not None and kind != "evident" and journal.mark(agent, kind) == "F":
                    ok, note = False, f"SELF refused: {agent}'s record on '{kind}' claims is F"
                else:
                    selfs.append(row["name"])
                    self_claims.append((kind, row.get("means") or row["name"]))
            if ok:
                row.setdefault("ground", "trace-" + t["kind"])
            else:
                downgraded.append((row["name"], note))
                row["status"], row["ground"] = "unverified", ""
                row.pop("ground")
        rows.append(row)
    r = zfl.run({"rows": rows, "claim": doc.get("claim", "")})
    j = (r.get("report") or {}).get("judge") or {}
    if journal is not None and r.get("ok"):
        for kind, text in self_claims:
            if not journal.find_open(agent, text):
                journal.add(agent, kind, text, ref=ref)
    return {"ok": bool(r.get("ok")), "verdict": j.get("verdict"), "disposition": j.get("disposition"),
            "unverified": j.get("unverified") or [], "downgraded": downgraded, "self": selfs,
            "issues": [i for i in r.get("issues", []) if i.get("level") == "error"]}
