# Prama brand

**Ask. Verify. Know.** — Answers you can check.

Prama comes from Sanskrit *pramāṇa*: a valid source of knowledge, or evidence. The mark is a lowercase P whose bowl is a lens, with the source — the amber dot — at its centre.

## Palette

| Token | Hex | Use |
| --- | --- | --- |
| Cream | `#F4F1E7` | Primary background |
| Paper | `#FBF8EF` | Raised surfaces |
| Ink | `#14151D` | Type and mark |
| Amber | `#F5A800` | Source dot, primary actions |
| Amber soft | `#FCEBC2` | Citation and selected states |
| Amber deep | `#7A5200` | Text on amber-soft |
| Line | `#DDD6C3` | Borders and dividers |
| Muted | `#6C675C` | Secondary text |

## Files

| File | Description |
| --- | --- |
| `prama-logo.svg` | Primary lockup, ink on cream, 480 × 160 |
| `prama-logo-reversed.svg` | Reversed lockup, cream on ink, 480 × 160 |
| `prama-mark.svg` | Transparent ink mark |
| `prama-mark-light.svg` | Transparent cream mark for dark surfaces |
| `prama-app-icon.svg` | Rounded app icon, 512 × 512 |
| `prama-mark-amber.svg` | One-colour mark on amber, 512 × 512 |
| `prama-favicon-32.svg` | Favicon, 32 × 32 |
| `prama-favicon-16.svg` | Favicon, 16 × 16 |

The app consumes `prama-app-icon.svg` through `frontend/app/icon.svg` and draws the mark inline in the UI.

## Type

The wordmark is **Montserrat SemiBold** with tight tracking (−0.028 em), converted to outlines in the SVG lockups so it renders identically everywhere. The app self-hosts the variable font at `frontend/public/fonts/Montserrat-Variable.ttf` under the SIL Open Font License (`OFL.txt`). Body copy uses the system UI sans.

## Usage

- Use the primary lockup on cream and the reversed lockup on ink.
- Keep clear space around the lockup equal to the height of the bowl.
- Do not recolor the amber dot, outline the wordmark, stretch the mark, or add effects.
- For small sizes, use the app icon or favicon files rather than the full lockup.
- When the lockup cannot be used, pair the mark with the name **Prama** in Montserrat SemiBold.
