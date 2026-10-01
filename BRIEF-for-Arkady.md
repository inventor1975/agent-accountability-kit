# Brief — Agent Accountability Kit (prototype, 30 Sept 2026)

**What it is.** A small open-source kit that lets an AI agent's answer leave only when a
zero-trust judge (the ZTL kernel) rules that its conclusion is earned from premises whose
evidence the kit checks itself — and that keeps an outcome journal with a trust cube per
agent and per kind of claim, humans included (factual claims only, never a veto).

**Why it may fit Foresight "AI for Science & Safety Nodes" (deadline 31 Oct 2026).**
Focus area 2, "Supercollaboration and decentralized alignment", lists: distributed oversight,
agent monitoring and verification projects; scalable verification and proof techniques;
credit-assignment protocols; and excludes reliance on a single central authority. The kit is
agent monitoring by verification, with an outcome journal as credit assignment. Area 3,
"Human Empowerment", asks for mechanisms to detect "oversight theatre"; the trust cube on agents
and humans measures when a word can be relied on and when evidence is required.

**What exists today.** Gate, trace checks (file / count / url / commit / self), outcome journal
and trust cube, a deterministic demo (two agents and a human), a test stand; ZTL kernel vendored
(upstream: Lean proofs). The same mechanism ran on the ZTL project's own AI assistant
(29 Sept – 1 Oct 2026) and was then retired there: it caught slips, not losses of meaning.

**No centre (added 30 Sept, evening).** `aak/p2p.py`: every agent is its own ZTL judge node
(public `ztljudgenode` from ZTL); signed statements over an unreliable network (delay, loss,
offline); trust per signer from delayed truth (the cube); proof-of-fault by re-computation;
quorum 2. Stand: 30 agents, a third lying in six ways, 3 seeds — 0 false EARNED, 90–93% of the
never-revealed facts decided correctly (1351/1460, 1551/1660, 1590/1760); without the cube,
half as many. Honest limit: colluding liars who look honest defeat any witness count
(measured); only ground truth or self-checked traces stop them. This answers the RFP's
"without relying on a single central authority: mutual monitoring and cross-checking among
agents".

**Swarm work.** The decentralized trust experiments (trust as a ZTL mark from delayed truth,
5K–100K agents) were done by the curator with the second assistant; the curator has cleared
including them.

**Open.** No external users yet; no numbers beyond our own use; the in-person hub priority
(SF / Berlin) is the main minus. The form's fields are listed in the attached notes.
