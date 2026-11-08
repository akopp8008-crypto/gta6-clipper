"""Text hooks and per-platform captions.

Viewers decide in about one second, so every clip gets a 3-6 word hook
on screen from frame one, and several variants to A/B test.
"""
from __future__ import annotations

import hashlib

HOOKS = {
    "cop_escalation": ["GTA 6 cops are insane", "One bump. Six stars.", "He just wanted to drive",
                       "Vice City PD doesn't play"],
    "chaos_fail": ["He didn't see it coming", "Wait for it…", "This went so wrong",
                   "Worst landing in GTA 6"],
    "npc_weirdness": ["GTA 6 NPCs are unwell", "Wait for the NPC", "Only in Leonida",
                      "Why did she do that"],
    "first_reaction": ["First time in Vice City", "GTA 6 looks unreal", "His face when he saw this",
                       "Nobody expected this detail"],
    "insane_skill": ["This shouldn't be possible", "Cleanest escape in GTA 6", "He actually made it",
                     "Hardest GTA 6 clutch"],
    "wildlife": ["GTA 6 gators are no joke", "The swamp chose violence", "Don't go in the water"],
    "chat_moment": ["Chat called it", "Chat lost it here", "Watch chat explode"],
}

HASHTAGS = {
    "youtube": ["#GTA6", "#Shorts", "#GTAVI"],
    "tiktok": ["#gta6", "#gaming", "#gtavi", "#fyp"],
    "instagram": ["#gta6", "#gaming", "#reels", "#gtavi"],
}


def hook_variants(kind: str, n: int = 3) -> list[str]:
    base = kind.split("+")[0]
    return HOOKS.get(base, HOOKS["chaos_fail"])[:n]


def pick_hook(kind: str, clip_id: str, platform: str, options: list[str] | None = None) -> str:
    """Different hook per platform so the three uploads are not identical copies."""
    options = options or hook_variants(kind, 4)
    h = int(hashlib.sha1(f"{clip_id}:{platform}".encode()).hexdigest(), 16)
    return options[h % len(options)]


def caption(kind: str, clip_id: str, platform: str, credit: str = "",
            hooks: list[str] | None = None, required: str = "") -> dict[str, str]:
    hook = pick_hook(kind, clip_id, platform, hooks)
    if required:
        # Campaign posts: hook line, then the campaign's required block exactly as written.
        if platform == "youtube":
            return {"title": hook[:95], "description": f"{hook}\n{required.strip()}"}
        return {"caption": f"{hook}\n{required.strip()}"}
    tags = " ".join(HASHTAGS[platform])
    who = f" | 🎮 {credit}" if credit else ""
    if platform == "youtube":
        title = f"GTA 6: {hook}"[:95]
        return {"title": title, "description": f"{hook}{who}\n\n{tags}"}
    question = "Would you have survived this?" if "cop" in kind else "Rate this 1-10 👇"
    return {"caption": f"{hook} 😭{who}\n{question}\n{tags}"}
