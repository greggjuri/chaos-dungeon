"""Integration tests for DM prompt building and response parsing."""

import pytest

from dm.parser import parse_dm_response
from dm.prompts import DMPromptBuilder
from shared.models import (
    AbilityScores,
    Character,
    CharacterClass,
    Item,
    Message,
    MessageRole,
    Session,
)


@pytest.fixture
def mock_character() -> Character:
    """Create a mock character for testing."""
    return Character(
        character_id="char-test-123",
        user_id="user-test-456",
        name="Grimjaw",
        character_class=CharacterClass.FIGHTER,
        level=2,
        xp=2100,
        hp=12,
        max_hp=16,
        gold=75,
        abilities=AbilityScores(
            strength=17,
            intelligence=8,
            wisdom=10,
            dexterity=12,
            constitution=16,
            charisma=11,
        ),
        inventory=[
            Item(name="longsword"),
            Item(name="chainmail"),
            Item(name="shield"),
            Item(name="backpack"),
            Item(name="torch"),
            Item(name="rations"),
        ],
        created_at="2026-01-01T00:00:00Z",
    )


@pytest.fixture
def mock_session() -> Session:
    """Create a mock session for testing."""
    return Session(
        session_id="sess-test-789",
        user_id="user-test-456",
        character_id="char-test-123",
        campaign_setting="forgotten_mines",
        current_location="The First Tunnel",
        world_state={
            "entrance_collapsed": False,
            "found_pickaxe": True,
            "heard_clicking": True,
        },
        message_history=[
            Message(
                role=MessageRole.DM,
                content="You enter the abandoned mine. The air is stale and cold.",
                timestamp="2026-01-01T10:00:00Z",
            ),
            Message(
                role=MessageRole.PLAYER,
                content="I light my torch and look around.",
                timestamp="2026-01-01T10:01:00Z",
            ),
            Message(
                role=MessageRole.DM,
                content="The flickering torchlight reveals old mining equipment.",
                timestamp="2026-01-01T10:02:00Z",
            ),
            Message(
                role=MessageRole.PLAYER,
                content="I search the equipment for anything useful.",
                timestamp="2026-01-01T10:03:00Z",
            ),
            Message(
                role=MessageRole.DM,
                content="You find a rusty but serviceable pickaxe.",
                timestamp="2026-01-01T10:04:00Z",
            ),
        ],
        created_at="2026-01-01T10:00:00Z",
    )


class TestFullDMFlow:
    """Integration tests for the complete DM flow."""

    def test_full_dm_flow_combat(
        self, mock_character: Character, mock_session: Session
    ) -> None:
        """Integration test: prompt building → combat response parsing."""
        builder = DMPromptBuilder()

        # Build prompts and verify they work correctly
        system = builder.build_system_prompt("forgotten_mines")
        context = builder.build_context(mock_character, mock_session)
        user_msg = builder.build_user_message("I attack the giant spider!")

        # Verify system prompt structure
        assert "Dungeon Master" in system
        assert "BECMI" in system
        assert "Deepholm" in system or "mines" in system.lower()
        assert len(system) > 1500  # Should be substantial

        # Verify context includes character and session info
        assert "Grimjaw" in context
        assert "Fighter" in context
        assert "12/16" in context  # HP
        assert "forgotten_mines" in context
        assert "pickaxe" in context.lower() or "clicking" in context.lower()

        # Verify user message format
        assert user_msg == "[Player Action]: I attack the giant spider!"

        # Simulate Claude response with combat
        mock_response = '''The giant spider hisses and lunges at you! You sidestep and bring your longsword down in a powerful arc. The blade bites deep into the creature's carapace, ichor spraying across the tunnel walls.

The spider screeches in pain but isn't finished yet. It rears back, fangs dripping with venom, ready to strike again.

```json
{
  "state_changes": {
    "xp_delta": 0
  },
  "dice_rolls": [
    {"type": "initiative", "roll": 4, "modifier": 1, "total": 5, "success": true},
    {"type": "attack", "roll": 17, "modifier": 3, "total": 20, "success": true},
    {"type": "damage", "roll": 7, "modifier": 3, "total": 10}
  ],
  "combat_active": true,
  "enemies": [
    {"name": "Giant Spider", "hp": 8, "ac": 14, "max_hp": 18}
  ]
}
```'''

        # Parse response
        result = parse_dm_response(mock_response)

        # Verify narrative
        assert "giant spider" in result.narrative.lower()
        assert "longsword" in result.narrative.lower()

        # Verify combat state
        assert result.combat_active is True
        assert len(result.enemies) == 1
        assert result.enemies[0].name == "Giant Spider"
        assert result.enemies[0].hp == 8
        assert result.enemies[0].max_hp == 18

        # Verify dice rolls
        assert len(result.dice_rolls) == 3
        attack_roll = next(r for r in result.dice_rolls if r.type == "attack")
        assert attack_roll.roll == 17
        assert attack_roll.total == 20
        assert attack_roll.success is True

    def test_full_dm_flow_exploration(
        self, mock_character: Character, mock_session: Session
    ) -> None:
        """Integration test: prompt building → exploration response parsing."""
        builder = DMPromptBuilder()

        # Build prompts (verify they don't raise)
        system = builder.build_system_prompt("forgotten_mines")
        context = builder.build_context(mock_character, mock_session)
        user_msg = builder.build_user_message("I search the dark alcove carefully.")

        # Verify prompts were built
        assert len(system) > 0
        assert len(context) > 0
        assert len(user_msg) > 0

        # Simulate Claude response with discovery
        mock_response = '''You approach the dark alcove cautiously, torch held high. The shadows retreat to reveal a small cache hidden behind loose stones.

Inside, you find a leather pouch containing gold coins and a small vial of shimmering blue liquid. The vial is cool to the touch.

```json
{
  "state_changes": {
    "gold_delta": 25,
    "xp_delta": 10,
    "inventory_add": ["potion of healing"],
    "world_state": {
      "alcove_searched": true
    }
  },
  "dice_rolls": [
    {"type": "perception", "roll": 14, "modifier": 0, "total": 14, "success": true}
  ],
  "combat_active": false
}
```'''

        result = parse_dm_response(mock_response)

        # Verify state changes
        assert result.state_changes.gold_delta == 25
        assert result.state_changes.xp_delta == 10
        assert "potion of healing" in result.state_changes.inventory_add
        assert result.state_changes.world_state.get("alcove_searched") is True

        # Verify no combat
        assert result.combat_active is False
        assert result.enemies == []

    def test_full_dm_flow_no_changes(
        self, mock_character: Character, mock_session: Session
    ) -> None:
        """Integration test: response with no state changes."""
        builder = DMPromptBuilder()

        # Build prompts (verify they work)
        context = builder.build_context(mock_character, mock_session)
        user_msg = builder.build_user_message("I listen carefully.")

        # Verify prompts were built
        assert len(context) > 0
        assert len(user_msg) > 0

        # Simulate response with no changes
        mock_response = '''You press your ear against the cold stone wall and listen. From somewhere deeper in the mine, you hear a faint clicking sound. It's rhythmic, almost like... mandibles.

The sound fades, then returns. Something is moving down there.

```json
{"state_changes": {}}
```'''

        result = parse_dm_response(mock_response)

        assert "clicking" in result.narrative.lower()
        assert result.state_changes.hp_delta == 0
        assert result.state_changes.gold_delta == 0
        assert result.state_changes.inventory_add == []

    def test_all_campaigns_build_successfully(self) -> None:
        """Test that all campaigns build valid prompts."""
        builder = DMPromptBuilder()
        campaigns = ["default", "dark_forest", "cursed_castle", "forgotten_mines"]

        for campaign in campaigns:
            prompt = builder.build_system_prompt(campaign)
            assert len(prompt) > 1000, f"Campaign {campaign} prompt too short"
            assert "Dungeon Master" in prompt
            assert "BECMI" in prompt

    def test_context_with_empty_history(self, mock_character: Character) -> None:
        """Test context building with empty message history."""
        builder = DMPromptBuilder()
        session = Session(
            session_id="sess-new",
            user_id="user-test-456",
            character_id="char-test-123",
            campaign_setting="default",
            current_location="The Rusty Tankard",
            world_state={},
            message_history=[],
            created_at="2026-01-01T00:00:00Z",
        )

        context = builder.build_context(mock_character, session)

        assert "Grimjaw" in context
        assert "No previous messages" in context or "RECENT HISTORY" in context

    def test_response_parsing_robustness(self) -> None:
        """Test parser handles various edge cases."""
        # Extra whitespace
        result1 = parse_dm_response("\n\n  You look around.  \n\n")
        assert "look around" in result1.narrative

        # JSON at very end
        result2 = parse_dm_response('Text.\n```json\n{"state_changes":{}}\n```')
        assert "Text" in result2.narrative

        # Multiple paragraphs before JSON
        result3 = parse_dm_response('''Para 1.

Para 2.

Para 3.

```json
{"state_changes": {"xp_delta": 5}}
```''')
        assert result3.state_changes.xp_delta == 5
        assert "Para 1" in result3.narrative
        assert "Para 3" in result3.narrative
