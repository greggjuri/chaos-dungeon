"""DM service for processing player actions."""

import os
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from aws_lambda_powertools import Logger

from dm.bedrock_client import MistralResponse
from dm.bestiary import spawn_enemy
from dm.combat import CombatResolver
from dm.models import (
    ActionResponse,
    CharacterSnapshot,
    CombatEnemy,
    CombatState,
    DiceRoll,
    DMResponse,
    Enemy,
    StateChanges,
)
from dm.parser import parse_dm_response
from dm.prompts import DMPromptBuilder
from dm.prompts.combat_prompt import build_combat_outcome_prompt
from shared.db import DynamoDBClient, convert_floats_to_decimal
from shared.dice import roll as roll_dice_notation
from shared.exceptions import GameStateError, NotFoundError
from shared.models import AbilityScores, Character, Item, Message, Session
from shared.token_tracker import TokenTracker

logger = Logger(child=True)

MAX_MESSAGE_HISTORY = 50

# Model provider: "mistral" (Bedrock) or "claude" (Anthropic API)
MODEL_PROVIDER = os.environ.get("MODEL_PROVIDER", "mistral")


class AIClient(Protocol):
    """Protocol for AI client interface (Claude or Bedrock)."""

    def send_action(
        self,
        system_prompt: str,
        context: str,
        action: str,
    ) -> MistralResponse:
        """Send player action and return response with usage stats."""
        ...


class DMService:
    """Service for processing player actions through AI (Claude or Mistral)."""

    def __init__(
        self,
        db: DynamoDBClient,
        ai_client: AIClient | None = None,
        token_tracker: TokenTracker | None = None,
    ):
        """Initialize DM service.

        Args:
            db: DynamoDB client for game state
            ai_client: Optional pre-configured AI client (for testing)
            token_tracker: Optional token tracker for usage recording
        """
        self.db = db
        self._ai_client = ai_client
        self._token_tracker = token_tracker
        self.prompt_builder = DMPromptBuilder()
        self.combat_resolver = CombatResolver()

    def _get_ai_client(self) -> AIClient:
        """Lazy initialization of AI client based on MODEL_PROVIDER."""
        if self._ai_client is None:
            if MODEL_PROVIDER == "mistral":
                from dm.bedrock_client import BedrockClient

                self._ai_client = BedrockClient()
                logger.info("Using Mistral via Bedrock")
            else:
                from dm.claude_client import ClaudeClient
                from shared.secrets import get_claude_api_key

                api_key = get_claude_api_key()
                self._ai_client = ClaudeClient(api_key)
                logger.info("Using Claude via Anthropic API")
        return self._ai_client

    def _record_usage(self, session_id: str, response: MistralResponse) -> None:
        """Record token usage from AI response.

        Args:
            session_id: Session ID for per-session tracking
            response: AI response with token counts
        """
        if self._token_tracker is None:
            return

        try:
            self._token_tracker.increment_usage(
                session_id=session_id,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            )
        except Exception as e:
            # Don't fail the request if usage tracking fails
            logger.warning(
                "Failed to record token usage",
                extra={"error": str(e), "session_id": session_id},
            )

    def process_action(
        self,
        session_id: str,
        user_id: str,
        action: str,
    ) -> ActionResponse:
        """Process a player action and return the DM response.

        Routes to combat or normal action processing based on combat state.

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
                "combat_active": session.get("combat_state", {}).get("active", False),
            },
        )

        # Check if we're in active combat
        combat_state = session.get("combat_state", {})
        if combat_state.get("active"):
            response = self._process_combat_action(session, character, action, user_id, session_id)
        else:
            response = self._process_normal_action(session, character, action, user_id, session_id)

        # Save updates to DynamoDB
        now = datetime.now(UTC).isoformat()
        character["updated_at"] = now
        session["updated_at"] = now

        char_data = convert_floats_to_decimal(
            {k: v for k, v in character.items() if k not in ("PK", "SK")}
        )
        session_data = convert_floats_to_decimal(
            {k: v for k, v in session.items() if k not in ("PK", "SK")}
        )

        self.db.put_item(char_pk, char_sk, char_data)
        self.db.put_item(session_pk, session_sk, session_data)

        return response

    def _process_combat_action(
        self,
        session: dict,
        character: dict,
        action: str,
        user_id: str,
        session_id: str,
    ) -> ActionResponse:
        """Process an action during active combat.

        Combat is resolved mechanically on the server, then Claude narrates.

        Args:
            session: Session dict from DynamoDB
            character: Character dict from DynamoDB
            action: Player's action text
            user_id: User UUID
            session_id: Session UUID

        Returns:
            ActionResponse with combat results
        """
        # Load combat state
        combat_state_dict = session.get("combat_state", {})
        combat_enemies_data = session.get("combat_enemies", [])

        combat_state = CombatState(**combat_state_dict)
        combat_state.round += 1

        combat_enemies = [CombatEnemy(**e) for e in combat_enemies_data]

        logger.info(
            "Resolving combat round",
            extra={
                "round": combat_state.round,
                "enemies": len(combat_enemies),
            },
        )

        # Resolve combat mechanically
        round_result = self.combat_resolver.resolve_combat_round(
            character, combat_state, combat_enemies
        )

        # Build outcome prompt for Claude - it can only narrate, not decide
        outcome_prompt = build_combat_outcome_prompt(
            round_result,
            character["name"],
            character["max_hp"],
        )

        # Get narrative from Claude
        campaign = session.get("campaign_setting", "default")
        system_prompt = self.prompt_builder.build_system_prompt(campaign)
        client = self._get_ai_client()
        ai_response = client.send_action(system_prompt, outcome_prompt, action)

        # Record token usage
        self._record_usage(session_id, ai_response)

        # Parse response (only for narrative, state is from combat)
        dm_response = parse_dm_response(ai_response.text)

        # Apply XP from combat
        character["xp"] += round_result.xp_gained

        # Build dice rolls from attack results
        dice_rolls = self._build_combat_dice_rolls(round_result)

        # Update combat state in session
        if round_result.combat_ended:
            session["combat_state"] = {"active": False, "round": 0}
            session["combat_enemies"] = []
            logger.info(
                "Combat ended",
                extra={"player_dead": round_result.player_dead},
            )
        else:
            session["combat_state"] = combat_state.model_dump()
            session["combat_enemies"] = [e.model_dump() for e in combat_enemies if e.hp > 0]

        # Update message history
        session = self._append_messages(session, action, dm_response.narrative)

        # Check for character death
        character_dead = round_result.player_dead
        session_ended = round_result.player_dead
        if character_dead:
            session["status"] = "ended"
            session["ended_reason"] = "character_death"
            logger.info(
                "Character died in combat",
                extra={"character": character["name"]},
            )

        # Build response
        inventory_names = [
            item["name"] if isinstance(item, dict) else item
            for item in character.get("inventory", [])
        ]

        # Convert remaining enemies to Enemy models for response
        remaining_enemies = [
            Enemy(name=e.name, hp=e.hp, ac=e.ac, max_hp=e.max_hp)
            for e in round_result.enemies_remaining
        ]

        return ActionResponse(
            narrative=dm_response.narrative,
            state_changes=StateChanges(
                hp_delta=round_result.player_hp - character.get("max_hp", 0),
                xp_delta=round_result.xp_gained,
            ),
            dice_rolls=dice_rolls,
            combat_active=not round_result.combat_ended,
            enemies=remaining_enemies,
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

    def _process_normal_action(
        self,
        session: dict,
        character: dict,
        action: str,
        user_id: str,
        session_id: str,
    ) -> ActionResponse:
        """Process a normal (non-combat) action.

        Claude handles narrative and may initiate combat.

        Args:
            session: Session dict from DynamoDB
            character: Character dict from DynamoDB
            action: Player's action text
            user_id: User UUID
            session_id: Session UUID

        Returns:
            ActionResponse with narrative and state changes
        """
        character_id = session["character_id"]
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
            message_history=[Message(**m) for m in session.get("message_history", [])],
        )

        context = self.prompt_builder.build_context(char_model, sess_model)

        # Call Claude
        client = self._get_ai_client()
        ai_response = client.send_action(system_prompt, context, action)

        # Record token usage
        self._record_usage(session_id, ai_response)

        # Parse response
        dm_response = parse_dm_response(ai_response.text)

        # Debug logging for combat initiation
        logger.debug(
            "Parsed DM response for combat check",
            extra={
                "combat_active": dm_response.combat_active,
                "enemies_count": len(dm_response.enemies) if dm_response.enemies else 0,
                "enemies": [e.model_dump() for e in dm_response.enemies]
                if dm_response.enemies
                else [],
            },
        )

        # Check if Claude initiated combat
        # Note: If enemies are present, we should initiate combat even if combat_active is False
        should_initiate_combat = dm_response.enemies and len(dm_response.enemies) > 0

        logger.info(
            "Combat initiation check",
            extra={
                "should_initiate": should_initiate_combat,
                "combat_active_from_claude": dm_response.combat_active,
                "has_enemies": bool(dm_response.enemies),
            },
        )

        if should_initiate_combat:
            self._initiate_combat(session, dm_response.enemies)

        # Apply state changes
        character, session = self._apply_state_changes(character, session, dm_response)

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

        # Build response
        inventory_names = [
            item["name"] if isinstance(item, dict) else item
            for item in character.get("inventory", [])
        ]

        # Use session combat state (set by _initiate_combat) rather than Claude's response
        is_combat_active = session.get("combat_state", {}).get("active", False)

        # Get enemies from session if combat is active, otherwise from Claude's response
        if is_combat_active:
            combat_enemies_data = session.get("combat_enemies", [])
            response_enemies = [
                Enemy(name=e["name"], hp=e["hp"], ac=e["ac"], max_hp=e.get("max_hp", e["hp"]))
                for e in combat_enemies_data
            ]
        else:
            response_enemies = dm_response.enemies

        logger.debug(
            "Building action response",
            extra={
                "combat_active": is_combat_active,
                "enemies_count": len(response_enemies) if response_enemies else 0,
            },
        )

        return ActionResponse(
            narrative=dm_response.narrative,
            state_changes=dm_response.state_changes,
            dice_rolls=dm_response.dice_rolls,
            combat_active=is_combat_active,
            enemies=response_enemies,
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

    def _initiate_combat(self, session: dict, enemies: list[Enemy]) -> None:
        """Start combat with enemies from Claude's response.

        Args:
            session: Session dict to update
            enemies: Enemies from Claude's response
        """
        logger.info(
            "Initiating combat",
            extra={
                "enemies_from_claude": [e.model_dump() for e in enemies],
            },
        )

        combat_enemies = []
        for enemy in enemies:
            try:
                # Try to spawn from bestiary
                spawned = spawn_enemy(enemy.name)
                combat_enemies.append(spawned.model_dump())
                logger.debug(
                    "Spawned enemy from bestiary",
                    extra={"enemy_name": enemy.name, "spawned": spawned.model_dump()},
                )
            except ValueError:
                # Unknown enemy - use stats from Claude's response
                fallback_enemy = {
                    "id": str(uuid4()),
                    "name": enemy.name,
                    "hp": enemy.hp,
                    "max_hp": enemy.max_hp or enemy.hp,
                    "ac": enemy.ac,
                    "attack_bonus": 1,
                    "damage_dice": "1d6",
                    "xp_value": max(10, enemy.hp * 2),
                }
                combat_enemies.append(fallback_enemy)
                logger.debug(
                    "Using Claude stats for unknown enemy",
                    extra={"enemy_name": enemy.name, "fallback": fallback_enemy},
                )

        # Roll initiative
        player_init, _ = roll_dice_notation("1d6")
        enemy_init, _ = roll_dice_notation("1d6")

        session["combat_state"] = {
            "active": True,
            "round": 0,
            "player_initiative": player_init,
            "enemy_initiative": enemy_init,
        }
        session["combat_enemies"] = combat_enemies

        logger.info(
            "Combat initiated successfully",
            extra={
                "enemies_count": len(combat_enemies),
                "player_init": player_init,
                "enemy_init": enemy_init,
                "combat_state": session["combat_state"],
            },
        )

    def _build_combat_dice_rolls(self, round_result) -> list[DiceRoll]:
        """Build DiceRoll list from combat round result.

        Args:
            round_result: CombatRoundResult from combat resolution

        Returns:
            List of DiceRoll for the response
        """
        dice_rolls = []
        for attack in round_result.attack_results:
            # Attack roll
            dice_rolls.append(
                DiceRoll(
                    type="attack",
                    roll=attack.attack_roll,
                    modifier=attack.attack_bonus,
                    total=attack.attack_total,
                    success=attack.is_hit,
                )
            )
            # Damage roll if hit
            if attack.is_hit and attack.damage > 0:
                dice_rolls.append(
                    DiceRoll(
                        type="damage",
                        roll=sum(attack.damage_rolls) if attack.damage_rolls else attack.damage,
                        modifier=0,
                        total=attack.damage,
                        success=True,
                    )
                )
        return dice_rolls

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
        inventory_names = [item["name"] if isinstance(item, dict) else item for item in inventory]

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

        # Track combat state (for non-combat actions, Claude may report enemies)
        if not session.get("combat_state", {}).get("active"):
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
