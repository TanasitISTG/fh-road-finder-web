# FH Road Finder (Web)

A fully browser-based tool that detects possible undiscovered roads in Forza Horizon map screenshots by scanning for pixels matching a target grey colour.

No installation needed. No server. No uploads. Everything runs locally in your browser.

## How It Works

1. Open `index.html` in any modern browser (Chrome, Edge, Firefox).
2. Upload or drag-and-drop a Forza Horizon map screenshot.
3. Configure the target RGB (default 128,128,128), tolerance, and output mode.
4. Click **Scan Image**.
5. The tool compares every pixel against the target colour using per-channel distance:
   - `abs(R - targetR) <= tolerance AND abs(G - targetG) <= tolerance AND abs(B - targetB) <= tolerance`
6. Matching pixels are highlighted in the chosen output mode.
7. Download the result as PNG.

## Privacy

**All image processing happens locally in your browser.** Your screenshots are never uploaded to any server. The tool works entirely offline after the page loads.

## Output Modes

- **Overlay** — original image with matched pixels blended in red (configurable).
- **Black highlight mask** — black background with matched pixels in red.
- **Transparent mask** — transparent background with matched pixels in red. Useful for layering over other images.

## Tolerance Guide

Tolerance controls how close a pixel must be to the target colour (per channel) to count as a match.

| Value | Name | Best for |
|-------|------|----------|
| 0 | Ultra strict | Clean PNG screenshots only |
| 1 | Strict | Clean PNG screenshots |
| 2 | Normal | Good default for PNG |
| 5 | Loose | Recommended for JPEG screenshots |
| 8 | Very loose | Wide net, more false positives |

**Why does JPEG need higher tolerance?** JPEG compression shifts pixel colours. A pixel that was exactly (128,128,128) in-game may become (126,129,127) in a saved JPEG. Higher tolerance compensates for this. For best results, save your screenshots as PNG.

## Use Locally

Just open `index.html` in your browser. No server needed — it works via `file://`.

## Deploy on GitHub Pages

1. Push the `fh-road-finder-web/` folder to a GitHub repository.
2. Go to **Settings > Pages**.
3. Set source to the branch and folder containing `index.html`.
4. The `.nojekyll` file is included to prevent Jekyll processing.
5. Your tool will be live at `https://yourusername.github.io/your-repo/`.

## Screenshot Tips

- Use **PNG** format for best accuracy (Win+Shift+S, paste into Paint, save as PNG).
- Zoom the in-game map so the area of interest fills the screen.
- Avoid UI overlays (menus, tooltips, popups) covering the map.
- If using JPEG, start with tolerance 5.

## Credits

Built for the Forza Horizon community. Open source, no dependencies, no tracking.
