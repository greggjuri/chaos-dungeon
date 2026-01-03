"""Campaign-specific prompts for the DM system prompt."""

CAMPAIGN_PROMPTS: dict[str, str] = {
    "default": """## CAMPAIGN: DEFAULT (Classic Adventure)
Setting: The village of Millbrook and surrounding wilderness
Tone: Classic fantasy adventure with dark undertones
Opening: The player arrives at The Rusty Tankard tavern seeking adventure

The village of Millbrook is a modest settlement at the edge of civilization. The Rusty Tankard serves as the social hub where adventurers gather, rumors spread, and quests begin. The surrounding wilderness holds ancient ruins, monster lairs, and forgotten treasures. The local lord pays well for those brave enough to deal with threats to the village.""",
    "dark_forest": """## CAMPAIGN: DARK_FOREST
Setting: The haunted Dark Forest, once home to elves now corrupted
Tone: Survival horror, isolation, supernatural threats
Opening: The player stands at the forest's edge as mist curls around dead trees

The Dark Forest was once a magnificent elven realm, but something corrupted it centuries ago. Now it's a place of eternal twilight where the trees themselves seem malevolent. Strange sounds echo through the mist, and those who enter rarely return. The few survivors speak of shadow creatures, whispering voices, and an ancient evil at the forest's heart. Only the desperate or foolish venture within.""",
    "cursed_castle": """## CAMPAIGN: CURSED_CASTLE
Setting: Castle Ravenmoor, domain of the vampire lord
Tone: Gothic horror, undead threats, tragic history
Opening: The crumbling gatehouse looms overhead, gargoyles watching silently

Castle Ravenmoor stands atop a craggy peak, shrouded in perpetual storm clouds. Once home to a noble family, it fell to darkness when Lord Ravenmoor made a pact with entities beyond mortal comprehension. Now undead servants patrol its halls, and the vampire lord holds court in the great hall. The villagers below live in terror, offering sacrifices to keep the horrors at bay. Rumors speak of treasures in the castle's depths—and a way to break the curse.""",
    "forgotten_mines": """## CAMPAIGN: FORGOTTEN_MINES
Setting: The Deepholm mines, abandoned after something was unearthed
Tone: Dungeon crawl, ancient evil, treasure hunting
Opening: Torchlight flickers at the mine entrance, darkness beyond

The Deepholm mines once produced precious gems and rare metals, enriching the dwarven clan that worked them. Then the miners dug too deep and unearthed something ancient. The dwarves sealed the deepest tunnels and abandoned the mines entirely. Now treasure hunters and adventurers seek the legendary riches left behind, but few return. Those who do speak of twisted creatures, strange glowing crystals, and whispers in the dark.""",
}


def get_campaign_prompt(campaign: str) -> str:
    """Get the campaign prompt, falling back to default if not found."""
    return CAMPAIGN_PROMPTS.get(campaign, CAMPAIGN_PROMPTS["default"])
