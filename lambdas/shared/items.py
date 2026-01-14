"""Item catalog and starting equipment for Chaos Dungeon.

Implements server-side inventory tracking with BECMI-accurate items.
Items can only be acquired through validated server-side actions.
"""

from enum import Enum

from pydantic import BaseModel, Field


class ItemType(str, Enum):
    """Types of items in the game."""

    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"
    QUEST = "quest"
    MISC = "misc"


class ItemDefinition(BaseModel):
    """Item template from the catalog."""

    id: str  # Unique item ID (e.g., "potion_healing")
    name: str  # Display name
    item_type: ItemType
    description: str = ""
    # Combat properties
    damage_dice: str | None = None  # e.g., "1d8" for longsword
    ac_bonus: int = 0  # For armor/shields
    # Consumable properties
    healing: int = 0  # HP restored when used
    uses: int = 1  # Number of uses (consumables)
    # Economy
    value: int = 0  # Base value in gold


class InventoryItem(BaseModel):
    """Item instance in a character's inventory."""

    item_id: str  # References ItemDefinition.id
    name: str  # Display name (copied from definition)
    quantity: int = Field(default=1, ge=1)
    # Denormalized for display
    item_type: str  # Stored as string for JSON serialization
    description: str = ""


# =============================================================================
# ITEM CATALOG - All items that can exist in the game
# =============================================================================

ITEM_CATALOG: dict[str, ItemDefinition] = {
    # Weapons
    "sword": ItemDefinition(
        id="sword",
        name="Sword",
        item_type=ItemType.WEAPON,
        damage_dice="1d8",
        value=10,
        description="A trusty steel sword.",
    ),
    "dagger": ItemDefinition(
        id="dagger",
        name="Dagger",
        item_type=ItemType.WEAPON,
        damage_dice="1d4",
        value=3,
        description="A sharp dagger, favored by thieves.",
    ),
    "mace": ItemDefinition(
        id="mace",
        name="Mace",
        item_type=ItemType.WEAPON,
        damage_dice="1d6",
        value=5,
        description="A heavy mace blessed for holy work.",
    ),
    "staff": ItemDefinition(
        id="staff",
        name="Staff",
        item_type=ItemType.WEAPON,
        damage_dice="1d4",
        value=1,
        description="A wooden staff, also useful as a focus.",
    ),
    # Armor
    "chain_mail": ItemDefinition(
        id="chain_mail",
        name="Chain Mail",
        item_type=ItemType.ARMOR,
        ac_bonus=4,
        value=40,
        description="Interlocking metal rings providing solid protection.",
    ),
    "leather_armor": ItemDefinition(
        id="leather_armor",
        name="Leather Armor",
        item_type=ItemType.ARMOR,
        ac_bonus=2,
        value=10,
        description="Lightweight leather protection.",
    ),
    "shield": ItemDefinition(
        id="shield",
        name="Shield",
        item_type=ItemType.ARMOR,
        ac_bonus=1,
        value=10,
        description="A sturdy wooden shield.",
    ),
    "robes": ItemDefinition(
        id="robes",
        name="Robes",
        item_type=ItemType.ARMOR,
        ac_bonus=0,
        value=5,
        description="Simple cloth robes favored by magic users.",
    ),
    # Consumables
    "potion_healing": ItemDefinition(
        id="potion_healing",
        name="Potion of Healing",
        item_type=ItemType.CONSUMABLE,
        healing=8,  # Rolls 1d8 in practice
        uses=1,
        value=50,
        description="A red potion that restores 1d8 HP.",
    ),
    "rations": ItemDefinition(
        id="rations",
        name="Rations",
        item_type=ItemType.CONSUMABLE,
        uses=7,
        value=5,
        description="A week's worth of trail rations.",
    ),
    "torch": ItemDefinition(
        id="torch",
        name="Torch",
        item_type=ItemType.MISC,
        value=1,
        description="Provides light for about an hour.",
    ),
    # Tools
    "thieves_tools": ItemDefinition(
        id="thieves_tools",
        name="Thieves' Tools",
        item_type=ItemType.MISC,
        value=25,
        description="Lockpicks and other tools of the trade.",
    ),
    "holy_symbol": ItemDefinition(
        id="holy_symbol",
        name="Holy Symbol",
        item_type=ItemType.MISC,
        value=25,
        description="A sacred symbol of your deity.",
    ),
    "spellbook": ItemDefinition(
        id="spellbook",
        name="Spellbook",
        item_type=ItemType.MISC,
        value=50,
        description="Contains your memorized spells.",
    ),
    "backpack": ItemDefinition(
        id="backpack",
        name="Backpack",
        item_type=ItemType.MISC,
        value=5,
        description="Carries your adventuring gear.",
    ),
    # Quest items (predefined common ones)
    "rusty_key": ItemDefinition(
        id="rusty_key",
        name="Rusty Key",
        item_type=ItemType.QUEST,
        value=0,
        description="An old, corroded key.",
    ),
    "golden_key": ItemDefinition(
        id="golden_key",
        name="Golden Key",
        item_type=ItemType.QUEST,
        value=0,
        description="A gleaming golden key.",
    ),
    "ancient_scroll": ItemDefinition(
        id="ancient_scroll",
        name="Ancient Scroll",
        item_type=ItemType.QUEST,
        value=0,
        description="A scroll covered in mysterious writing.",
    ),
}

# =============================================================================
# STARTING EQUIPMENT BY CLASS (BECMI-accurate)
# =============================================================================

STARTING_EQUIPMENT: dict[str, list[str]] = {
    "fighter": ["sword", "shield", "chain_mail", "backpack", "rations", "torch"],
    "thief": ["dagger", "leather_armor", "thieves_tools", "backpack", "rations", "torch"],
    "cleric": ["mace", "shield", "chain_mail", "holy_symbol", "backpack", "rations"],
    "magic_user": ["dagger", "staff", "spellbook", "robes", "backpack", "rations"],
}

# =============================================================================
# ITEM ALIASES - Common variations that map to catalog items
# =============================================================================

ITEM_ALIASES: dict[str, str] = {
    # Healing potions
    "healing potion": "potion_healing",
    "health potion": "potion_healing",
    "potion of health": "potion_healing",
    "red potion": "potion_healing",
    "hp potion": "potion_healing",
    # Keys (default to rusty for generic)
    "key": "rusty_key",
    "old key": "rusty_key",
    "iron key": "rusty_key",
    "bronze key": "rusty_key",
    # Scrolls
    "scroll": "ancient_scroll",
    "old scroll": "ancient_scroll",
    "parchment": "ancient_scroll",
    # Weapons
    "longsword": "sword",
    "short sword": "sword",
    "shortsword": "sword",
    "blade": "sword",
    "knife": "dagger",
    "club": "mace",
    "cudgel": "mace",
    "walking stick": "staff",
    "quarterstaff": "staff",
    # Armor
    "chainmail": "chain_mail",
    "mail": "chain_mail",
    "leather": "leather_armor",
    "leathers": "leather_armor",
    # Other
    "food": "rations",
    "provisions": "rations",
    "light": "torch",
    "lantern": "torch",
    "lockpicks": "thieves_tools",
    "picks": "thieves_tools",
    "holy relic": "holy_symbol",
    "symbol": "holy_symbol",
}

# =============================================================================
# QUEST KEYWORDS - Items containing these words can be dynamically created
# =============================================================================

QUEST_KEYWORDS = [
    "key",
    "letter",
    "note",
    "scroll",
    "ring",
    "amulet",
    "token",
    "locket",
    "pendant",
    "coin",
    "gem",
    "map",
    "journal",
    "book",
    "vial",
    "pouch",
    "badge",
    "seal",
    "charm",
    "relic",
    "artifact",
    "orb",
    "crystal",
    "skull",
    "bone",
    "feather",
    "claw",
    "fang",
    "talisman",
    "idol",
    "medallion",
    "brooch",
    "crown",
    "scepter",
    "rod",
    "wand",
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def find_item_by_name(name: str) -> ItemDefinition | None:
    """Find item by name (case-insensitive, fuzzy match).

    Search order:
    1. Exact match on item name
    2. Exact match on item ID
    3. Partial match (catalog item name contains search term)
    4. Alias lookup
    5. Dynamic quest item creation for narrative items

    Args:
        name: Item name to search for

    Returns:
        ItemDefinition if found, None otherwise
    """
    if not name or not name.strip():
        return None

    normalized = name.lower().strip()

    # 1. Exact match on name
    for item_def in ITEM_CATALOG.values():
        if item_def.name.lower() == normalized:
            return item_def

    # 2. Exact match on ID
    if normalized in ITEM_CATALOG:
        return ITEM_CATALOG[normalized]

    # 3. Partial match (catalog name contains search term)
    for item_def in ITEM_CATALOG.values():
        if normalized in item_def.name.lower():
            return item_def

    # 4. Check aliases
    if normalized in ITEM_ALIASES:
        alias_id = ITEM_ALIASES[normalized]
        return ITEM_CATALOG.get(alias_id)

    # 5. Dynamic quest item creation for narrative flexibility
    # If the item name contains a quest keyword, create a generic quest entry
    for keyword in QUEST_KEYWORDS:
        if keyword in normalized:
            # Create dynamic quest item with sanitized ID
            sanitized_id = normalized.replace(" ", "_").replace("'", "")[:30]
            return ItemDefinition(
                id=f"quest_{sanitized_id}",
                name=name.title(),
                item_type=ItemType.QUEST,
                value=0,
                description=f"A mysterious {name.lower()}.",
            )

    return None


def get_starting_equipment(character_class: str) -> list[dict]:
    """Get starting equipment for a character class.

    Args:
        character_class: One of fighter, thief, cleric, magic_user

    Returns:
        List of inventory item dicts ready for character creation
    """
    equipment_ids = STARTING_EQUIPMENT.get(character_class.lower(), [])
    inventory = []

    for item_id in equipment_ids:
        if item_id in ITEM_CATALOG:
            item_def = ITEM_CATALOG[item_id]
            inventory.append({
                "item_id": item_id,
                "name": item_def.name,
                "quantity": 1,
                "item_type": item_def.item_type.value,
                "description": item_def.description,
            })

    return inventory
