"""Tests for DM response parser."""


from dm.models import DiceRoll, DMResponse, Enemy, StateChanges
from dm.parser import parse_dm_response


class TestParseDMResponse:
    """Tests for parse_dm_response function."""

    def test_parse_valid_response(self) -> None:
        """Test parsing a complete valid response."""
        response = '''The goblin snarls as you swing your sword. Your blade connects with a satisfying thunk, and the creature falls.

```json
{
  "state_changes": {
    "hp_delta": -2,
    "xp_delta": 25,
    "gold_delta": 5
  },
  "dice_rolls": [
    {"type": "attack", "roll": 15, "modifier": 2, "total": 17, "success": true},
    {"type": "damage", "roll": 6, "modifier": 1, "total": 7}
  ],
  "combat_active": false
}
```'''

        result = parse_dm_response(response)

        assert "goblin snarls" in result.narrative
        assert result.state_changes.hp_delta == -2
        assert result.state_changes.xp_delta == 25
        assert result.state_changes.gold_delta == 5
        assert len(result.dice_rolls) == 2
        assert result.dice_rolls[0].type == "attack"
        assert result.dice_rolls[0].success is True
        assert result.combat_active is False

    def test_parse_state_changes_all_fields(self) -> None:
        """Test parsing all state change fields."""
        response = '''You pick up the key and move forward.

```json
{
  "state_changes": {
    "hp_delta": 5,
    "gold_delta": -10,
    "xp_delta": 50,
    "location": "The Secret Chamber",
    "inventory_add": ["golden key", "ancient map"],
    "inventory_remove": ["copper coin"],
    "world_state": {
      "secret_door_found": true,
      "guards_alerted": false
    }
  }
}
```'''

        result = parse_dm_response(response)

        assert result.state_changes.hp_delta == 5
        assert result.state_changes.gold_delta == -10
        assert result.state_changes.xp_delta == 50
        assert result.state_changes.location == "The Secret Chamber"
        assert "golden key" in result.state_changes.inventory_add
        assert "ancient map" in result.state_changes.inventory_add
        assert "copper coin" in result.state_changes.inventory_remove
        assert result.state_changes.world_state["secret_door_found"] is True
        assert result.state_changes.world_state["guards_alerted"] is False

    def test_parse_dice_rolls(self) -> None:
        """Test parsing dice rolls."""
        response = '''The thief attempts to pick the lock.

```json
{
  "state_changes": {},
  "dice_rolls": [
    {"type": "skill", "roll": 12, "modifier": 0, "total": 12, "success": false},
    {"type": "save", "roll": 18, "modifier": -1, "total": 17, "success": true}
  ]
}
```'''

        result = parse_dm_response(response)

        assert len(result.dice_rolls) == 2

        skill_roll = result.dice_rolls[0]
        assert skill_roll.type == "skill"
        assert skill_roll.roll == 12
        assert skill_roll.modifier == 0
        assert skill_roll.total == 12
        assert skill_roll.success is False

        save_roll = result.dice_rolls[1]
        assert save_roll.type == "save"
        assert save_roll.success is True

    def test_parse_combat_state(self) -> None:
        """Test parsing combat state with enemies."""
        response = '''Two goblins emerge from the shadows!

```json
{
  "state_changes": {},
  "combat_active": true,
  "enemies": [
    {"name": "Goblin Warrior", "hp": 6, "ac": 13, "max_hp": 6},
    {"name": "Goblin Archer", "hp": 4, "ac": 11}
  ]
}
```'''

        result = parse_dm_response(response)

        assert result.combat_active is True
        assert len(result.enemies) == 2

        warrior = result.enemies[0]
        assert warrior.name == "Goblin Warrior"
        assert warrior.hp == 6
        assert warrior.ac == 13
        assert warrior.max_hp == 6

        archer = result.enemies[1]
        assert archer.name == "Goblin Archer"
        assert archer.hp == 4
        assert archer.max_hp is None

    def test_parse_no_json(self) -> None:
        """Test parsing response without JSON block."""
        response = "The door creaks open, revealing a dusty chamber beyond. Cobwebs hang from the ceiling."

        result = parse_dm_response(response)

        assert result.narrative == response
        assert result.state_changes.hp_delta == 0
        assert result.state_changes.gold_delta == 0
        assert result.state_changes.xp_delta == 0
        assert result.state_changes.location is None
        assert result.dice_rolls == []
        assert result.combat_active is False
        assert result.enemies == []

    def test_parse_invalid_json(self) -> None:
        """Test parsing response with malformed JSON."""
        response = '''You enter the room.

```json
{not valid json at all}
```'''

        result = parse_dm_response(response)

        # Should return narrative only
        assert "enter the room" in result.narrative
        assert result.state_changes.hp_delta == 0
        assert result.dice_rolls == []

    def test_parse_partial_state_changes(self) -> None:
        """Test parsing with only some state change fields."""
        response = '''You find some gold!

```json
{
  "state_changes": {
    "gold_delta": 15
  }
}
```'''

        result = parse_dm_response(response)

        assert result.state_changes.gold_delta == 15
        assert result.state_changes.hp_delta == 0  # Default
        assert result.state_changes.xp_delta == 0  # Default
        assert result.state_changes.location is None  # Default
        assert result.state_changes.inventory_add == []  # Default

    def test_parse_empty_response(self) -> None:
        """Test parsing empty response."""
        result = parse_dm_response("")

        assert result.narrative == ""
        assert result.state_changes.hp_delta == 0

    def test_parse_whitespace_only(self) -> None:
        """Test parsing whitespace-only response."""
        result = parse_dm_response("   \n\t  ")

        assert result.narrative == ""

    def test_parse_empty_state_changes(self) -> None:
        """Test parsing with empty state_changes object."""
        response = '''Nothing happens.

```json
{"state_changes": {}}
```'''

        result = parse_dm_response(response)

        assert "Nothing happens" in result.narrative
        assert result.state_changes.hp_delta == 0
        assert result.state_changes.inventory_add == []

    def test_parse_preserves_narrative_formatting(self) -> None:
        """Test that narrative preserves original formatting."""
        response = '''The ancient tome reads:

"Beware the shadow that walks."

A chill runs down your spine.

```json
{"state_changes": {}}
```'''

        result = parse_dm_response(response)

        # Narrative should be stripped but otherwise preserved
        assert "ancient tome" in result.narrative
        assert "Beware the shadow" in result.narrative


class TestStateChangesModel:
    """Tests for StateChanges model."""

    def test_defaults(self) -> None:
        """Test that all fields have sensible defaults."""
        state = StateChanges()

        assert state.hp_delta == 0
        assert state.gold_delta == 0
        assert state.xp_delta == 0
        assert state.location is None
        assert state.inventory_add == []
        assert state.inventory_remove == []
        assert state.world_state == {}

    def test_partial_construction(self) -> None:
        """Test construction with partial fields."""
        state = StateChanges(hp_delta=-5, xp_delta=10)

        assert state.hp_delta == -5
        assert state.xp_delta == 10
        assert state.gold_delta == 0


class TestDiceRollModel:
    """Tests for DiceRoll model."""

    def test_full_construction(self) -> None:
        """Test constructing a complete dice roll."""
        roll = DiceRoll(
            type="attack",
            roll=15,
            modifier=3,
            total=18,
            success=True,
        )

        assert roll.type == "attack"
        assert roll.roll == 15
        assert roll.modifier == 3
        assert roll.total == 18
        assert roll.success is True

    def test_optional_success(self) -> None:
        """Test that success is optional."""
        roll = DiceRoll(
            type="damage",
            roll=6,
            modifier=2,
            total=8,
        )

        assert roll.success is None


class TestEnemyModel:
    """Tests for Enemy model."""

    def test_full_construction(self) -> None:
        """Test constructing a complete enemy."""
        enemy = Enemy(
            name="Orc Chieftain",
            hp=25,
            ac=15,
            max_hp=30,
        )

        assert enemy.name == "Orc Chieftain"
        assert enemy.hp == 25
        assert enemy.ac == 15
        assert enemy.max_hp == 30

    def test_optional_max_hp(self) -> None:
        """Test that max_hp is optional."""
        enemy = Enemy(name="Goblin", hp=3, ac=12)

        assert enemy.max_hp is None


class TestDMResponseModel:
    """Tests for DMResponse model."""

    def test_minimal_construction(self) -> None:
        """Test constructing with just narrative."""
        response = DMResponse(narrative="You enter the cave.")

        assert response.narrative == "You enter the cave."
        assert response.state_changes.hp_delta == 0
        assert response.dice_rolls == []
        assert response.combat_active is False
        assert response.enemies == []

    def test_full_construction(self) -> None:
        """Test constructing a complete response."""
        response = DMResponse(
            narrative="Battle begins!",
            state_changes=StateChanges(hp_delta=-5),
            dice_rolls=[DiceRoll(type="attack", roll=10, modifier=2, total=12)],
            combat_active=True,
            enemies=[Enemy(name="Skeleton", hp=5, ac=13)],
        )

        assert response.narrative == "Battle begins!"
        assert response.state_changes.hp_delta == -5
        assert len(response.dice_rolls) == 1
        assert response.combat_active is True
        assert len(response.enemies) == 1
