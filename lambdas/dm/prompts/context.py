"""Dynamic context builder for the DM."""

from shared.items import ITEM_CATALOG
from shared.models import Character, Message, MessageRole, Session
from shared.utils import calculate_modifier

from .system_prompt import build_system_prompt

# Maximum number of messages to include in history
MAX_MESSAGE_HISTORY = 10


class DMPromptBuilder:
    """Builds prompts for the DM Lambda.

    Handles both cacheable system prompts and dynamic context
    that changes with each request.
    """

    def build_system_prompt(self, campaign: str = "default") -> str:
        """Build the cacheable system prompt (~2000 tokens).

        Args:
            campaign: Campaign setting key

        Returns:
            Complete system prompt string
        """
        return build_system_prompt(campaign)

    def build_context(
        self,
        character: Character,
        session: Session,
        session_data: dict | None = None,
        action: str = "",
    ) -> str:
        """Build the dynamic context section (~500-800 tokens).

        Includes:
        - Character stats block
        - Current location and world state
        - Recent message history (last 10 messages)
        - Pending loot info (if any)
        - Commerce context (if buy/sell action detected)

        Args:
            character: Current player character
            session: Current game session
            session_data: Optional raw session dict for pending_loot access
            action: Player action text for commerce detection

        Returns:
            Context string to append after system prompt
        """
        parts = [
            self._format_character_block(character),
            self._format_world_state(session),
            self._format_message_history(session.message_history),
        ]

        # Add loot context if there's pending loot
        if session_data:
            loot_context = self._format_pending_loot(session_data)
            if loot_context:
                parts.append(loot_context)

        # Add commerce context if commerce action detected
        if action:
            commerce_context = self._format_commerce_context(character, action)
            if commerce_context:
                parts.append(commerce_context)

        return "\n\n".join(parts)

    def build_user_message(self, action: str) -> str:
        """Format the player's action for the API call.

        Args:
            action: Player's action text

        Returns:
            Formatted action string
        """
        return f"[Player Action]: {action}"

    def _format_character_block(self, character: Character) -> str:
        """Format character for context (~150 tokens).

        Args:
            character: Player character

        Returns:
            Formatted character block
        """
        abilities = character.abilities

        # Calculate all modifiers
        str_mod = calculate_modifier(abilities.strength)
        int_mod = calculate_modifier(abilities.intelligence)
        wis_mod = calculate_modifier(abilities.wisdom)
        dex_mod = calculate_modifier(abilities.dexterity)
        con_mod = calculate_modifier(abilities.constitution)
        cha_mod = calculate_modifier(abilities.charisma)

        # Format inventory with item types for clarity
        if character.inventory:
            inventory_items = []
            for item in character.inventory:
                item_type = getattr(item, 'item_type', 'misc')
                inventory_items.append(f"{item.name} ({item_type})")
            inventory_str = ", ".join(inventory_items)
        else:
            inventory_str = "Empty"

        return f"""## CURRENT CHARACTER
Name: {character.name}
Class: {character.character_class.value.title()} Level {character.level}
HP: {character.hp}/{character.max_hp}
Gold: {character.gold} gp
XP: {character.xp}

Abilities: STR {abilities.strength} ({str_mod:+d}), INT {abilities.intelligence} ({int_mod:+d}), WIS {abilities.wisdom} ({wis_mod:+d}), DEX {abilities.dexterity} ({dex_mod:+d}), CON {abilities.constitution} ({con_mod:+d}), CHA {abilities.charisma} ({cha_mod:+d})

Inventory: {inventory_str}"""

    def _format_world_state(self, session: Session) -> str:
        """Format current world state (~100 tokens).

        Args:
            session: Current game session

        Returns:
            Formatted world state block
        """
        # Format world state flags
        if session.world_state:
            flags = ", ".join(f"{k}={v}" for k, v in session.world_state.items())
        else:
            flags = "None"

        return f"""## CURRENT SITUATION
Location: {session.current_location}
Campaign: {session.campaign_setting}
World State: {flags}"""

    def _format_message_history(
        self,
        messages: list[Message],
        max_messages: int = MAX_MESSAGE_HISTORY,
    ) -> str:
        """Format recent message history (~800 tokens max).

        Takes the last N messages to fit within token budget.

        Args:
            messages: Full message history
            max_messages: Maximum messages to include

        Returns:
            Formatted message history block
        """
        if not messages:
            return "## RECENT HISTORY\nNo previous messages."

        # Take last N messages
        recent = messages[-max_messages:]

        lines = ["## RECENT HISTORY"]
        for msg in recent:
            role = "Player" if msg.role == MessageRole.PLAYER else "DM"
            lines.append(f"[{role}]: {msg.content}")

        return "\n".join(lines)

    def _format_pending_loot(self, session_data: dict) -> str:
        """Format pending loot info for DM context.

        The DM's role is NARRATIVE ONLY - the server handles actual loot claiming.

        Args:
            session_data: Raw session dict containing pending_loot

        Returns:
            Formatted loot context block, or no-loot context if empty
        """
        pending = session_data.get("pending_loot")

        # If no pending loot, return NO LOOT context
        if not pending:
            return self._format_no_loot_context()

        gold = pending.get("gold", 0)
        items = pending.get("items", [])

        # If pending exists but is empty, return NO LOOT context
        if not gold and not items:
            return self._format_no_loot_context()

        lines = [
            "## LOOT AVAILABLE",
            "The player has defeated enemies. Loot is available:",
        ]

        if gold > 0:
            lines.append(f"- Gold: {gold}")

        if items:
            # Convert item IDs to display names
            item_names = []
            for item_id in items:
                if item_id in ITEM_CATALOG:
                    item_names.append(ITEM_CATALOG[item_id].name)
                else:
                    item_names.append(item_id.replace("_", " ").title())
            lines.append(f"- Items: {', '.join(item_names)}")

        lines.extend([
            "",
            "When the player searches (variations: 'search', 'loot', 'check bodies', 'take their stuff'):",
            "- Narrate them finding these items",
            "- The SERVER handles adding items to inventory (you do NOT output gold_delta or inventory_add)",
            "",
            "Do NOT give loot until player explicitly searches.",
            "If player declines to search, acknowledge their choice.",
        ])

        return "\n".join(lines)

    def _format_no_loot_context(self) -> str:
        """Format context when no loot is available.

        Tells the DM to narrate finding nothing when player searches.

        Returns:
            Formatted no-loot context block
        """
        return """## NO LOOT AVAILABLE
There is no loot available in this area.
If the player searches, narrate them finding nothing of value.
Do NOT invent items or gold - the server controls all acquisition."""

    def _format_commerce_context(self, character: Character, action: str) -> str | None:
        """Format commerce context when buy/sell action detected.

        Args:
            character: Player character
            action: Player action text

        Returns:
            Commerce context block or None if not a commerce action
        """
        from shared.actions import is_buy_action, is_sell_action

        is_sell = is_sell_action(action)
        is_buy = is_buy_action(action)

        if not is_sell and not is_buy:
            return None

        gold = character.gold

        lines = ["## COMMERCE CONTEXT"]
        lines.append(f"Player has {gold} gold.")

        if is_sell and character.inventory:
            lines.append("")
            lines.append("SELLABLE ITEMS (50% value, minimum 1 gold):")
            for item in character.inventory:
                item_id = getattr(item, "item_id", None) or item.name.lower().replace(" ", "_")
                item_def = ITEM_CATALOG.get(item_id)
                if item_def:
                    sell_price = max(1, item_def.value // 2)
                    lines.append(f"- {item_def.name} ({item_def.id}): {sell_price} gold")
                else:
                    lines.append(f"- {item.name}: 1 gold (unknown item)")

        if is_buy:
            lines.append("")
            lines.append(f"Player can afford items up to {gold} gold.")
            lines.append("")
            lines.append("COMMON SHOP PRICES:")
            lines.append("- torch: 1 gold")
            lines.append("- dagger: 3 gold")
            lines.append("- rations: 5 gold")
            lines.append("- sword: 10 gold")
            lines.append("- shield: 10 gold")
            lines.append("- leather_armor: 10 gold")
            lines.append("- chain_mail: 40 gold")
            lines.append("- potion_healing: 50 gold")

        return "\n".join(lines)
