"""DM service for processing player actions."""

import os
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

from aws_lambda_powertools import Logger

from dm.bedrock_client import MistralResponse
from dm.bestiary import spawn_enemies
from dm.combat import CombatResolver
from dm.combat_narrator import (
    COMBAT_NARRATOR_SYSTEM_PROMPT,
    build_combat_log_entries,
    build_defend_log_entry,
    build_defend_narrative,
    build_flee_log_entry,
    build_flee_narrative,
    build_narrator_prompt,
    clean_narrator_output,
)
from dm.combat_parser import get_default_action, parse_combat_action
from dm.models import (
    ActionResponse,
    CharacterSnapshot,
    CombatAction,
    CombatActionType,
    CombatEnemy,
    CombatLogEntry,
    CombatPhase,
    CombatResponse,
    CombatState,
    DiceRoll,
    DMResponse,
    Enemy,
    StateChanges,
    UsageStats,
)
from dm.parser import parse_dm_response
from dm.prompts import DMPromptBuilder
from shared.cost_limits import CostLimits
from shared.db import DynamoDBClient, convert_floats_to_decimal
from shared.dice import roll as roll_dice_notation
from shared.exceptions import GameStateError, NotFoundError
from shared.items import ITEM_CATALOG, find_item_by_name
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

    def _record_usage(
        self, session_id: str, response: MistralResponse
    ) -> UsageStats | None:
        """Record token usage from AI response and return stats.

        Args:
            session_id: Session ID for per-session tracking
            response: AI response with token counts

        Returns:
            UsageStats with current usage, or None if tracking unavailable
        """
        if self._token_tracker is None:
            return None

        try:
            global_usage, session_usage = self._token_tracker.increment_usage(
                session_id=session_id,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            )
            limits = CostLimits()
            return UsageStats(
                session_tokens=session_usage["input_tokens"]
                + session_usage["output_tokens"],
                session_limit=limits.SESSION_DAILY_TOKENS,
                global_tokens=global_usage["input_tokens"]
                + global_usage["output_tokens"],
                global_limit=limits.GLOBAL_DAILY_TOKENS,
            )
        except Exception as e:
            # Don't fail the request if usage tracking fails
            logger.warning(
                "Failed to record token usage",
                extra={"error": str(e), "session_id": session_id},
            )
            return None

    def process_action(
        self,
        session_id: str,
        user_id: str,
        action: str,
        combat_action: CombatAction | None = None,
    ) -> ActionResponse:
        """Process a player action and return the DM response.

        Routes to combat or normal action processing based on combat state.

        Args:
            session_id: Session UUID
            user_id: User UUID
            action: Player action text
            combat_action: Optional structured combat action (takes precedence)

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
            response = self._process_combat_action(
                session, character, action, user_id, session_id, combat_action
            )
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
        combat_action: CombatAction | None = None,
    ) -> ActionResponse:
        """Process an action during active combat using turn-based system.

        Combat is resolved mechanically on the server, then AI narrates.

        Args:
            session: Session dict from DynamoDB
            character: Character dict from DynamoDB
            action: Player's action text
            user_id: User UUID
            session_id: Session UUID
            combat_action: Optional structured combat action

        Returns:
            ActionResponse with combat results
        """
        # Load combat state
        combat_state_dict = session.get("combat_state", {})
        combat_enemies_data = session.get("combat_enemies", [])

        combat_state = CombatState(**combat_state_dict)
        combat_state.round += 1

        combat_enemies = [CombatEnemy(**e) for e in combat_enemies_data]

        # Parse action if not structured
        if not combat_action:
            combat_action = parse_combat_action(action, combat_enemies)
            if not combat_action:
                combat_action = get_default_action(combat_enemies)

        logger.info(
            "Processing turn-based combat",
            extra={
                "round": combat_state.round,
                "enemies": len(combat_enemies),
                "action_type": combat_action.action_type.value,
                "target": combat_action.target_id,
            },
        )

        # Track attack results and new log entries
        attack_results: list = []
        new_log_entries: list[CombatLogEntry] = []
        xp_gained = 0
        fled = False
        player_defending = False
        narrative = ""
        item_used_result = None  # Track if item was used

        # ========== HANDLE USE_ITEM BEFORE PLAYER TURN ==========
        if combat_action.action_type == CombatActionType.USE_ITEM:
            item_used_result = self._handle_use_item(
                character, combat_action.item_id, combat_state.round
            )
            if item_used_result:
                # Item was used - still proceed to enemy turn
                new_log_entries.extend(item_used_result.get("log_entries", []))

        # ========== PLAYER TURN ==========
        player_attack, fled, player_defending = self.combat_resolver.resolve_player_turn(
            character, combat_action, combat_enemies
        )

        # Handle flee
        if fled:
            new_log_entries.append(build_flee_log_entry(combat_state.round, True))
            narrative = build_flee_narrative(True)
            return self._end_combat_response(
                session,
                character,
                session_id,
                combat_state,
                narrative,
                new_log_entries,
                victory=False,
                fled=True,
            )

        # Handle defend
        if player_defending:
            new_log_entries.append(build_defend_log_entry(combat_state.round))

        # Handle player attack result
        if player_attack:
            attack_results.append(player_attack)
            if player_attack.target_dead:
                # Find the enemy that was killed to get XP
                for enemy in combat_enemies:
                    if enemy.name == player_attack.defender and enemy.hp <= 0:
                        xp_gained += enemy.xp_value
                        break

        # Check if all enemies dead after player turn
        combat_ended, player_won, total_xp = self.combat_resolver.check_combat_end(
            character, combat_enemies
        )
        if combat_ended and player_won:
            xp_gained = total_xp  # Award all XP on victory
            # Generate victory narrative
            narrative = self._generate_combat_narrative(
                attack_results, character["name"], combat_enemies, session_id, outcome="victory"
            ) if attack_results else "Victory! All enemies have been defeated."
            new_log_entries.extend(
                build_combat_log_entries(attack_results, combat_state.round, character["name"])
            )
            return self._end_combat_response(
                session,
                character,
                session_id,
                combat_state,
                narrative,
                new_log_entries,
                attack_results=attack_results,
                victory=True,
                xp_gained=xp_gained,
            )

        # ========== ENEMY TURN ==========
        enemy_results = self.combat_resolver.resolve_enemy_phase(
            character, combat_enemies, player_defending
        )
        attack_results.extend(enemy_results)

        # Check for player death
        combat_ended, player_won, _ = self.combat_resolver.check_combat_end(
            character, combat_enemies
        )
        if combat_ended and not player_won:
            logger.info(
                "Player death detected",
                extra={
                    "attack_results_count": len(attack_results),
                    "attack_results": [
                        {
                            "attacker": a.attacker,
                            "defender": a.defender,
                            "damage": a.damage,
                            "is_hit": a.is_hit,
                        }
                        for a in attack_results
                    ],
                    "character_hp": character["hp"],
                },
            )
            narrative = self._generate_combat_narrative(
                attack_results, character["name"], combat_enemies, session_id, outcome="player_died"
            ) if attack_results else "You have fallen in battle."
            new_log_entries.extend(
                build_combat_log_entries(attack_results, combat_state.round, character["name"])
            )
            return self._end_combat_response(
                session,
                character,
                session_id,
                combat_state,
                narrative,
                new_log_entries,
                attack_results=attack_results,
                victory=False,
                died=True,
            )

        # ========== CONTINUE COMBAT ==========
        # Generate narrative for the round
        if item_used_result:
            # Item was used - build narrative around that
            item_narrative = item_used_result["log_entries"][0].narrative if item_used_result.get("log_entries") else ""
            if attack_results:
                # Item used + enemies attacked
                enemy_narrative = self._generate_combat_narrative(
                    attack_results, character["name"], combat_enemies, session_id
                )
                narrative = f"{item_narrative}\n\n{enemy_narrative}"
            else:
                narrative = item_narrative
        elif attack_results:
            narrative = self._generate_combat_narrative(
                attack_results, character["name"], combat_enemies, session_id
            )
        else:
            narrative = build_defend_narrative() if player_defending else "The combatants circle warily."

        # Build log entries
        new_log_entries.extend(
            build_combat_log_entries(attack_results, combat_state.round, character["name"])
        )

        # Update combat state
        combat_state.phase = CombatPhase.PLAYER_TURN
        combat_state.player_defending = False
        combat_state.combat_log.extend(new_log_entries)

        # Persist updated state
        session["combat_state"] = combat_state.model_dump()
        session["combat_enemies"] = [e.model_dump() for e in combat_enemies]

        # Update message history
        action_text = action if action else combat_action.action_type.value
        session = self._append_messages(session, action_text, narrative)

        # Apply XP gained this round (from kills)
        character["xp"] += xp_gained

        # Build response
        return self._build_combat_action_response(
            session, character, combat_state, combat_enemies, narrative, attack_results, None
        )

    def _generate_combat_narrative(
        self,
        attack_results: list,
        player_name: str,
        combat_enemies: list,
        session_id: str,
        outcome: str = "ongoing",
    ) -> str:
        """Generate AI narrative for combat results.

        Args:
            attack_results: List of AttackResult from combat
            player_name: Player character name
            combat_enemies: List of CombatEnemy in combat
            session_id: For usage tracking
            outcome: Combat outcome - "ongoing", "player_died", "victory"

        Returns:
            Narrative string
        """
        if not attack_results:
            return ""

        try:
            prompt = build_narrator_prompt(player_name, combat_enemies, attack_results, outcome)
            client = self._get_ai_client()

            # Use dedicated narrator method if available (Bedrock), otherwise fallback
            if hasattr(client, "narrate_combat"):
                ai_response = client.narrate_combat(
                    COMBAT_NARRATOR_SYSTEM_PROMPT,
                    prompt,
                )
            else:
                # Fallback for Claude client
                ai_response = client.send_action(
                    COMBAT_NARRATOR_SYSTEM_PROMPT,
                    "",
                    prompt,
                )

            # Record usage
            self._record_usage(session_id, ai_response)

            # Clean the response to remove any prompt leakage
            cleaned = clean_narrator_output(ai_response.text)
            if not cleaned:
                # If cleaning removed everything, use fallback
                return self._build_fallback_narrative(attack_results, player_name)
            return cleaned
        except Exception as e:
            logger.warning(f"Failed to generate combat narrative: {e}")
            # Fallback to simple description
            return self._build_fallback_narrative(attack_results, player_name)

    def _build_fallback_narrative(self, attack_results: list, player_name: str) -> str:
        """Build a fallback narrative if AI fails.

        Args:
            attack_results: List of AttackResult
            player_name: Player character name

        Returns:
            Simple narrative string
        """
        parts = []
        for result in attack_results:
            if result.is_hit:
                if result.target_dead:
                    parts.append(f"{result.attacker} strikes down {result.defender}!")
                else:
                    parts.append(f"{result.attacker} hits {result.defender} for {result.damage} damage.")
            else:
                parts.append(f"{result.attacker} misses {result.defender}.")
        return " ".join(parts)

    def _end_combat_response(
        self,
        session: dict,
        character: dict,
        session_id: str,
        combat_state: CombatState,
        narrative: str,
        log_entries: list[CombatLogEntry],
        attack_results: list | None = None,
        victory: bool = False,
        fled: bool = False,
        died: bool = False,
        xp_gained: int = 0,
    ) -> ActionResponse:
        """Build response for combat ending.

        Args:
            session: Session dict
            character: Character dict
            session_id: Session ID
            combat_state: Current combat state
            narrative: Narrative text
            log_entries: Combat log entries
            victory: True if player won
            fled: True if player fled
            died: True if player died
            xp_gained: XP to award

        Returns:
            ActionResponse with combat end state
        """
        # Apply XP
        character["xp"] += xp_gained

        # Clear combat state
        session["combat_state"] = {
            "active": False,
            "round": 0,
            "phase": CombatPhase.COMBAT_END.value,
            "player_initiative": 0,
            "enemy_initiative": 0,
            "player_defending": False,
            "combat_log": [],
        }
        session["combat_enemies"] = []

        # Handle death
        character_dead = died
        session_ended = died
        if died:
            session["status"] = "ended"
            session["ended_reason"] = "character_death"
            logger.info("Character died in combat", extra={"character": character["name"]})

        # Update message history
        action_summary = "Fled combat" if fled else ("Victory!" if victory else "Defeat")
        session = self._append_messages(session, action_summary, narrative)

        # Build inventory list
        inventory_names = [
            item["name"] if isinstance(item, dict) else item
            for item in character.get("inventory", [])
        ]

        # Build dice rolls from attack results (includes the killing blow)
        logger.debug(
            "Building dice rolls for combat end",
            extra={
                "attack_results_received": attack_results is not None,
                "attack_results_count": len(attack_results) if attack_results else 0,
                "died": died,
            },
        )
        dice_rolls = self._build_combat_dice_rolls_from_list(attack_results or [])
        logger.debug(
            "Built dice rolls",
            extra={"dice_rolls_count": len(dice_rolls)},
        )

        return ActionResponse(
            narrative=narrative,
            state_changes=StateChanges(xp_delta=xp_gained),
            dice_rolls=dice_rolls,
            combat_active=False,
            enemies=[],
            combat=CombatResponse(
                active=False,
                round=combat_state.round,
                phase=CombatPhase.COMBAT_END,
                your_hp=character["hp"],
                your_max_hp=character["max_hp"],
                enemies=[],
                available_actions=[],
                valid_targets=[],
                combat_log=log_entries,
            ),
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
            usage=None,
        )

    def _handle_use_item(
        self,
        character: dict,
        item_id: str | None,
        combat_round: int,
    ) -> dict | None:
        """Handle USE_ITEM combat action.

        Consumes the item and applies its effects. Currently supports
        healing potions.

        Args:
            character: Character dict (will be modified in-place)
            item_id: ID of item to use, or None to auto-select
            combat_round: Current combat round number

        Returns:
            Dict with item_name, healing, log_entries, or None if no item used
        """
        inventory = character.get("inventory", [])

        # Auto-select healing potion if no item_id provided
        if not item_id:
            for item in inventory:
                if isinstance(item, dict) and item.get("item_id") == "potion_healing":
                    item_id = "potion_healing"
                    break

        if not item_id:
            logger.info("USE_ITEM: No usable item found")
            return None

        # Find and consume item
        item_found = None
        new_inventory = []

        for item in inventory:
            if isinstance(item, dict):
                if item.get("item_id") == item_id and not item_found:
                    item_found = item
                    # Decrement quantity or remove
                    qty = item.get("quantity", 1)
                    if qty > 1:
                        new_inventory.append({**item, "quantity": qty - 1})
                    # else: consumed, don't add back
                else:
                    new_inventory.append(item)
            else:
                new_inventory.append(item)

        if not item_found:
            logger.warning(f"USE_ITEM: Item {item_id} not in inventory")
            return None

        character["inventory"] = new_inventory

        # Apply item effect
        item_def = ITEM_CATALOG.get(item_id)
        result: dict = {
            "item_name": item_found.get("name", item_id),
            "healing": 0,
            "log_entries": [],
        }

        if item_def and item_def.healing > 0:
            # Healing potion - roll 1d8
            healing_roll, _ = roll_dice_notation("1d8")
            old_hp = character["hp"]
            character["hp"] = min(character["max_hp"], old_hp + healing_roll)
            actual_healing = character["hp"] - old_hp
            result["healing"] = actual_healing

            logger.info(
                f"USE_ITEM: {item_def.name} healed {actual_healing} HP",
                extra={
                    "item_id": item_id,
                    "healing_roll": healing_roll,
                    "actual_healing": actual_healing,
                    "hp_before": old_hp,
                    "hp_after": character["hp"],
                },
            )

            # Add log entry
            result["log_entries"].append(
                CombatLogEntry(
                    round=combat_round,
                    actor="player",
                    action="use_item",
                    target=None,
                    roll=healing_roll,
                    damage=None,
                    result=f"healed_{actual_healing}",
                    narrative=f"You drink the {item_def.name} and restore {actual_healing} HP.",
                )
            )
        else:
            logger.info(f"USE_ITEM: Used {result['item_name']} (no mechanical effect)")
            result["log_entries"].append(
                CombatLogEntry(
                    round=combat_round,
                    actor="player",
                    action="use_item",
                    target=None,
                    roll=None,
                    damage=None,
                    result="used",
                    narrative=f"You use the {result['item_name']}.",
                )
            )

        return result

    def _build_combat_action_response(
        self,
        session: dict,
        character: dict,
        combat_state: CombatState,
        combat_enemies: list[CombatEnemy],
        narrative: str,
        attack_results: list,
        usage_stats: UsageStats | None,
    ) -> ActionResponse:
        """Build ActionResponse for ongoing combat.

        Args:
            session: Session dict
            character: Character dict
            combat_state: Current combat state
            combat_enemies: List of enemies
            narrative: Narrative text
            attack_results: Attack results this round
            usage_stats: Token usage stats

        Returns:
            ActionResponse with combat state
        """
        # Build dice rolls from attack results
        dice_rolls = self._build_combat_dice_rolls_from_list(attack_results)

        # Build inventory list
        inventory_names = [
            item["name"] if isinstance(item, dict) else item
            for item in character.get("inventory", [])
        ]

        # Get living enemies for response - use dicts to ensure id is serialized
        living_enemies = [e for e in combat_enemies if e.hp > 0]
        response_enemies = []
        for e in living_enemies:
            enemy_id = e.id
            if not enemy_id:
                # Generate ID if missing (shouldn't happen)
                enemy_id = str(uuid4())
                logger.warning(f"Combat enemy {e.name} missing ID, generated: {enemy_id}")
            response_enemies.append({
                "id": enemy_id,
                "name": e.name,
                "hp": e.hp,
                "ac": e.ac,
                "max_hp": e.max_hp,
            })
        logger.debug(
            "Built combat response enemies",
            extra={"enemies": response_enemies},
        )

        # Build available actions
        available_actions = [
            CombatActionType.ATTACK,
            CombatActionType.DEFEND,
            CombatActionType.FLEE,
        ]
        # Add USE_ITEM if player has potions
        if any("potion" in (item.get("name", item) if isinstance(item, dict) else item).lower()
               for item in character.get("inventory", [])):
            available_actions.append(CombatActionType.USE_ITEM)

        # Get valid targets
        valid_targets = [e.id for e in living_enemies]

        return ActionResponse(
            narrative=narrative,
            state_changes=StateChanges(),
            dice_rolls=dice_rolls,
            combat_active=True,
            enemies=response_enemies,
            combat=CombatResponse(
                active=True,
                round=combat_state.round,
                phase=combat_state.phase,
                your_hp=character["hp"],
                your_max_hp=character["max_hp"],
                enemies=response_enemies,
                available_actions=available_actions,
                valid_targets=valid_targets,
                combat_log=combat_state.combat_log[-10:],  # Last 10 entries
            ),
            character=CharacterSnapshot(
                hp=character["hp"],
                max_hp=character["max_hp"],
                xp=character["xp"],
                gold=character["gold"],
                level=character["level"],
                inventory=inventory_names,
            ),
            character_dead=False,
            session_ended=False,
            usage=usage_stats,
        )

    def _build_combat_dice_rolls_from_list(self, attack_results: list) -> list[DiceRoll]:
        """Build DiceRoll list from attack results.

        Args:
            attack_results: List of AttackResult

        Returns:
            List of DiceRoll for the response
        """
        dice_rolls = []
        for attack in attack_results:
            # Attack roll with attacker/target attribution
            dice_rolls.append(
                DiceRoll(
                    type="attack",
                    dice="d20",
                    roll=attack.attack_roll,
                    modifier=attack.attack_bonus,
                    total=attack.attack_total,
                    success=attack.is_hit,
                    attacker=attack.attacker,
                    target=attack.defender,
                )
            )
            # Damage roll if hit
            if attack.is_hit and attack.damage > 0:
                # Extract die type from damage_dice (e.g., "1d6" -> "d6", "2d4+1" -> "d4")
                damage_die = "d6"  # default
                if hasattr(attack, "damage_dice") and attack.damage_dice:
                    import re
                    match = re.search(r"d(\d+)", attack.damage_dice)
                    if match:
                        damage_die = f"d{match.group(1)}"

                # Calculate modifier (total - raw roll)
                raw_roll = sum(attack.damage_rolls) if attack.damage_rolls else attack.damage
                damage_mod = attack.damage - raw_roll

                dice_rolls.append(
                    DiceRoll(
                        type="damage",
                        dice=damage_die,
                        roll=raw_roll,
                        modifier=damage_mod,
                        total=attack.damage,
                        success=None,  # No success/fail for damage
                        attacker=attack.attacker,
                        target=attack.defender,
                    )
                )
        return dice_rolls

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

        # Record token usage and get stats
        usage_stats = self._record_usage(session_id, ai_response)

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
        # Use dicts to ensure id field is always serialized
        if is_combat_active:
            combat_enemies_data = session.get("combat_enemies", [])
            response_enemies = []
            for e in combat_enemies_data:
                enemy_id = e.get("id")
                if not enemy_id:
                    # Generate ID if missing (shouldn't happen but safety net)
                    enemy_id = str(uuid4())
                    logger.warning(f"Enemy {e.get('name')} missing ID, generated: {enemy_id}")
                response_enemies.append({
                    "id": enemy_id,
                    "name": e["name"],
                    "hp": e["hp"],
                    "ac": e["ac"],
                    "max_hp": e.get("max_hp", e["hp"]),
                })
            logger.debug(
                "Built response_enemies from session",
                extra={"enemies": response_enemies},
            )
        else:
            # Convert Enemy objects to dicts for non-combat responses
            response_enemies = [
                {"id": e.id, "name": e.name, "hp": e.hp, "ac": e.ac, "max_hp": e.max_hp}
                for e in (dm_response.enemies or [])
            ]

        logger.debug(
            "Building action response",
            extra={
                "combat_active": is_combat_active,
                "enemies_count": len(response_enemies) if response_enemies else 0,
            },
        )

        # Build CombatResponse if combat was just initiated
        combat_response = None
        if is_combat_active:
            combat_enemies_data = session.get("combat_enemies", [])
            combat_state_data = session.get("combat_state", {})

            # Build available actions
            available_actions = [
                CombatActionType.ATTACK,
                CombatActionType.DEFEND,
                CombatActionType.FLEE,
            ]
            if any("potion" in (item.get("name", item) if isinstance(item, dict) else item).lower()
                   for item in character.get("inventory", [])):
                available_actions.append(CombatActionType.USE_ITEM)

            combat_response = CombatResponse(
                active=True,
                round=combat_state_data.get("round", 0),
                phase=CombatPhase.PLAYER_TURN,
                your_hp=character["hp"],
                your_max_hp=character["max_hp"],
                enemies=response_enemies,
                available_actions=available_actions,
                valid_targets=[e.get("id", "") for e in combat_enemies_data],
                combat_log=[],
            )

        return ActionResponse(
            narrative=dm_response.narrative,
            state_changes=dm_response.state_changes,
            dice_rolls=dm_response.dice_rolls,
            combat_active=is_combat_active,
            enemies=response_enemies,
            combat=combat_response,
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
            usage=usage_stats,
        )

    def _initiate_combat(self, session: dict, enemies: list[Enemy]) -> None:
        """Start combat with enemies from Claude's response.

        Uses spawn_enemies to handle duplicate enemy types with numbered names.

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

        # Collect enemies for spawning
        known_enemies: list[dict] = []
        unknown_enemies: list[Enemy] = []

        # Separate known (bestiary) from unknown enemies
        for enemy in enemies:
            from dm.bestiary import get_enemy_template

            if get_enemy_template(enemy.name):
                # Will be handled by spawn_enemies
                pass
            else:
                unknown_enemies.append(enemy)

        # Spawn known enemies with numbering
        try:
            known_types = [e.name for e in enemies if get_enemy_template(e.name)]
            if known_types:
                spawned = spawn_enemies(known_types)
                known_enemies = [e.model_dump() for e in spawned]
                logger.debug(
                    "Spawned enemies from bestiary with numbering",
                    extra={"spawned": known_enemies},
                )
        except ValueError as err:
            logger.warning(f"Failed to spawn some enemies: {err}")

        # Handle unknown enemies with fallback stats (add numbering manually)
        unknown_type_counts: dict[str, int] = {}
        unknown_type_indices: dict[str, int] = {}
        for e in unknown_enemies:
            normalized = e.name.lower().strip()
            unknown_type_counts[normalized] = unknown_type_counts.get(normalized, 0) + 1

        fallback_enemies: list[dict] = []
        for enemy in unknown_enemies:
            normalized = enemy.name.lower().strip()
            count = unknown_type_counts[normalized]

            name = enemy.name
            if count > 1:
                idx = unknown_type_indices.get(normalized, 0) + 1
                unknown_type_indices[normalized] = idx
                name = f"{enemy.name} {idx}"

            fallback_enemy = {
                "id": str(uuid4()),
                "name": name,
                "hp": enemy.hp,
                "max_hp": enemy.max_hp or enemy.hp,
                "ac": enemy.ac,
                "attack_bonus": 1,
                "damage_dice": "1d6",
                "xp_value": max(10, enemy.hp * 2),
            }
            fallback_enemies.append(fallback_enemy)
            logger.debug(
                "Using Claude stats for unknown enemy",
                extra={"enemy_name": enemy.name, "fallback": fallback_enemy},
            )

        combat_enemies = known_enemies + fallback_enemies

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
                "enemies_with_ids": [
                    {"id": e.get("id"), "name": e.get("name")} for e in combat_enemies
                ],
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

    def _find_inventory_item_index(
        self, inventory: list, item_name: str
    ) -> int | None:
        """Find item index by name or item_id (case-insensitive).

        Args:
            inventory: List of inventory items (dicts or strings)
            item_name: Item name or ID to find

        Returns:
            Index of item if found, None otherwise
        """
        normalized = item_name.lower().strip()
        for i, item in enumerate(inventory):
            if isinstance(item, dict):
                if item.get("name", "").lower() == normalized:
                    return i
                if item.get("item_id", "").lower() == normalized:
                    return i
            elif isinstance(item, str):
                if item.lower() == normalized:
                    return i
        return None

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

        # Inventory changes - validate items through catalog
        inventory = character.get("inventory", [])
        # Track item_ids to avoid duplicates
        inventory_ids = [
            item.get("item_id") for item in inventory if isinstance(item, dict)
        ]

        for item_name in state.inventory_add:
            # Validate item through catalog lookup
            item_def = find_item_by_name(item_name)
            if item_def is None:
                logger.warning(
                    f"DM tried to give unknown item: {item_name}",
                    extra={"item_name": item_name},
                )
                continue  # Skip unknown items

            # Only add if not already in inventory
            if item_def.id not in inventory_ids:
                inventory.append({
                    "item_id": item_def.id,
                    "name": item_def.name,
                    "quantity": 1,
                    "item_type": item_def.item_type.value,
                    "description": item_def.description,
                })
                inventory_ids.append(item_def.id)
                logger.info(
                    f"Added item to inventory: {item_def.name}",
                    extra={"item_id": item_def.id, "item_type": item_def.item_type.value},
                )

        for item_name in state.inventory_remove:
            idx = self._find_inventory_item_index(inventory, item_name)
            if idx is not None:
                item = inventory[idx]
                if isinstance(item, dict):
                    qty = item.get("quantity", 1)
                    if qty > 1:
                        inventory[idx]["quantity"] = qty - 1
                        logger.info(f"Decremented {item_name} quantity to {qty - 1}")
                    else:
                        inventory.pop(idx)
                        logger.info(f"Removed {item_name} from inventory")
                else:
                    # Legacy string format
                    inventory.pop(idx)
                    logger.info(f"Removed {item_name} from inventory (legacy)")
            else:
                logger.warning(f"Tried to remove item not in inventory: {item_name}")

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
