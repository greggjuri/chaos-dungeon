# init-13-version-display

## Overview

Display the game version number in the UI footer so we can verify deployments are live.

## Requirements

1. Add version number to `package.json` (start at `0.12.0` to match init number)
2. Display version in the UI footer, small and unobtrusive (e.g., "v0.12.0" in bottom-right corner)
3. Version should be visible on all pages (character creation, game, death screen)

## Implementation

- Read version from `package.json` at build time (Vite can do this)
- Create a simple `<Version />` component or just add to existing layout
- Style: small, muted text (gray-500 or similar), fixed position bottom-right or in footer

## Out of Scope

- Backend version endpoint
- Automatic version bumping
- Git tag integration

This is a 15-minute task, no PRP needed.
