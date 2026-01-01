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

// ============ API Response Types ============

/** Campaign setting options */
export type CampaignSetting =
  | 'default'
  | 'dark_forest'
  | 'cursed_castle'
  | 'forgotten_mines';

/** Character summary for list view */
export interface CharacterSummary {
  character_id: string;
  name: string;
  character_class: CharacterClass;
  level: number;
  created_at: string;
}

/** Response from GET /characters */
export interface CharacterListResponse {
  characters: CharacterSummary[];
}

/** Session summary for list view */
export interface SessionSummary {
  session_id: string;
  character_id: string;
  character_name: string;
  campaign_setting: CampaignSetting;
  current_location: string;
  created_at: string;
  updated_at: string | null;
}

/** Response from GET /sessions */
export interface SessionListResponse {
  sessions: SessionSummary[];
}

/** Request to create a session */
export interface SessionCreateRequest {
  character_id: string;
  campaign_setting?: CampaignSetting;
}

/** Response from POST /sessions */
export interface SessionCreateResponse {
  session_id: string;
  character_id: string;
  campaign_setting: CampaignSetting;
  current_location: string;
  world_state: Record<string, unknown>;
  message_history: Message[];
  created_at: string;
}

/** Response from GET /sessions/{id}/history */
export interface MessageHistoryResponse {
  messages: Message[];
  has_more: boolean;
  next_cursor: string | null;
}

// ============ Error Types ============

/** API error response body */
export interface ApiErrorBody {
  error: string;
  details?: Record<string, unknown>;
}

/** Custom error for API requests */
export class ApiRequestError extends Error {
  constructor(
    public status: number,
    public error: string,
    public details?: Record<string, unknown>
  ) {
    super(error);
    this.name = 'ApiRequestError';
  }
}
