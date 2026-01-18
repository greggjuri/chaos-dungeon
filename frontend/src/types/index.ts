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
  item_id?: string;
  name: string;
  quantity: number;
  item_type: string;  // weapon, armor, consumable, quest, misc
  weight?: number;
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
  stats: AbilityScores;  // Backend uses 'stats' field for ability scores
  abilities?: AbilityScores;  // Legacy field, prefer stats
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
  options?: GameOptions;
  created_at: string;
  updated_at?: string;
}

/** Dice roll result from server */
export interface DiceRoll {
  type: string;
  dice: string;
  roll: number;
  modifier: number;
  total: number;
  success: boolean | null;
  attacker?: string;
  target?: string;
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

// ============ Game UI Types ============

/** State changes from action response */
export interface StateChanges {
  hp_delta: number;
  gold_delta: number;
  xp_delta: number;
  location: string | null;
  inventory_add: string[];
  inventory_remove: string[];
  world_state: Record<string, unknown>;
}

/** Enemy in combat */
export interface CombatEnemy {
  id?: string;
  name: string;
  hp: number;
  max_hp: number;
  ac: number;
}

// ============ Turn-Based Combat Types ============

/** Combat phase state */
export type CombatPhase =
  | 'combat_start'
  | 'player_turn'
  | 'resolve_player'
  | 'enemy_turn'
  | 'combat_end';

/** Player combat action types */
export type CombatActionType = 'attack' | 'defend' | 'flee' | 'use_item';

/** Structured combat action */
export interface CombatAction {
  action_type: CombatActionType;
  target_id?: string;
  item_id?: string;
}

/** Combat log entry */
export interface CombatLogEntry {
  round: number;
  actor: string;
  action: string;
  target?: string;
  roll?: number;
  damage?: number;
  result: string;
  narrative: string;
}

/** Full combat state for turn-based UI */
export interface CombatResponse {
  active: boolean;
  round: number;
  phase: CombatPhase;
  your_hp: number;
  your_max_hp: number;
  enemies: CombatEnemy[];
  available_actions: CombatActionType[];
  valid_targets: string[];
  combat_log: CombatLogEntry[];
}

/** Character snapshot from action response */
export interface CharacterSnapshot {
  hp: number;
  max_hp: number;
  xp: number;
  gold: number;
  level: number;
  inventory: Item[];  // Full item objects with quantity, type, etc.
}

/** Token usage statistics for cost monitoring */
export interface UsageStats {
  session_tokens: number;
  session_limit: number;
  global_tokens: number;
  global_limit: number;
}

// ============ Game Options Types ============

/** Gore level preference for violence descriptions */
export type GoreLevel = 'mild' | 'standard' | 'extreme';

/** Mature content preference for romantic/sexual scenes */
export type MatureContentLevel = 'fade_to_black' | 'suggestive' | 'explicit';

/** Player game options stored in session */
export interface GameOptions {
  confirm_combat_noncombat: boolean;
  gore_level: GoreLevel;
  mature_content: MatureContentLevel;
}

/** Default game options */
export const DEFAULT_GAME_OPTIONS: GameOptions = {
  confirm_combat_noncombat: true,
  gore_level: 'standard',
  mature_content: 'suggestive',
};

/** Pending combat confirmation state */
export interface PendingCombatConfirmation {
  target: string;
  original_action: string;
  reason: string;
}

/** Full action response from server */
export interface FullActionResponse {
  narrative: string;
  state_changes: StateChanges;
  dice_rolls: DiceRoll[];
  combat_active: boolean;
  enemies: CombatEnemy[];
  combat?: CombatResponse;
  character: CharacterSnapshot;
  character_dead: boolean;
  session_ended: boolean;
  usage?: UsageStats;
  pending_confirmation?: boolean;
}

/** Response when token limits are reached */
export interface LimitReachedResponse {
  error: 'limit_reached';
  message: string;
}

/** Type guard for limit reached responses */
export function isLimitReached(
  response: FullActionResponse | LimitReachedResponse
): response is LimitReachedResponse {
  return (
    'error' in response &&
    response.error === 'limit_reached' &&
    'message' in response
  );
}

/** Extended message for game UI (includes dice rolls and state changes) */
export interface GameMessage extends Message {
  dice_rolls?: DiceRoll[];
  state_changes?: StateChanges;
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
