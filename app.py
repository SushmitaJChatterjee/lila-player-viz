import streamlit as st
import pandas as pd
import pyarrow.parquet as pq
import plotly.graph_objects as go
import plotly.express as px
import os
from PIL import Image

# ─── PAGE SETUP ───────────────────────────────────────────
st.set_page_config(
    page_title="LILA BLACK - Player Journey Tool",
    page_icon="🎮",
    layout="wide"
)

st.title("🎮 LILA BLACK — Player Journey Visualizer")
st.caption("Built for Level Designers to explore player behavior on maps")

# ─── CONSTANTS ────────────────────────────────────────────
DATA_PATH = "player_data"
MINIMAP_PATH = os.path.join(DATA_PATH, "minimaps")

MAP_CONFIG = {
    "AmbroseValley": {"scale": 900,  "origin_x": -370, "origin_z": -473, "image": "AmbroseValley_Minimap.png"},
    "GrandRift":     {"scale": 581,  "origin_x": -290, "origin_z": -290, "image": "GrandRift_Minimap.png"},
    "Lockdown":      {"scale": 1000, "origin_x": -500, "origin_z": -500, "image": "Lockdown_Minimap.jpg"},
}

EVENT_COLORS = {
    "Position":       "#4A9EFF",
    "BotPosition":    "#888888",
    "Kill":           "#FF4444",
    "Killed":         "#FF8C00",
    "BotKill":        "#FF6B6B",
    "BotKilled":      "#FFA07A",
    "KilledByStorm":  "#9B59B6",
    "Loot":           "#2ECC71",
}

DATES = ["February_10", "February_11", "February_12", "February_13", "February_14"]

# ─── HELPER FUNCTIONS ─────────────────────────────────────

def is_bot(user_id):
    """Bots have numeric IDs, humans have UUIDs"""
    return str(user_id).replace("-", "").isdigit() or (len(str(user_id)) < 10)

def world_to_pixel(x, z, map_name):
    """Convert game world coordinates to minimap pixel coordinates"""
    cfg = MAP_CONFIG[map_name]
    u = (x - cfg["origin_x"]) / cfg["scale"]
    v = (z - cfg["origin_z"]) / cfg["scale"]
    pixel_x = u * 1024
    pixel_y = (1 - v) * 1024
    return pixel_x, pixel_y

@st.cache_data
def load_data(selected_dates, selected_map):
    """Load all parquet files for selected dates and map"""
    frames = []
    for date in selected_dates:
        folder = os.path.join(DATA_PATH, date)
        if not os.path.exists(folder):
            continue
        for filename in os.listdir(folder):
            filepath = os.path.join(folder, filename)
            try:
                df = pq.read_table(filepath).to_pandas()
                df['event'] = df['event'].apply(
                    lambda x: x.decode('utf-8') if isinstance(x, bytes) else x
                )
                df['date'] = date
                df['is_bot'] = df['user_id'].apply(is_bot)
                frames.append(df)
            except:
                continue

    if not frames:
        return pd.DataFrame()

    full_df = pd.concat(frames, ignore_index=True)
    full_df = full_df[full_df['map_id'] == selected_map]
    return full_df

# ─── SIDEBAR FILTERS ──────────────────────────────────────
st.sidebar.header("🔎 Filters")

selected_map = st.sidebar.selectbox(
    "Select Map",
    options=list(MAP_CONFIG.keys()),
    index=0
)

selected_dates = st.sidebar.multiselect(
    "Select Dates",
    options=DATES,
    default=["February_10"]
)

show_humans = st.sidebar.checkbox("Show Human Players", value=True)
show_bots = st.sidebar.checkbox("Show Bots", value=False)

all_events = list(EVENT_COLORS.keys())
selected_events = st.sidebar.multiselect(
    "Select Event Types",
    options=all_events,
    default=["Position", "Kill", "Killed", "KilledByStorm", "Loot"]
)

# ─── LOAD DATA ────────────────────────────────────────────
if not selected_dates:
    st.warning("Please select at least one date from the sidebar.")
    st.stop()

with st.spinner("Loading match data..."):
    df = load_data(tuple(selected_dates), selected_map)

if df.empty:
    st.error("No data found for the selected map and dates.")
    st.stop()

# ─── MATCH FILTER ─────────────────────────────────────────
all_matches = df['match_id'].unique().tolist()
selected_match = st.sidebar.selectbox(
    "Select Match",
    options=["All Matches"] + all_matches[:50],
)

if selected_match != "All Matches":
    df = df[df['match_id'] == selected_match]

# Apply filters
if not show_humans:
    df = df[df['is_bot'] == True]
if not show_bots:
    df = df[df['is_bot'] == False]
if selected_events:
    df = df[df['event'].isin(selected_events)]

# ─── STATS ROW ────────────────────────────────────────────
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Events", f"{len(df):,}")
col2.metric("Unique Players", df['user_id'].nunique())
col3.metric("Matches", df['match_id'].nunique())
col4.metric("Map", selected_map)
st.markdown("---")

# ─── MAIN MAP VISUALIZATION ───────────────────────────────
st.subheader(f"🗺️ Player Journeys on {selected_map}")

# Load minimap image
minimap_file = MAP_CONFIG[selected_map]["image"]
minimap_path = os.path.join(MINIMAP_PATH, minimap_file)

try:
    minimap_img = Image.open(minimap_path)
except:
    st.error(f"Could not load minimap image: {minimap_path}")
    st.stop()

# Convert coordinates
df['pixel_x'], df['pixel_y'] = zip(*df.apply(
    lambda row: world_to_pixel(row['x'], row['z'], selected_map), axis=1
))

# ─── BUILD PLOTLY FIGURE ──────────────────────────────────
fig = go.Figure()

# Add minimap as background
fig.add_layout_image(
    dict(
        source=minimap_img,
        xref="x", yref="y",
        x=0, y=0,
        sizex=1024, sizey=1024,
        sizing="stretch",
        layer="below"
    )
)

# ── SINGLE MATCH: Draw player paths as lines ──────────────
if selected_match != "All Matches":
    path_df = df[df['event'] == 'Position'].sort_values('ts')
    players = path_df['user_id'].unique()
    colors = px.colors.qualitative.Plotly + px.colors.qualitative.Dark24

    for i, player_id in enumerate(players):
        player_path = path_df[path_df['user_id'] == player_id]
        if len(player_path) < 2:
            continue
        color = colors[i % len(colors)]
        label = "Bot" if is_bot(player_id) else "Human"

        fig.add_trace(go.Scatter(
            x=player_path['pixel_x'],
            y=player_path['pixel_y'],
            mode='lines+markers',
            line=dict(color=color, width=2),
            marker=dict(size=3, color=color),
            opacity=0.7,
            name=f"{label}: {str(player_id)[:8]}",
            hovertemplate=f"<b>{label}</b><br>{str(player_id)[:8]}<extra></extra>"
        ))

    # Draw start dot (green) and end dot (red) for each player
    for i, player_id in enumerate(players):
        player_path = path_df[path_df['user_id'] == player_id].sort_values('ts')
        if player_path.empty:
            continue

        # Start point
        fig.add_trace(go.Scatter(
            x=[player_path.iloc[0]['pixel_x']],
            y=[player_path.iloc[0]['pixel_y']],
            mode='markers',
            marker=dict(symbol='circle', color='lime', size=10,
                       line=dict(color='white', width=1.5)),
            name='Start',
            showlegend=(i == 0),
            hovertemplate="<b>Start</b><extra></extra>"
        ))

        # End point
        fig.add_trace(go.Scatter(
            x=[player_path.iloc[-1]['pixel_x']],
            y=[player_path.iloc[-1]['pixel_y']],
            mode='markers',
            marker=dict(symbol='x', color='white', size=10,
                       line=dict(color='white', width=2)),
            name='End',
            showlegend=(i == 0),
            hovertemplate="<b>End</b><extra></extra>"
        ))

# ── Draw EVENTS as bold markers on top ────────────────────
event_styles = {
    'Kill':          ('#FF4444', 'circle', 12),
    'Killed':        ('#FF8C00', 'circle', 12),
    'BotKill':       ('#FF6B6B', 'circle', 9),
    'BotKilled':     ('#FFA07A', 'circle', 9),
    'KilledByStorm': ('#9B59B6', 'diamond', 14),
    'Loot':          ('#2ECC71', 'star',   10),
}

for event_type in selected_events:
    if event_type in ['Position', 'BotPosition']:
        # Only show positions as dots when all matches selected
        if selected_match == "All Matches":
            event_df = df[df['event'] == event_type]
            if not event_df.empty:
                color = EVENT_COLORS.get(event_type, '#FFFFFF')
                fig.add_trace(go.Scatter(
                    x=event_df['pixel_x'],
                    y=event_df['pixel_y'],
                    mode='markers',
                    marker=dict(color=color, size=3, opacity=0.4),
                    name=event_type,
                    hoverinfo='skip'
                ))
        continue

    event_df = df[df['event'] == event_type]
    if event_df.empty:
        continue

    color, symbol, size = event_styles.get(event_type, ('#FFFFFF', 'circle', 8))

    fig.add_trace(go.Scatter(
        x=event_df['pixel_x'],
        y=event_df['pixel_y'],
        mode='markers',
        marker=dict(
            symbol=symbol,
            color=color,
            size=size,
            opacity=0.95,
            line=dict(color='white', width=1)
        ),
        name=event_type,
        text=event_df['user_id'].apply(lambda x: str(x)[:8]),
        hovertemplate="<b>%{text}</b><br>" + event_type + "<extra></extra>"
    ))

# ─── MAP LAYOUT ───────────────────────────────────────────
fig.update_layout(
    xaxis=dict(range=[0, 1024], showgrid=False, zeroline=False, showticklabels=False),
    yaxis=dict(range=[1024, 0], showgrid=False, zeroline=False,
               showticklabels=False, scaleanchor="x"),
    margin=dict(l=0, r=0, t=0, b=0),
    height=700,
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    legend=dict(
        bgcolor='rgba(0,0,0,0.6)',
        font=dict(color='white', size=11),
        bordercolor='rgba(255,255,255,0.2)',
        borderwidth=1
    )
)

st.plotly_chart(fig, use_container_width=True)

# ─── TIP ──────────────────────────────────────────────────
if selected_match == "All Matches":
    st.info("💡 Tip: Select a specific match from the sidebar to see player paths as lines!")

# ─── HEATMAP ──────────────────────────────────────────────
st.markdown("---")
st.subheader("🔥 Heatmap — Where things happened most")

heatmap_event = st.selectbox(
    "Choose event to heatmap",
    options=["All Events", "Kill", "Killed", "KilledByStorm", "Loot", "Position"]
)

heat_df = df.copy()
if heatmap_event != "All Events":
    heat_df = heat_df[heat_df['event'] == heatmap_event]

fig2 = go.Figure()

fig2.add_layout_image(
    dict(
        source=minimap_img,
        xref="x", yref="y",
        x=0, y=0,
        sizex=1024, sizey=1024,
        sizing="stretch",
        layer="below"
    )
)

fig2.add_trace(go.Histogram2dContour(
    x=heat_df['pixel_x'],
    y=heat_df['pixel_y'],
    colorscale='Hot',
    reversescale=True,
    opacity=0.6,
    showscale=True,
    nbinsx=40,
    nbinsy=40,
    contours=dict(showlines=False)
))

fig2.update_layout(
    xaxis=dict(range=[0, 1024], showgrid=False, zeroline=False, showticklabels=False),
    yaxis=dict(range=[1024, 0], showgrid=False, zeroline=False,
               showticklabels=False, scaleanchor="x"),
    margin=dict(l=0, r=0, t=0, b=0),
    height=700,
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
)

st.plotly_chart(fig2, use_container_width=True)

# ─── EVENT BREAKDOWN TABLE ────────────────────────────────
st.markdown("---")
st.subheader("📊 Event Breakdown")
event_counts = df['event'].value_counts().reset_index()
event_counts.columns = ['Event', 'Count']
st.dataframe(event_counts, use_container_width=True)

# ─── MATCH TIMELINE ───────────────────────────────────────
if selected_match != "All Matches":
    st.markdown("---")
    st.subheader("⏱️ Match Timeline")

    timeline_df = df.sort_values('ts')
    timeline_df['time_seconds'] = (
        (timeline_df['ts'] - timeline_df['ts'].min())
        .dt.total_seconds()
    )

    fig3 = go.Figure()

    for event_type in ['Kill', 'Killed', 'KilledByStorm', 'Loot']:
        e_df = timeline_df[timeline_df['event'] == event_type]
        if e_df.empty:
            continue
        color = EVENT_COLORS.get(event_type, '#FFFFFF')
        fig3.add_trace(go.Scatter(
            x=e_df['time_seconds'],
            y=[event_type] * len(e_df),
            mode='markers',
            marker=dict(color=color, size=10, opacity=0.8),
            name=event_type,
            text=e_df['user_id'].apply(lambda x: str(x)[:8]),
            hovertemplate="<b>%{text}</b><br>%{x:.0f}s<extra></extra>"
        ))

    fig3.update_layout(
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0.3)',
        font=dict(color='white'),
        xaxis=dict(title="Seconds into match", color='white'),
        yaxis=dict(color='white'),
        margin=dict(l=10, r=10, t=10, b=40)
    )

    st.plotly_chart(fig3, use_container_width=True)
