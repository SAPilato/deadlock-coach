"""Lesson cards. Coaching text only: every game number comes from facts.py.

Rules for this file (checked by tests/test_learn.py):
- title: 2-5 words; summary and points: sentences of 15 words or fewer;
- at most 3 points and 3 facts per lesson;
- topic is one of TOPICS (groups the Learn page);
- every findings rule's `lesson_id` must exist here.
`facts` lists keys resolved by facts.py from game data, measurements or replays.
`try` links to the map layer or Build Lab view that shows the idea.
`icon` names a line icon (frontend components/LessonIcon.tsx); no emojis.
"""
from __future__ import annotations

TOPICS = ["Lane", "Map", "Fights", "Items"]

LESSONS: list[dict] = [
    {
        "id": "wave-management",
        "topic": "Lane",
        "title": "Wave management",
        "icon": "waves",
        "summary": "Control where waves meet. A healthy wave gives you safe souls.",
        "points": [
            "Kill enemy troopers fast when your own wave is small.",
            "Shoot the soul orbs your kills drop. Deny the enemy's orbs.",
            "Push your wave before you leave, so your Guardian stays safe.",
        ],
        "facts": ["wave_timing", "orb_split", "trooper_souls"],
        "try": {"label": "Watch real waves", "href": "/map?mode=waves"},
    },
    {
        "id": "slow-vs-fast-push",
        "topic": "Lane",
        "title": "Slow push vs fast push",
        "icon": "fast-forward",
        "summary": "Choose how fast your wave moves. Each push sets up something different.",
        "points": [
            "Slow push: let waves stack, then hit the Guardian together.",
            "Fast push: clear quickly, then leave to farm or fight.",
            "Push before you go back to base, so you lose fewer souls.",
        ],
        "facts": ["wave_timing", "wave_squad"],
        "try": {"label": "See where waves meet", "href": "/map?mode=waves"},
    },
    {
        "id": "freezing",
        "topic": "Lane",
        "title": "Freezing a wave",
        "icon": "snowflake",
        "summary": "Keep the fight near your Guardian. The enemy must walk up to farm.",
        "points": [
            "Only last-hit. Do not shoot the whole wave down.",
            "Let the enemy wave come to you, near your Guardian.",
            "Punish enemies who walk up to farm.",
        ],
        "facts": ["guardian_hp", "orb_split"],
        "try": {"label": "See where waves meet", "href": "/map?mode=waves"},
    },
    {
        "id": "rotate-after-laning",
        "topic": "Map",
        "title": "When to rotate",
        "icon": "repeat",
        "summary": "After your Guardian falls, the map matters more than your lane.",
        "points": [
            "Push your wave first, then move.",
            "Rotate to the nearest fight, objective or big camp.",
            "Take the zipline for long trips. Run for short hops.",
        ],
        "facts": ["guardian_bounty", "zip_vs_run"],
        "try": {"label": "Compare routes", "href": "/map?mode=route"},
    },
    {
        "id": "waves-and-camps",
        "topic": "Map",
        "title": "Camp and crate rotations",
        "icon": "package",
        "summary": "Farm between waves. Every minute should have a target.",
        "points": [
            "Clear a Haunt camp, then meet your next wave.",
            "Break crates and buff containers on your path.",
            "Never walk far just for one crate.",
        ],
        "facts": ["camp_counts", "crate_counts", "buff_types"],
        "try": {"label": "Show camps and crates", "href": "/map?mode=explore&layers=lanes,camps,crates,statues"},
    },
    {
        "id": "item-timing",
        "topic": "Items",
        "title": "Itemization principles",
        "icon": "shopping-cart",
        "summary": "Spend souls early. Unspent souls do nothing in a fight.",
        "points": [
            "Buy your next item the moment you can afford it.",
            "Spending more in one category gives a bonus.",
            "Counter what hurts you most: bullets or spirit.",
        ],
        "facts": ["item_prices", "weapon_spend_bonus"],
        "try": {"label": "Test items in Build Lab", "href": "/build#shop"},
    },
    {
        "id": "group-for-objectives",
        "topic": "Fights",
        "title": "When to take objectives",
        "icon": "castle",
        "summary": "Objectives win games. Take them when the enemy cannot defend.",
        "points": [
            "After you win a fight, hit the nearest objective.",
            "Push a wave into the objective first.",
            "Never start one while enemies are alive and near.",
        ],
        "facts": ["objective_bounties", "rejuvenator"],
        "try": {"label": "Show objectives", "href": "/map?mode=explore&layers=lanes,objectives,special"},
    },
    {
        "id": "fight-with-team",
        "topic": "Fights",
        "title": "Fight with your team",
        "icon": "handshake",
        "summary": "Many deaths happen alone. Move where your team can help.",
        "points": [
            "Check the minimap before you cross mid.",
            "Go deep only with an ally near.",
            "If you are alone, farm a safe camp instead.",
        ],
        "facts": [],
        "try": {"label": "Practice real moments", "href": "/map?mode=decide"},
    },
    {
        "id": "death-spots",
        "topic": "Fights",
        "title": "Avoid death spots",
        "icon": "skull",
        "summary": "Dying in the same place twice is a pattern. Break it.",
        "points": [
            "Look at your death map after each game.",
            "Take a different path past that spot.",
            "Go there only with two allies.",
        ],
        "facts": [],
        "try": {"label": "See your heatmap", "href": "/map?mode=heatmap"},
    },
    {
        "id": "always-moving",
        "topic": "Map",
        "title": "Always have a target",
        "icon": "footprints",
        "summary": "Every second out of combat should move you toward souls.",
        "points": [
            "Know your next wave, camp or fight.",
            "Use the zipline when it is faster.",
            "Never wait in one spot.",
        ],
        "facts": ["zip_vs_run"],
        "try": {"label": "Compare routes", "href": "/map?mode=route"},
    },
    {
        "id": "urn",
        "topic": "Map",
        "title": "Urn fights",
        "icon": "amphora",
        "summary": "The urn is a big soul swing. Plan for it before it spawns.",
        "points": [
            "Know which side it spawns on next.",
            "Move toward it with your team early.",
            "Guard your carrier to the drop-off.",
        ],
        "facts": ["urn_sites"],
        "try": {"label": "Show urn sites", "href": "/map?mode=explore&layers=lanes,urn"},
    },
]

LESSONS.sort(key=lambda x: TOPICS.index(x["topic"]))  # stable: keeps order within a topic

BY_ID = {lesson["id"]: lesson for lesson in LESSONS}
