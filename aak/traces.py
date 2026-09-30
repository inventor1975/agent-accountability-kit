"""Traces the kit checks itself. An agent may PROPOSE that a premise is verified; only a
trace that holds here makes it so (VEIP: authorization precedes execution)."""
import pathlib
import re
import subprocess
import urllib.request


def check(trace):
    """(holds, note). kinds: file(path[, contains]) · count(path, pattern[, regex], equals) · url(url[, contains])
    · commit(repo, rev) · self(reason)."""
    if not trace:
        return False, "no trace"
    kind = trace.get("kind")
    try:
        if kind == "file":
            p = pathlib.Path(trace["path"])
            if not p.exists():
                return False, f"file {p.name} does not exist"
            want = trace.get("contains")
            if want is None:
                return True, f"file {p.name} exists"
            return (want in p.read_text(encoding="utf-8", errors="replace"),
                    f"file {p.name} {'contains' if want in p.read_text(encoding='utf-8', errors='replace') else 'lacks'} {want!r}")
        if kind == "url":
            with urllib.request.urlopen(trace["url"], timeout=15) as r:
                body = r.read().decode("utf-8", errors="replace")
            want = trace.get("contains")
            return (want is None or want in body), f"url {trace['url']} {r.status}"
        if kind == "commit":
            ok = subprocess.run(["git", "-C", trace["repo"], "cat-file", "-e", trace["rev"] + "^{commit}"],
                                capture_output=True).returncode == 0
            return ok, f"commit {trace['rev']} {'exists' if ok else 'not found'}"
        if kind == "count":                     # the kit RECOMPUTES: lines matching a pattern
            p = pathlib.Path(trace["path"])
            pat = trace.get("pattern", "")
            hit = (lambda s: re.search(pat, s) is not None) if trace.get("regex") else (lambda s: pat in s)
            n = sum(1 for line in p.read_text(encoding="utf-8", errors="replace").splitlines() if hit(line))
            return n == int(trace["equals"]), f"count of {trace.get('pattern', '')!r} in {p.name} = {n}"
        if kind == "self":
            reason = (trace.get("reason") or "").strip()
            return bool(reason), "SELF: " + (reason or "no reason given")
    except Exception as e:                      # an unreadable trace does not hold
        return False, f"{kind} trace failed: {type(e).__name__}"
    return False, f"unknown trace kind {kind!r}"
