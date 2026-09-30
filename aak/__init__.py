"""Agent Accountability Kit — an answer leaves only when a zero-trust judge says it is earned.

  lay     the agent lays its answer as ZFL: premises (rows with traces) -> a conclusion (claim)
  check   every trace is checked by the kit, never taken on the agent's word (VEIP)
  judge   the ZTL kernel gives the verdict; only EARNED is released
  learn   an outcome journal records what each claim turned out to be; a trust cube per
          (agent, kind of claim) takes an agent's bare word away where its record is F
"""
from .journal import Journal
from .judge import judge
from .gate import Gate

__all__ = ["Journal", "judge", "Gate"]
