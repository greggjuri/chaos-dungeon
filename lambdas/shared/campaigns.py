"""Campaign setting definitions for game sessions."""

CAMPAIGN_SETTINGS: dict[str, dict] = {
    "default": {
        "name": "Classic Adventure",
        "starting_location": "The Rusty Tankard tavern in Millbrook village",
        "theme": "Classic fantasy, open-ended exploration",
    },
    "dark_forest": {
        "name": "The Dark Forest",
        "starting_location": "The edge of the Dark Forest, where the road ends",
        "theme": "Horror and survival in haunted woods",
    },
    "cursed_castle": {
        "name": "The Cursed Castle",
        "starting_location": "The crumbling gatehouse of Castle Ravenmoor",
        "theme": "Gothic horror with undead threats",
    },
    "forgotten_mines": {
        "name": "The Forgotten Mines",
        "starting_location": "The abandoned entrance to the Deepholm mines",
        "theme": "Dungeon crawl with ancient treasures",
    },
}


def get_starting_location(campaign: str) -> str:
    """Get the starting location for a campaign setting.

    Args:
        campaign: Campaign setting key

    Returns:
        The starting location description
    """
    return CAMPAIGN_SETTINGS.get(campaign, CAMPAIGN_SETTINGS["default"])["starting_location"]


def get_opening_message(campaign: str, character_name: str) -> str:
    """Generate the initial DM message for a new session.

    Args:
        campaign: Campaign setting key
        character_name: Name of the player's character

    Returns:
        Opening narrative from the DM
    """
    location = get_starting_location(campaign)
    return f"You are {character_name}. {location}. What do you do?"
