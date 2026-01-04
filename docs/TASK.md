# Chaos Dungeon - Task Tracker

## Current Sprint: Foundation

### In Progress
- None

### To Do (Phase 1 - Foundation)
- (completed)

### To Do (Phase 2 - Core Game Loop)
- [x] init-06-action-handler.md - Process player actions
- [x] init-08-game-ui.md - Chat interface with message history
- [ ] init-08-state-parsing.md - Parse DM responses for state changes

### To Do (Phase 3 - Game Systems)
- [x] init-07-combat-system.md - Server-side combat resolution
- [ ] init-10-inventory.md - Item management
- [ ] init-11-dice-rolling.md - Dice mechanics with UI
- [ ] init-12-leveling.md - XP and level progression

### To Do (Phase 4 - Polish)
- [ ] init-13-save-slots.md - Multiple characters/campaigns
- [ ] init-14-session-resume.md - Continue saved games
- [ ] init-15-character-sheet.md - Detailed character view
- [ ] init-16-domain-setup.md - chaos.jurigregg.com deployment

### Completed
- [x] Initial project planning (PLANNING.md)
- [x] Claude Code instructions (CLAUDE.md)
- [x] init-01-project-foundation.md - CDK base stack, DynamoDB, Lambda structure, Frontend shell
- [x] init-02-character-api.md - Character CRUD endpoints with BECMI rules
- [x] init-03-session-api.md - Session CRUD with campaign settings and message history
- [x] init-04-frontend-shell.md - React app with routing, pages, API services, user context, age gate
- [x] init-05-dm-system-prompt.md - DM prompt engineering with BECMI rules, campaign prompts, response parser
- [x] init-06-action-handler.md - DM Lambda with Claude API, action processing, state changes
- [x] init-07-combat-system.md - Server-side combat resolution with dice, bestiary, combat resolver
- [x] init-08-game-ui.md - Chat interface with message history, character status, combat display
- [x] prp-09-mistral-dm.md - Migrate DM from Claude Haiku to Mistral Small via AWS Bedrock

---

## Notes

### Blockers
None currently.

### Questions to Resolve
1. ~~Anonymous sessions vs Cognito auth for MVP?~~ - Resolved: Anonymous sessions per ADR-005
2. Preset starting scenarios vs fully procedural?

### Cost Tracking
- Current estimated monthly: $0 (not deployed)
- Target: < $20/month

---

*Last updated: 2026-01-04 (prp-09 Mistral DM migration complete)*
