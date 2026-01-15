# init-16h-document-scroll-fix

## Overview

Fix document-level scrolling. DevTools confirmed the `<html>` element is scrolling (scrollTop: 182), not our wrapper.

## Problem (from DevTools)

```
HTML scrollTop: 182        // Document is scrolling!
Body height: 1286          // Body is taller than viewport
Window height: 1023        // Viewport height
```

The game container has `h-screen overflow-hidden` but the `<html>` element itself is scrollable because the body is taller than the viewport (1286 > 1023).

## Solution

Prevent document-level scrolling by adding `overflow: hidden` to `<html>` and `<body>` when on the game page.

### Option A: Global CSS (in index.css)
```css
html, body {
  overflow: hidden;
  height: 100%;
}
```

### Option B: useEffect in GamePage (scoped to game page only)
```tsx
useEffect(() => {
  // Prevent document scrolling on game page
  document.documentElement.style.overflow = 'hidden';
  document.body.style.overflow = 'hidden';
  
  return () => {
    // Restore on unmount
    document.documentElement.style.overflow = '';
    document.body.style.overflow = '';
  };
}, []);
```

Option B is better because it only affects the game page, not other pages like character selection.

## Files to Modify

```
frontend/src/pages/GamePage.tsx    # Add useEffect to disable document scroll
```

## Implementation

Add this useEffect near the top of GamePage component:

```tsx
// Prevent document-level scrolling on game page
useEffect(() => {
  const html = document.documentElement;
  const body = document.body;
  
  // Save original values
  const originalHtmlOverflow = html.style.overflow;
  const originalBodyOverflow = body.style.overflow;
  
  // Disable scrolling
  html.style.overflow = 'hidden';
  body.style.overflow = 'hidden';
  
  return () => {
    // Restore on unmount
    html.style.overflow = originalHtmlOverflow;
    body.style.overflow = originalBodyOverflow;
  };
}, []);
```

## Acceptance Criteria

- [ ] `document.documentElement.scrollTop` returns 0
- [ ] Header visible on page load without scrolling
- [ ] Chat scrolls inside wrapper, not document
- [ ] Other pages (character select, etc.) still scroll normally

## Cost Impact

$0 - CSS/JS only
