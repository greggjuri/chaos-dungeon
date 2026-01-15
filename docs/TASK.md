# Chaos Dungeon - Task Tracker

## Current Sprint: Inventory System Polish

### In Progress
None currently.

### Up Next
- [ ] init-17-player-agency.md - DM prompt fixes for player agency (stop moral railroading on dark actions)
- [ ] init-19-shops.md - Gold-based item purchases from merchants

---

## Backlog

### Phase 3 - Game Systems (Prioritized)
- [ ] init-19-shops.md - Gold-based item purchases from merchants
- [ ] init-11-dice-rolling.md - Dice mechanics with UI display
- [ ] init-12-leveling.md - XP and level progression

### Phase 4 - Polish
- [ ] init-13-save-slots.md - Multiple characters/campaigns
- [ ] init-14-session-resume.md - Continue saved games
- [ ] init-15-character-sheet.md - Detailed character view

### Phase 5 - Advanced Features
- [ ] Spell system for Magic-Users and Clerics
- [ ] Dungeon generation / procedural content
- [ ] Boss encounters with special mechanics

---

## Completed

### Infrastructure & Foundation
- [x] init-01-project-foundation.md - CDK base stack, DynamoDB, Lambda structure, Frontend shell
- [x] init-02-character-api.md - Character CRUD endpoints with BECMI rules
- [x] init-03-session-api.md - Session CRUD with campaign settings and message history
- [x] init-04-frontend-shell.md - React app with routing, pages, API services, user context, age gate
- [x] prp-11-domain-setup.md - S3/CloudFront/Route53 hosting at chaos.jurigregg.com

### DM & AI System
- [x] init-05-dm-system-prompt.md - DM prompt engineering with BECMI rules, campaign prompts, response parser
- [x] init-06-action-handler.md - DM Lambda with Claude API, action processing, state changes
- [x] prp-09-mistral-dm.md - Migrate DM from Claude Haiku to Mistral Small via AWS Bedrock

### Combat System
- [x] init-07-combat-system.md - Server-side combat resolution with dice, bestiary, combat resolver
- [x] prp-12-turn-based-combat.md - Turn-based combat with targeting, flee mechanics
- [x] prp-14-combat-polish.md - Combat narrator cleanup, enemy numbering, positive constraints

### UI & Game Interface
- [x] init-08-game-ui.md - Chat interface with message history, character status, combat display
- [x] Token counter UI - Debug overlay showing session/global token usage (press T to toggle)

### Cost Control
- [x] prp-10-cost-protection.md - Application-level cost protection with token limits

### Inventory System
- [x] prp-15-inventory-system.md - Server-side inventory, starting equipment, item catalog, USE_ITEM combat action
- [x] prp-16-inventory-fixes.md - Case-insensitive removal, quantity handling
- [x] prp-16a-frontend-inventory-sync.md - Frontend inventory sync from action responses
- [x] prp-16b-inventory-ui-polish.md - Inline quantities, item increment on add
- [x] prp-16c-final-inventory-fixes.md - Auto-focus, quote stripping, expanded keywords
- [x] prp-16d-layout-and-tools.md - Status bar semantic markup, tool keywords
- [x] prp-16e-layout-hotfix.md - Resizable inventory panel, overflow-hidden restore
- [x] prp-16f-scroll-containment.md - Scroll containment wrapper with flex-1 min-h-0
- [x] prp-16g-chathistory-scroll-fix.md - Move scroll to wrapper, ChatHistory fills with h-full
- [x] prp-16h-document-scroll-fix.md - Prevent document-level scrolling with useEffect

### Loot System
- [x] prp-18-loot-tables.md - BECMI-style loot tables, pending loot on victory, server validation
- [x] prp-18a-item-authority.md - Item authority lockdown, DM cannot grant items/gold, server-side loot claim

---

## Architecture Decisions

### Key Learnings from Inventory System (init-15/16)
1. **Positive constraints > negative constraints** - Tell DM what items exist, not what to avoid
2. **Server authority = game integrity** - Dice, combat, inventory all controlled server-side
3. **Manual integration testing is essential** - Unit tests miss frontend-backend integration bugs
4. **Check where functions are called** - Bugs often in invocation, not implementation

### Key Learnings from Layout Fixes (prp-16d-16h)
1. **Flexbox scroll containment requires min-h-0** - Without it, flex items grow to content size
2. **Single scroll container per region** - Don't have nested elements both trying to scroll
3. **Document can scroll independently** - Must set overflow:hidden on html/body to prevent
4. **DevTools is essential** - getBoundingClientRect() and scrollTop reveal true state

### Implemented: Loot Table System (prp-18)
Server-controlled loot replaces free-form item giving:
- BECMI-style weighted loot tables for all bestiary enemies
- Loot rolled on combat victory, stored as pending_loot
- Player must "search" to claim loot (DM prompted in context)
- Gold and items validated against pending loot
- Unclaimed loot lost when new combat starts
- Positive constraints: DM told what loot exists, not what to avoid

### Implemented: Item Authority Lockdown (prp-18a)
Comprehensive lockdown of item/gold acquisition:
- DM CANNOT grant gold (positive gold_delta blocked at server level)
- DM CANNOT grant items (inventory_add blocked at server level)
- Server claims loot when search action detected + pending_loot exists
- DM prompts updated with manipulation resistance examples
- Closes exploit vectors: corpse re-looting, exploration looting, item wishing

---

## Notes

### Configuration
- MAX_SESSIONS_PER_USER: 15
- MAX_MESSAGE_HISTORY: 50
- GLOBAL_DAILY_TOKENS: 500,000
- SESSION_DAILY_TOKENS: 50,000

### Cost Tracking
- Current estimated monthly: ~$5-10 (Mistral Small + AWS)
- Target: < $20/month
- Protection: Real-time token limits (ADR-010)

### Known Issues
- DM sometimes overrides player agency on dark/violent actions (init-17 will fix)

---

*Last updated: 2026-01-15 (item authority lockdown PRP-18a complete)*
