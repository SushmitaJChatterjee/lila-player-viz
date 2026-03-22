## What I Built
A browser-based visualization tool for LILA BLACK's Level Design team
to explore player behavior across 3 maps and 5 days of match data.

## Tech Stack

| Tool | Purpose | Why I chose it |
|---|---|---|
| Python | Data processing | README used Python examples |
| Streamlit | Web framework | Write Python, get a website — no HTML needed |
| Pandas + PyArrow | Read parquet files | Fast and handles the bytes encoding |
| Plotly | Interactive maps and heatmaps | Supports image backgrounds + interactive markers |
| Pillow | Load minimap images | Simple image loading |
| Streamlit Cloud | Hosting | Free, one-click deploy from GitHub |

## How Data Flows
```
Parquet files (1243 files across 5 folders)
        ↓
PyArrow reads each file → Pandas DataFrame
        ↓
Decode event column from bytes → string
        ↓
Tag each row: is_bot (numeric ID = bot, UUID = human)
        ↓
Convert world coordinates (x, z) → pixel coordinates
        ↓
Plotly renders dots/lines on top of minimap image
        ↓
Streamlit serves everything in the browser
```

## Coordinate Mapping Approach

The game uses 3D world coordinates (x, y, z).
For 2D minimap display I only use x and z (y = elevation, ignored).

Each map has a scale and origin defined in the README:
```
u = (x - origin_x) / scale
v = (z - origin_z) / scale
pixel_x = u * 1024
pixel_y = (1 - v) * 1024   ← Y is flipped (image origin is top-left)
```

The Y flip was the trickiest part — without it all dots appear 
mirrored vertically on the map.

## Assumptions Made

- Files with no .parquet extension are valid parquet files (confirmed 
  by README)
- Bot detection: user_id shorter than 10 chars or fully numeric = bot
- February 14 is partial data (noted in README) — included anyway
- Timestamps represent time elapsed in match, not wall clock time

## Trade-offs

| Decision | Alternative | Why I chose this |
|---|---|---|
| Streamlit | React + FastAPI | Much faster to build, good enough for internal tool |
| Load all files at startup | On-demand loading | Simpler code, data is only 25MB total |
| Plotly scatter for paths | Canvas/WebGL | Easier to add hover tooltips and interactivity |
| Streamlit Cloud | Vercel/Railway | Native Streamlit support, zero config |

## What I'd Do With More Time

- Add animation — watch a match play back frame by frame
- Player comparison — put two players side by side
- Survival analysis — how long do players survive before dying to storm
- Mobile-friendly layout
- Faster loading using DuckDB instead of loading all files into memory