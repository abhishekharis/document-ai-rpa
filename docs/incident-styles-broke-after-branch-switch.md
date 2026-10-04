# Incident: Website stopped loading after switching branches

**Severity:** ⭐⭐⭐ Medium — blocked the page, but only on the local dev server.

**Date:** September 30, 2026
**Branch affected:** `feature/ui-redesign`
**Status:** Resolved

## Problem

After the UI redesign, the page failed to load with a red error screen: the
style `shadow-card` "does not exist." It happened twice — once right after the
redesign (fixed by restarting the dev server), and again after switching to
`main` and back. Only the local dev server was affected; production builds
always worked, so the code itself was not broken.

## Root cause

The dev server keeps the Tailwind settings file in memory and, in this setup,
never re-read it. On the first occurrence it was still holding pre-redesign
settings with no `shadow-card`. On the second, it had loaded `main`'s settings
and kept them after switching back — so the redesign's styles asked for
`shadow-card`, which `main` doesn't define, and the page failed.

Underlying reason: the recent Node.js version loads this style of config file
(`main`'s ESM config) into a permanent module cache that Tailwind cannot
clear. Once loaded, the settings stayed until a full server restart.

A quieter symptom existed too: even without the error, the redesign could
render `main`'s old violet colours and font instead of indigo and Inter — the
page loaded but looked half-reverted.

## Approach

- A fresh production build succeeded → problem was specific to the dev server.
- Checked when the server started → it predated the redesign, explaining the
  first occurrence.
- Reproduced the second occurrence: switched to `main`, then back — the server
  kept `main`'s settings after returning.
- Touched the settings file directly — the server still served the old ones,
  so it never reloads them.
- Traced how Tailwind loads its settings → found the Node.js caching quirk.

## Fix

- `shadow-card` is now defined directly in `index.css` — the page can't crash
  over it even if the server holds outdated settings.
- The config was converted to CommonJS (`tailwind.config.js` →
  `tailwind.config.cjs`), which Tailwind reloads properly — the server now
  always uses the current branch's settings.

## Verification

With the same dev server running and no restart, `main` ↔
`feature/ui-redesign` was switched twice: no errors, `main` showed violet,
the feature branch showed indigo + Inter every time. Build passes.

## Takeaways

- The failure came from the dev server's cached settings, not the code.
- Branch switching while the dev server runs is now safe on this branch.
- `main` still uses the old config format — harmless alone, and the fix
  merges in with the redesign.
- If the site shows styling that doesn't match the code, restart `npm run
  dev` first.
