"""Dynamic context builder for the DM."""

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
    ) -> str:
        """Build the dynamic context section (~500-800 tokens).

        Includes:
        - Character stats block
        - Current location and world state
        - Recent message history (last 10 messages)

        Args:
            character: Current player character
            session: Current game session

        Returns:
            Context string to append after system prompt
        """
        parts = [
            self._format_character_block(character),
            self._format_world_state(session),
            self._format_message_history(session.message_history),
        ]
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
