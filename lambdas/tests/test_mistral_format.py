"""Tests for Mistral prompt formatting."""


from dm.prompts.mistral_format import (
    build_mistral_prompt,
    build_mistral_prompt_with_history,
)


class TestBuildMistralPrompt:
    """Tests for build_mistral_prompt function."""

    def test_basic_prompt_format(self) -> None:
        """Test basic prompt formatting."""
        prompt = build_mistral_prompt(
            system_prompt="You are a DM",
            context="Character: Grog",
            action="I look around",
        )

        assert prompt.startswith("<s>[INST]")
        assert "[/INST]" in prompt
        assert "You are a DM" in prompt
        assert "Character: Grog" in prompt
        assert "I look around" in prompt

    def test_prompt_ends_with_inst_close(self) -> None:
        """Test that prompt ends with [/INST] for response."""
        prompt = build_mistral_prompt(
            system_prompt="System",
            context="Context",
            action="Action",
        )

        assert prompt.endswith("[/INST]")

    def test_prompt_contains_action_label(self) -> None:
        """Test that player action is properly labeled."""
        prompt = build_mistral_prompt(
            system_prompt="System",
            context="Context",
            action="I attack",
        )

        assert "Player action: I attack" in prompt

    def test_prompt_contains_dm_instruction(self) -> None:
        """Test that prompt includes DM response instruction."""
        prompt = build_mistral_prompt(
            system_prompt="System",
            context="Context",
            action="Action",
        )

        assert "Respond as the Dungeon Master" in prompt


class TestBuildMistralPromptWithHistory:
    """Tests for build_mistral_prompt_with_history function."""

    def test_includes_character_state(self) -> None:
        """Test that character state is included."""
        prompt = build_mistral_prompt_with_history(
            system_prompt="You are a DM",
            message_history=[],
            current_action="I look around",
            character_state={
                "name": "Grog",
                "character_class": "Fighter",
                "level": 3,
                "hp": 25,
                "max_hp": 30,
                "gold": 100,
                "xp": 5000,
            },
        )

        assert "Grog" in prompt
        assert "Fighter Level 3" in prompt
        assert "HP: 25/30" in prompt
        assert "Gold: 100" in prompt
        assert "XP: 5000" in prompt

    def test_includes_message_history(self) -> None:
        """Test that message history is included."""
        history = [
            {"role": "player", "content": "I enter the tavern"},
            {"role": "dm", "content": "You see a crowded room"},
            {"role": "player", "content": "I approach the bar"},
        ]

        prompt = build_mistral_prompt_with_history(
            system_prompt="You are a DM",
            message_history=history,
            current_action="I order an ale",
            character_state={"name": "Test"},
        )

        assert "Player: I enter the tavern" in prompt
        assert "DM: You see a crowded room" in prompt
        assert "Player: I approach the bar" in prompt

    def test_limits_history_to_last_10(self) -> None:
        """Test that only last 10 messages are included."""
        # Create 15 messages
        history = [
            {"role": "player" if i % 2 == 0 else "dm", "content": f"Message {i}"}
            for i in range(15)
        ]

        prompt = build_mistral_prompt_with_history(
            system_prompt="You are a DM",
            message_history=history,
            current_action="Action",
            character_state={"name": "Test"},
        )

        # Should not include first 5 messages
        assert "Message 0" not in prompt
        assert "Message 4" not in prompt

        # Should include last 10 messages
        assert "Message 5" in prompt
        assert "Message 14" in prompt

    def test_handles_empty_history(self) -> None:
        """Test that empty history is handled gracefully."""
        prompt = build_mistral_prompt_with_history(
            system_prompt="You are a DM",
            message_history=[],
            current_action="I look around",
            character_state={"name": "Grog"},
        )

        assert "<s>[INST]" in prompt
        assert "I look around" in prompt

    def test_handles_missing_character_fields(self) -> None:
        """Test that missing character fields use defaults."""
        prompt = build_mistral_prompt_with_history(
            system_prompt="You are a DM",
            message_history=[],
            current_action="Action",
            character_state={},  # Empty state
        )

        assert "Unknown" in prompt  # Default name
        assert "Level 1" in prompt  # Default level
        assert "HP: 0/0" in prompt  # Default HP

    def test_format_matches_mistral_spec(self) -> None:
        """Test that format matches Mistral specification."""
        prompt = build_mistral_prompt_with_history(
            system_prompt="System",
            message_history=[],
            current_action="Action",
            character_state={"name": "Test"},
        )

        # Mistral expects: <s>[INST] ... [/INST]
        assert prompt.startswith("<s>[INST]")
        assert prompt.endswith("[/INST]")
        # Should not have closing </s> since we want a response
        assert "</s>" not in prompt
