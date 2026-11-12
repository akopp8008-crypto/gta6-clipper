"""On-screen hooks, titles and per-platform captions (see research/Clipping playbook.md).

* On-screen hook: 3-7 words, on screen from frame one to the end, opens a
  question or states the stakes. Viewers decide in under a second.
* YouTube title: a statement or "POV:" line, about 9 words, one emoji, no
  question (questions and "GTA ..." openers underperformed in our GTA sample).
* TikTok / Instagram caption: a searchable first line (the apps index caption
  text), then a prompt that gets sends or comments, then 3-4 topic hashtags.
  No #fyp: it says nothing about the clip.
"""
from __future__ import annotations

import hashlib

HOOKS = {
    "cop_escalation": ["One bump. Six stars.", "He just wanted to drive", "Vice City PD doesn't play",
                       "How fast this escalated"],
    "chaos_fail": ["Wait for it…", "He didn't see it coming", "This went so wrong",
                   "Worst landing in GTA 6"],
    "npc_weirdness": ["Wait for the NPC", "GTA 6 NPCs are unwell", "Only in Leonida",
                      "Nobody coded this on purpose"],
    "first_reaction": ["First time in Vice City", "His face when he saw this", "GTA 6 looks unreal",
                       "Nobody expected this detail"],
    "insane_skill": ["This shouldn't be possible", "He actually made it", "Cleanest escape in GTA 6",
                     "Watch the last second"],
    "wildlife": ["Don't go in the water", "The swamp chose violence", "GTA 6 gators are no joke"],
    "chat_moment": ["Chat called it", "Chat lost it here", "Watch chat explode"],
}

# YouTube titles: POV and statements beat questions in our sample. One emoji.
TITLES = {
    "cop_escalation": ["POV: You Bump ONE Cop Car in GTA 6 💀", "GTA 6 Cops Went From 1 Star to 6 in Seconds 💀"],
    "chaos_fail": ["POV: Your First Landing in GTA 6 💀", "This GTA 6 Plan Went So Wrong 💀"],
    "npc_weirdness": ["POV: You Walk Past the WRONG NPC in GTA 6 💀", "GTA 6 NPCs Are Not Okay 💀"],
    "first_reaction": ["POV: You Load Into Vice City for the First Time 🌴", "GTA 6 Detail Nobody Expected 🤯"],
    "insane_skill": ["The Cleanest Escape in GTA 6 So Far 🔥", "POV: You Actually Pull It Off in GTA 6 🔥"],
    "wildlife": ["POV: You Go in the Water in GTA 6 🐊", "The GTA 6 Swamp Chose Violence 🐊"],
    "chat_moment": ["Chat Called It Before He Did 💀", "The Moment Chat Lost It in GTA 6 💀"],
}

# Searchable first caption line per moment type (TikTok and Instagram index this text).
SEARCH_LINES = {
    "cop_escalation": "GTA 6 police chase",
    "chaos_fail": "GTA 6 funny fail",
    "npc_weirdness": "GTA 6 funny NPC moment",
    "first_reaction": "GTA 6 first reaction",
    "insane_skill": "GTA 6 insane escape",
    "wildlife": "GTA 6 alligator",
    "chat_moment": "GTA 6 funny stream moment",
}

# Instagram ranks sends per reach highest for non-followers; TikTok weighs comments and shares.
PROMPTS = {
    "instagram": ["Send this to the friend who drives like this", "Send this to whoever you'd play GTA 6 with"],
    "tiktok": ["What would you have done? 👇", "Rate this 1-10 👇"],
}

HASHTAGS = {
    "youtube": ["#GTA6", "#Shorts", "#GTAVI"],
    "tiktok": ["#gta6", "#gtavi", "#gaming", "#gta6clips"],
    "instagram": ["#gta6", "#gtavi", "#gaming", "#gta6clips"],
}


def _pick(options: list[str], *key: str) -> str:
    h = int(hashlib.sha1(":".join(key).encode()).hexdigest(), 16)
    return options[h % len(options)]


def hook_variants(kind: str, n: int = 3) -> list[str]:
    base = kind.split("+")[0]
    return HOOKS.get(base, HOOKS["chaos_fail"])[:n]


def pick_hook(kind: str, clip_id: str, platform: str, options: list[str] | None = None) -> str:
    """Different hook per platform so the three uploads are not identical copies."""
    return _pick(options or hook_variants(kind, 4), clip_id, platform)


def title(kind: str, clip_id: str, hook: str = "") -> str:
    """YouTube title: a POV/statement line, never a question."""
    base = kind.split("+")[0]
    t = _pick(TITLES.get(base, TITLES["chaos_fail"]), clip_id, "title")
    return t[:95]


def caption(kind: str, clip_id: str, platform: str, credit: str = "",
            hooks: list[str] | None = None, required: str = "") -> dict[str, str]:
    hook = pick_hook(kind, clip_id, platform, hooks)
    if required:
        # Campaign posts: hook line, then the campaign's required block exactly as written.
        if platform == "youtube":
            return {"title": hook[:95], "description": f"{hook}\n{required.strip()}"}
        return {"caption": f"{hook}\n{required.strip()}"}
    base = kind.split("+")[0]
    tags = " ".join(HASHTAGS[platform])
    who = f"\n🎮 {credit}" if credit else ""
    if platform == "youtube":
        return {"title": title(kind, clip_id, hook), "description": f"{hook}{who}\n\n{tags}"}
    search = SEARCH_LINES.get(base, SEARCH_LINES["chaos_fail"])
    prompt = _pick(PROMPTS[platform], clip_id, platform)
    return {"caption": f"{search}: {hook}{who}\n{prompt}\n{tags}"}
