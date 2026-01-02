"""DM service for processing player actions."""

from datetime import UTC, datetime

from aws_lambda_powertools import Logger

from dm.claude_client import ClaudeClient
from dm.models import ActionResponse, CharacterSnapshot, DMResponse
from dm.parser import parse_dm_response
from dm.prompts import DMPromptBuilder
from shared.db import DynamoDBClient, convert_floats_to_decimal
from shared.exceptions import GameStateError, NotFoundError
from shared.models import AbilityScores, Character, Item, Message, Session
from shared.secrets import get_claude_api_key

logger = Logger(child=True)

MAX_MESSAGE_HISTORY = 50


class DMService:
    """Service for processing player actions through Claude."""

    def __init__(
        self, db: DynamoDBClient, claude_client: ClaudeClient | None = None
    ):
        """Initialize DM service.

        Args:
            db: DynamoDB client for game state
            claude_client: Optional pre-configured Claude client (for testing)
        """
        self.db = db
        self.claude_client = claude_client
        self.prompt_builder = DMPromptBuilder()

    def _get_claude_client(self) -> ClaudeClient:
        """Lazy initialization of Claude client."""
        if self.claude_client is None:
            api_key = get_claude_api_key()
            self.claude_client = ClaudeClient(api_key)
        return self.claude_client

    def process_action(
        self,
        session_id: str,
        user_id: str,
        action: str,
    ) -> ActionResponse:
        """Process a player action and return the DM response.

        Args:
            session_id: Session UUID
            user_id: User UUID
            action: Player action text

        Returns:
            ActionResponse with narrative, state changes, and character state

        Raises:
            NotFoundError: Session or character not found
            GameStateError: Session has ended
        """
        # Load session
        session_pk = f"USER#{user_id}"
        session_sk = f"SESS#{session_id}"
        session = self.db.get_item(session_pk, session_sk)
        if not session:
            raise NotFoundError("session", session_id)

        # Check if session has ended
        if session.get("status") == "ended":
            raise GameStateError(
                "Session has ended",
                current_state=session.get("ended_reason", "unknown"),
            )

        # Load character
        character_id = session["character_id"]
        char_pk = f"USER#{user_id}"
        char_sk = f"CHAR#{character_id}"
        character = self.db.get_item(char_pk, char_sk)
        if not character:
            raise NotFoundError("character", character_id)

        logger.info(
            "Processing player action",
            extra={
                "session_id": session_id,
                "character_id": character_id,
                "action_length": len(action),
            },
        )

        # Build prompts
        campaign = session.get("campaign_setting", "default")
        system_prompt = self.prompt_builder.build_system_prompt(campaign)

        # Build character model for context
        char_model = Character(
            character_id=character_id,
            user_id=user_id,
            name=character["name"],
            character_class=character["character_class"],
            level=character["level"],
            xp=character["xp"],
            hp=character["hp"],
            max_hp=character["max_hp"],
            gold=character["gold"],
            abilities=AbilityScores(**character["stats"]),
            inventory=[
                Item(**item) if isinstance(item, dict) else Item(name=item)
                for item in character.get("inventory", [])
            ],
        )

        # Build session model for context
        sess_model = Session(
            session_id=session_id,
            user_id=user_id,
            character_id=character_id,
            campaign_setting=campaign,
            current_location=session.get("current_location", "Unknown"),
            world_state=session.get("world_state", {}),
            message_history=[
                Message(**m) for m in session.get("message_history", [])
            ],
        )

        context = self.prompt_builder.build_context(char_model, sess_model)

        # Call Claude
        client = self._get_claude_client()
        raw_response = client.send_action(system_prompt, context, action)

        # Parse response
        dm_response = parse_dm_response(raw_response)

        # Apply state changes
        character, session = self._apply_state_changes(
            character, session, dm_response
        )

        # Update message history
        session = self._append_messages(session, action, dm_response.narrative)

        # Check for character death
        character_dead = False
        session_ended = False
        if character["hp"] <= 0:
            character_dead = True
            session_ended = True
            session["status"] = "ended"
            session["ended_reason"] = "character_death"
            logger.info(
                "Character died",
                extra={"character_id": character_id, "session_id": session_id},
            )

        # Save updates to DynamoDB
        now = datetime.now(UTC).isoformat()
        character["updated_at"] = now
        session["updated_at"] = now

        # Convert floats to Decimal for DynamoDB compatibility
        char_data = convert_floats_to_decimal(
            {k: v for k, v in character.items() if k not in ("PK", "SK")}
        )
        session_data = convert_floats_to_decimal(
            {k: v for k, v in session.items() if k not in ("PK", "SK")}
        )

        self.db.put_item(char_pk, char_sk, char_data)
        self.db.put_item(session_pk, session_sk, session_data)

        # Build response
        inventory_names = [
            item["name"] if isinstance(item, dict) else item
            for item in character.get("inventory", [])
        ]

        return ActionResponse(
            narrative=dm_response.narrative,
            state_changes=dm_response.state_changes,
            dice_rolls=dm_response.dice_rolls,
            combat_active=dm_response.combat_active,
            enemies=dm_response.enemies,
            character=CharacterSnapshot(
                hp=character["hp"],
                max_hp=character["max_hp"],
                xp=character["xp"],
                gold=character["gold"],
                level=character["level"],
                inventory=inventory_names,
            ),
            character_dead=character_dead,
            session_ended=session_ended,
        )

    def _apply_state_changes(
        self,
        character: dict,
        session: dict,
        dm_response: DMResponse,
    ) -> tuple[dict, dict]:
        """Apply state changes from DM response.

        Args:
            character: Character dict from DynamoDB
            session: Session dict from DynamoDB
            dm_response: Parsed DM response

        Returns:
            Updated (character, session) tuple
        """
        state = dm_response.state_changes

        # Update character HP with bounds
        new_hp = character["hp"] + state.hp_delta
        character["hp"] = max(0, min(new_hp, character["max_hp"]))

        # Update gold (can't go negative)
        character["gold"] = max(0, character["gold"] + state.gold_delta)

        # Update XP
        character["xp"] = character["xp"] + state.xp_delta

        # Inventory changes - handle both Item objects and strings
        inventory = character.get("inventory", [])
        inventory_names = [
            item["name"] if isinstance(item, dict) else item for item in inventory
        ]

        for item_name in state.inventory_add:
            if item_name not in inventory_names:
                inventory.append({"name": item_name, "quantity": 1, "weight": 0.0})
                inventory_names.append(item_name)

        for item_name in state.inventory_remove:
            # Find and remove item
            inventory = [
                item
                for item in inventory
                if (item["name"] if isinstance(item, dict) else item) != item_name
            ]

        character["inventory"] = inventory

        # Update session location
        if state.location:
            session["current_location"] = state.location

        # Merge world state flags
        if state.world_state:
            session.setdefault("world_state", {}).update(state.world_state)

        # Track combat state
        session["combat_active"] = dm_response.combat_active
        if dm_response.enemies:
            session["enemies"] = [e.model_dump() for e in dm_response.enemies]
        elif not dm_response.combat_active:
            session["enemies"] = []

        return character, session

    def _append_messages(
        self,
        session: dict,
        action: str,
        narrative: str,
    ) -> dict:
        """Append player action and DM response to message history.

        Args:
            session: Session dict from DynamoDB
            action: Player's action text
            narrative: DM's narrative response

        Returns:
            Updated session dict
        """
        now = datetime.now(UTC).isoformat()

        history = session.get("message_history", [])

        history.append(
            {
                "role": "player",
                "content": action,
                "timestamp": now,
            }
        )
        history.append(
            {
                "role": "dm",
                "content": narrative,
                "timestamp": now,
            }
        )

        # Trim to max messages
        if len(history) > MAX_MESSAGE_HISTORY:
            history = history[-MAX_MESSAGE_HISTORY:]

        session["message_history"] = history
        return session
