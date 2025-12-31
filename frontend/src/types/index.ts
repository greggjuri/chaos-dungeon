/**
 * TypeScript types for Chaos Dungeon frontend.
 * These mirror the backend Pydantic models.
 */

/** BECMI character classes */
export type CharacterClass = 'fighter' | 'thief' | 'magic_user' | 'cleric';

/** Message sender role */
export type MessageRole = 'player' | 'dm';

/** D&D ability scores (3-18 range) */
export interface AbilityScores {
  strength: number;
  intelligence: number;
  wisdom: number;
  dexterity: number;
  constitution: number;
  charisma: number;
}

/** Inventory item */
export interface Item {
  name: string;
  quantity: number;
  weight: number;
  description?: string;
}

/** Game message in session history */
export interface Message {
  role: MessageRole;
  content: string;
  timestamp: string;
}

/** Player character */
export interface Character {
  character_id: string;
  user_id: string;
  name: string;
  character_class: CharacterClass;
  level: number;
  xp: number;
  hp: number;
  max_hp: number;
  gold: number;
  abilities: AbilityScores;
  inventory: Item[];
  created_at: string;
  updated_at?: string;
}

/** Game session with state */
export interface Session {
  session_id: string;
  user_id: string;
  character_id: string;
  campaign_setting: string;
  current_location: string;
  world_state: Record<string, unknown>;
  message_history: Message[];
  created_at: string;
  updated_at?: string;
}

/** Dice roll result */
export interface DiceRoll {
  type: string; // e.g., "d20", "2d6"
  result: number;
  modifier?: number;
  success?: boolean;
}

/** API response wrapper */
export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}

/** Create character request */
export interface CreateCharacterRequest {
  name: string;
  character_class: CharacterClass;
  abilities: AbilityScores;
}

/** Player action request */
export interface ActionRequest {
  action: string;
}

/** DM response with potential state changes */
export interface ActionResponse {
  message: Message;
  dice_rolls?: DiceRoll[];
  state_changes?: Record<string, unknown>;
}
