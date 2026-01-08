"""Tests for DM prompt builders."""

import pytest

from dm.prompts import (
    BECMI_RULES,
    CAMPAIGN_PROMPTS,
    OUTPUT_FORMAT,
    DMPromptBuilder,
    build_system_prompt,
)
from dm.prompts.campaigns import get_campaign_prompt
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
        character_id="char-123",
        user_id="user-456",
        name="Thorin",
        character_class=CharacterClass.FIGHTER,
        level=1,
        xp=0,
        hp=8,
        max_hp=10,
        gold=50,
        abilities=AbilityScores(
            strength=16,
            intelligence=10,
            wisdom=12,
            dexterity=14,
            constitution=15,
            charisma=9,
        ),
        inventory=[Item(name="longsword"), Item(name="shield"), Item(name="torch")],
        created_at="2026-01-01T00:00:00Z",
    )


@pytest.fixture
def mock_session() -> Session:
    """Create a mock session for testing."""
    return Session(
        session_id="sess-789",
        user_id="user-456",
        character_id="char-123",
        campaign_setting="dark_forest",
        current_location="The edge of the Dark Forest",
        world_state={"torch_lit": True, "heard_whispers": True},
        message_history=[
            Message(
                role=MessageRole.DM,
                content="You stand at the forest's edge.",
                timestamp="2026-01-01T00:01:00Z",
            ),
            Message(
                role=MessageRole.PLAYER,
                content="I light my torch and enter.",
                timestamp="2026-01-01T00:02:00Z",
            ),
            Message(
                role=MessageRole.DM,
                content="The flame flickers as you step into darkness.",
                timestamp="2026-01-01T00:03:00Z",
            ),
        ],
        created_at="2026-01-01T00:00:00Z",
    )


class TestBuildSystemPrompt:
    """Tests for build_system_prompt function."""

    def test_build_system_prompt_default(self) -> None:
        """Test building system prompt with default campaign."""
        prompt = build_system_prompt()

        assert "Dungeon Master" in prompt
        assert "BECMI" in prompt
        assert "OUTPUT FORMAT" in prompt
        assert "CONTENT GUIDELINES" in prompt
        assert "DEFAULT" in prompt or "Millbrook" in prompt

    def test_build_system_prompt_dark_forest(self) -> None:
        """Test building system prompt with dark_forest campaign."""
        prompt = build_system_prompt("dark_forest")

        assert "Dark Forest" in prompt
        assert "survival horror" in prompt.lower() or "haunted" in prompt.lower()

    def test_build_system_prompt_cursed_castle(self) -> None:
        """Test building system prompt with cursed_castle campaign."""
        prompt = build_system_prompt("cursed_castle")

        assert "Castle Ravenmoor" in prompt or "vampire" in prompt.lower()

    def test_build_system_prompt_forgotten_mines(self) -> None:
        """Test building system prompt with forgotten_mines campaign."""
        prompt = build_system_prompt("forgotten_mines")

        assert "Deepholm" in prompt or "mines" in prompt.lower()

    def test_build_system_prompt_invalid_falls_back(self) -> None:
        """Test that invalid campaign falls back to default."""
        prompt = build_system_prompt("nonexistent_campaign")

        # Should fall back to default
        assert "Millbrook" in prompt or "Rusty Tankard" in prompt

    def test_system_prompt_contains_all_sections(self) -> None:
        """Test that system prompt contains all required sections."""
        prompt = build_system_prompt()

        # DM identity
        assert "Dungeon Master" in prompt
        assert "dark fantasy" in prompt.lower()

        # BECMI rules
        assert "Attack roll" in prompt
        assert "Saving Throws" in prompt

        # Output format
        assert "state_changes" in prompt
        assert "dice_rolls" in prompt

        # Content guidelines
        assert "adults only" in prompt.lower() or "adults-only" in prompt.lower()


class TestCampaignPrompts:
    """Tests for campaign prompt configuration."""

    def test_all_campaigns_defined(self) -> None:
        """Test that all expected campaigns are defined."""
        expected = {"default", "dark_forest", "cursed_castle", "forgotten_mines"}
        assert set(CAMPAIGN_PROMPTS.keys()) == expected

    def test_get_campaign_prompt_valid(self) -> None:
        """Test getting a valid campaign prompt."""
        prompt = get_campaign_prompt("dark_forest")
        assert "Dark Forest" in prompt

    def test_get_campaign_prompt_invalid(self) -> None:
        """Test that invalid campaign returns default."""
        prompt = get_campaign_prompt("invalid")
        default = get_campaign_prompt("default")
        assert prompt == default


class TestBecmiRules:
    """Tests for BECMI rules content."""

    def test_rules_contains_combat(self) -> None:
        """Test that rules contain combat mechanics."""
        assert "Attack roll" in BECMI_RULES
        assert "d20" in BECMI_RULES
        assert "AC" in BECMI_RULES

    def test_rules_contains_modifiers(self) -> None:
        """Test that rules contain ability modifier table."""
        assert "Modifier" in BECMI_RULES
        assert "-3" in BECMI_RULES
        assert "+3" in BECMI_RULES

    def test_rules_contains_classes(self) -> None:
        """Test that rules contain all four classes."""
        assert "Fighter" in BECMI_RULES
        assert "Thief" in BECMI_RULES
        assert "Magic-User" in BECMI_RULES
        assert "Cleric" in BECMI_RULES


class TestOutputFormat:
    """Tests for output format instructions."""

    def test_format_contains_json_example(self) -> None:
        """Test that output format contains JSON example."""
        assert "```json" in OUTPUT_FORMAT
        assert "state_changes" in OUTPUT_FORMAT

    def test_format_documents_fields(self) -> None:
        """Test that output format documents all fields."""
        assert "hp_delta" in OUTPUT_FORMAT
        assert "gold_delta" in OUTPUT_FORMAT
        assert "xp_delta" in OUTPUT_FORMAT
        assert "inventory_add" in OUTPUT_FORMAT
        assert "dice_rolls" in OUTPUT_FORMAT
        # combat_active is inferred from presence of enemies, not explicitly documented
        assert "enemies" in OUTPUT_FORMAT


class TestDMPromptBuilder:
    """Tests for DMPromptBuilder class."""

    def test_build_system_prompt_via_builder(self) -> None:
        """Test building system prompt via builder class."""
        builder = DMPromptBuilder()
        prompt = builder.build_system_prompt("default")

        assert "Dungeon Master" in prompt
        assert len(prompt) > 1000  # Should be substantial

    def test_build_context(self, mock_character: Character, mock_session: Session) -> None:
        """Test building context from character and session."""
        builder = DMPromptBuilder()
        context = builder.build_context(mock_character, mock_session)

        # Character info
        assert "Thorin" in context
        assert "Fighter" in context
        assert "8/10" in context  # HP
        assert "50 gp" in context  # Gold

        # Abilities with modifiers
        assert "STR 16" in context
        assert "+2" in context  # STR modifier

        # Inventory
        assert "longsword" in context
        assert "shield" in context

        # Session info
        assert "dark_forest" in context
        assert "torch_lit" in context

        # Message history
        assert "forest's edge" in context
        assert "light my torch" in context

    def test_format_character_block(self, mock_character: Character) -> None:
        """Test character block formatting."""
        builder = DMPromptBuilder()
        block = builder._format_character_block(mock_character)

        assert "## CURRENT CHARACTER" in block
        assert "Thorin" in block
        assert "Fighter Level 1" in block
        assert "HP: 8/10" in block
        assert "Gold: 50 gp" in block
        assert "longsword" in block
        assert "shield" in block
        assert "torch" in block

    def test_format_character_empty_inventory(self) -> None:
        """Test character block with empty inventory."""
        builder = DMPromptBuilder()
        char = Character(
            character_id="char-123",
            user_id="user-456",
            name="Barehand",
            character_class=CharacterClass.THIEF,
            level=1,
            xp=0,
            hp=4,
            max_hp=4,
            gold=0,
            abilities=AbilityScores(
                strength=10,
                intelligence=10,
                wisdom=10,
                dexterity=10,
                constitution=10,
                charisma=10,
            ),
            inventory=[],
            created_at="2026-01-01T00:00:00Z",
        )
        block = builder._format_character_block(char)

        assert "Inventory: Empty" in block

    def test_format_world_state(self, mock_session: Session) -> None:
        """Test world state formatting."""
        builder = DMPromptBuilder()
        state = builder._format_world_state(mock_session)

        assert "## CURRENT SITUATION" in state
        assert "edge of the Dark Forest" in state
        assert "dark_forest" in state
        assert "torch_lit" in state

    def test_format_world_state_empty(self) -> None:
        """Test world state with no flags."""
        builder = DMPromptBuilder()
        session = Session(
            session_id="sess-789",
            user_id="user-456",
            character_id="char-123",
            campaign_setting="default",
            current_location="The Rusty Tankard",
            world_state={},
            message_history=[],
            created_at="2026-01-01T00:00:00Z",
        )
        state = builder._format_world_state(session)

        assert "World State: None" in state

    def test_format_message_history(self, mock_session: Session) -> None:
        """Test message history formatting."""
        builder = DMPromptBuilder()
        history = builder._format_message_history(mock_session.message_history)

        assert "## RECENT HISTORY" in history
        assert "[DM]:" in history
        assert "[Player]:" in history
        assert "forest's edge" in history

    def test_format_message_history_empty(self) -> None:
        """Test empty message history."""
        builder = DMPromptBuilder()
        history = builder._format_message_history([])

        assert "No previous messages" in history

    def test_format_message_history_truncation(self) -> None:
        """Test that message history truncates to max."""
        builder = DMPromptBuilder()

        # Create 20 messages
        messages = [
            Message(
                role=MessageRole.PLAYER if i % 2 == 0 else MessageRole.DM,
                content=f"Message {i}",
                timestamp="2026-01-01T00:00:00Z",
            )
            for i in range(20)
        ]

        history = builder._format_message_history(messages, max_messages=10)

        # Should only have last 10 messages
        assert "Message 10" in history
        assert "Message 19" in history
        assert "Message 0" not in history
        assert "Message 9" not in history

    def test_build_user_message(self) -> None:
        """Test user message formatting."""
        builder = DMPromptBuilder()
        msg = builder.build_user_message("I attack the goblin")

        assert "[Player Action]: I attack the goblin" == msg
