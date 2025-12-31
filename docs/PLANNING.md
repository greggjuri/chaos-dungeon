# Chaos Dungeon - Project Planning

## Project Vision

A text-based RPG web game hosted at **chaos.jurigregg.com** where Claude serves as an intelligent Dungeon Master. Based on D&D 1983 BECMI Rules (Basic, Expert, Companion, Master). The game features mature, graphic content with intense combat and dark fantasy themes.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                     │
│                  React + TypeScript + Tailwind                       │
│                    S3 + CloudFront                                   │
│                  chaos.jurigregg.com                                 │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       API GATEWAY                                    │
│                    REST API + CORS                                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       LAMBDA FUNCTIONS                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                 │
│  │  Character  │  │   Session   │  │     DM      │                 │
│  │   Handler   │  │   Handler   │  │   Handler   │                 │
│  └─────────────┘  └─────────────┘  └─────────────┘                 │
└─────────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│    DynamoDB     │  │   Claude API    │  │  Secrets Mgr    │
│    (State)      │  │   (Haiku 3)     │  │   (API Key)     │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## Cost Budget: $20/month Maximum

### Claude API (Haiku 3) - Target: $10-15/month
- Pricing: $0.25/1M input tokens, $1.25/1M output tokens
- Per action (~2000 tokens): ~$0.0015
- Monthly budget allows: ~10,000 actions
- Average player: 50-100 actions/session, 3-5 sessions/week

### AWS Services - Target: $5-10/month
| Service | Est. Cost | Notes |
|---------|-----------|-------|
| Lambda | $0-1 | 1M free requests/month |
| API Gateway | $1-3 | $3.50/1M requests |
| DynamoDB | $1-3 | On-demand, ~$1.25/1M writes |
| S3 + CloudFront | $1-2 | Minimal static hosting |
| Secrets Manager | $0.40 | 1 secret |
| Route 53 | $0.50 | Hosted zone |

### Cost Optimization Strategies
1. Use Claude Haiku 3 (cheapest model)
2. Prompt caching for system prompts (90% savings on cached tokens)
3. Compact game state serialization
4. DynamoDB on-demand (no reserved capacity)
5. CloudFront caching for static assets

## Tech Stack

### Frontend
- **Framework**: React 18 + TypeScript
- **Styling**: Tailwind CSS
- **Build**: Vite
- **State**: React Context + useReducer
- **HTTP**: fetch (native)

### Backend
- **Runtime**: Python 3.12
- **Framework**: AWS Lambda + API Gateway
- **Validation**: Pydantic
- **Logging**: AWS Lambda Powertools
- **AI**: Claude API (Haiku 3)

### Infrastructure
- **IaC**: AWS CDK (Python)
- **CI/CD**: GitHub Actions (later)
- **Domain**: chaos.jurigregg.com (*.jurigregg.com cert exists)

## Data Models

### Character (DynamoDB)
```
PK: USER#{user_id}
SK: CHAR#{character_id}
Attributes:
  - name: string
  - class: warrior|rogue|mage|cleric
  - level: 1-36 (BECMI max)
  - xp: number
  - hp: number
  - max_hp: number
  - gold: number
  - inventory: list[Item]
  - abilities: list[string]
  - stats: {str, int, wis, dex, con, cha}
  - created_at: ISO timestamp
  - updated_at: ISO timestamp
```

### Session (DynamoDB)
```
PK: USER#{user_id}
SK: SESS#{session_id}
Attributes:
  - character_id: string
  - campaign_setting: string
  - current_location: Location
  - main_quest: Quest
  - quest_log: list[Quest]
  - world_state: map (flags like "dragon_slain")
  - npc_memory: list[NPCMemory]
  - message_history: list[Message] (last 20)
  - created_at: ISO timestamp
  - updated_at: ISO timestamp
```

### Message
```
{
  role: "player" | "dm"
  content: string
  timestamp: ISO string
  dice_rolls?: list[DiceRoll]
  state_changes?: list[StateChange]
}
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /characters | Create character |
| GET | /characters | List user's characters |
| GET | /characters/{id} | Get character details |
| DELETE | /characters/{id} | Delete character |
| POST | /sessions | Start new game |
| GET | /sessions/{id} | Load session |
| POST | /sessions/{id}/action | Player action → DM response |
| GET | /sessions/{id}/history | Get message history |

## D&D BECMI Rules Integration

### Character Classes (Phase 1 - Basic)
1. **Fighter** - High HP, combat focus, all weapons/armor
2. **Thief** - Skills, backstab, light armor
3. **Magic-User** - Spells, low HP, no armor
4. **Cleric** - Healing, turn undead, medium armor

### Core Mechanics
- **Ability Scores**: 3d6 for STR, INT, WIS, DEX, CON, CHA
- **Combat**: d20 + modifiers vs AC (descending in BECMI, we'll use ascending)
- **Saving Throws**: By class, vs Death Ray, Wands, Paralysis, Breath, Spells
- **Experience**: Class-based XP tables
- **Levels**: 1-14 (Basic/Expert), expandable to 36 (Companion/Master)

### Spell System (Simplified)
- Magic-Users: Intelligence-based, Vancian (memorize/forget)
- Clerics: Wisdom-based, granted by deity
- Spell slots by level

## Project Structure

```
chaos-dungeon/
├── CLAUDE.md                    # Project rules for Claude Code
├── docs/
│   ├── PLANNING.md              # This file
│   ├── TASK.md                  # Current tasks
│   └── DECISIONS.md             # Architecture decisions
├── initials/                    # Feature specifications (init-*.md)
├── prps/                        # Implementation plans (prp-*.md)
│   └── templates/
│       └── prp-template.md
├── .claude/
│   └── commands/
│       ├── generate-prp.md
│       └── execute-prp.md
├── examples/                    # Code patterns for Claude Code
│   ├── lambda/
│   ├── cdk/
│   └── frontend/
├── cdk/                         # Infrastructure as Code
│   ├── app.py
│   ├── stacks/
│   └── requirements.txt
├── lambdas/                     # Backend code
│   ├── shared/                  # Shared utilities
│   ├── character/               # Character CRUD
│   ├── session/                 # Session management
│   ├── dm/                      # DM/AI handler
│   └── requirements.txt
├── frontend/                    # React app
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── types/
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## Development Phases

### Phase 1: Foundation (Week 1)
- [ ] Project structure setup
- [ ] CDK infrastructure (DynamoDB, Lambda, API Gateway)
- [ ] Basic character CRUD API
- [ ] Simple frontend shell

### Phase 2: Core Game Loop (Week 2)
- [ ] DM system prompt engineering
- [ ] Action processing Lambda
- [ ] Game UI with message history
- [ ] State parsing and persistence

### Phase 3: Game Systems (Week 3)
- [ ] Combat encounters (BECMI rules)
- [ ] Inventory management
- [ ] Dice rolling with visual feedback
- [ ] XP and leveling

### Phase 4: Polish (Week 4)
- [ ] Multiple save slots
- [ ] Session resume
- [ ] Character sheet UI
- [ ] Mobile responsive
- [ ] Domain setup (chaos.jurigregg.com)

### Future Phases
- Expert-level content (levels 4-14)
- Companion rules (levels 15-25)
- Master rules (levels 26-36)
- Multiplayer party system
- AI-generated images (budget permitting)

## Key Constraints

1. **500-line file limit** - Split into modules when approaching
2. **Commit after each feature** - Atomic, working commits
3. **$20/month budget** - Monitor Claude API usage
4. **BECMI authenticity** - Follow 1983 rules where practical
5. **Mobile-first** - Responsive design from start

## Success Criteria

1. ✅ Create character and start adventure
2. ✅ Natural conversation with AI DM
3. ✅ Combat with BECMI dice mechanics
4. ✅ State persists across sessions
5. ✅ World consistency (NPCs remember, consequences persist)
6. ✅ Complete simple quest arc (1-2 hours gameplay)
7. ✅ Monthly AWS costs under $20
