"""Mistral prompt format builder."""


def build_mistral_prompt(
    system_prompt: str,
    context: str,
    action: str,
) -> str:
    """Build Mistral-formatted prompt.

    Mistral uses <s>[INST] format:
    <s>[INST] System prompt + context [/INST]

    Args:
        system_prompt: DM system prompt (identity, rules, guidelines)
        context: Dynamic context (character state, message history)
        action: Player's current action

    Returns:
        Formatted prompt string for Mistral
    """
    # Combine system prompt and context
    full_prompt = f"""<s>[INST] {system_prompt}

{context}

Player action: {action}

Respond as the Dungeon Master. [/INST]"""

    return full_prompt


def build_mistral_prompt_with_history(
    system_prompt: str,
    message_history: list[dict],
    current_action: str,
    character_state: dict,
) -> str:
    """Build Mistral-formatted prompt with conversation history.

    For multi-turn conversations, Mistral expects:
    <s>[INST] System + first message [/INST] Response</s>
    <s>[INST] Next message [/INST] Response</s>
    ...
    <s>[INST] Current action [/INST]

    Args:
        system_prompt: DM system prompt
        message_history: List of {"role": "player"|"dm", "content": str}
        current_action: Player's current action
        character_state: Current character stats

    Returns:
        Formatted prompt string for Mistral
    """
    # Build context block
    context = f"""## CHARACTER STATE
Name: {character_state.get('name', 'Unknown')}
Class: {character_state.get('character_class', 'Unknown')} Level {character_state.get('level', 1)}
HP: {character_state.get('hp', 0)}/{character_state.get('max_hp', 0)}
Gold: {character_state.get('gold', 0)}
XP: {character_state.get('xp', 0)}

## RECENT HISTORY
"""

    # Add recent messages (last 10)
    recent = message_history[-10:] if len(message_history) > 10 else message_history
    for msg in recent:
        role = "Player" if msg["role"] == "player" else "DM"
        context += f"{role}: {msg['content']}\n"

    # Build full prompt
    prompt = f"<s>[INST] {system_prompt}\n\n{context}\n\nPlayer action: {current_action}\n\nRespond as the Dungeon Master. [/INST]"

    return prompt
