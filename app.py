import base64
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots


# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(
    page_title="Gas Network Explorer – Wales & West Utilities",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ------------------------------------------------------
# BRAND COLOURS (HYDROSTAR + DARK THEME)
# ------------------------------------------------------
PRIMARY_COLOUR = "#a7d730"
SECONDARY_COLOUR = "#499823"
DARK_GREY = "#30343c"
LIGHT_GREY = "#8c919a"
BACKGROUND = "#0e1117"
PANEL_BG = "#1b222b"
TEXT_COL = "#f2f4f7"
SUBTEXT_COL = LIGHT_GREY
ACCENT_COLOUR = "#86d5f8"

LOCATION_COLOURS = {
    "Great Hele": "#a7d730",
    "High Bickington": "#499823",
    "Whitminster": "#86d5f8",
    "Malmesbury": "#f59e0b",
}

# Per-location series colour maps (used in individual mode)
SERIES_COLOUR_MAPS = {
    "Great Hele": {
        "Flow (Scmh)": PRIMARY_COLOUR,
        "Pressure (Bar)": ACCENT_COLOUR,
    },
    "High Bickington": {
        "Flow (Kscmh) F1": PRIMARY_COLOUR,
        "Flow (Kscmh) F2": SECONDARY_COLOUR,
        "Flow (Kscmh) F3": ACCENT_COLOUR,
    },
    "Whitminster": {
        "Flow (Kscmh)": PRIMARY_COLOUR,
    },
    "Malmesbury": {
        "Flow (Kscmh)": PRIMARY_COLOUR,
    },
}


# ======================================================
# LOCATION METADATA
# ======================================================
LOCATIONS = {
    "Great Hele": {
        "file": "great_hele_combined.parquet",
        "lat": 50.98,
        "lon": -3.60,
        "compare_col": "Flow (Scmh)",
        "compare_scale": 1 / 1000,  # Scmh → Kscmh
        "flow_unit": "Scmh",
        "has_pressure": True,
        "description": "Flow & Pressure · Devon",
    },
    "High Bickington": {
        "file": "High_Bickington_cleaned.parquet",
        "lat": 50.94,
        "lon": -3.93,
        "compare_col": "Flow (Kscmh) F1",
        "compare_scale": 1.0,
        "flow_unit": "Kscmh",
        "has_pressure": False,
        "description": "3 Flow sensors · Devon",
    },
    "Whitminster": {
        "file": "whitminster_cleaned.parquet",
        "lat": 51.74,
        "lon": -2.31,
        "compare_col": "Flow (Kscmh)",
        "compare_scale": 1.0,
        "flow_unit": "Kscmh",
        "has_pressure": False,
        "description": "Flow · Gloucestershire",
    },
    "Malmesbury": {
        "file": "malmesbury_cleaned.parquet",
        "lat": 51.58,
        "lon": -2.10,
        "compare_col": "Flow (Kscmh)",
        "compare_scale": 1.0,
        "flow_unit": "Kscmh",
        "has_pressure": False,
        "description": "Flow · Wiltshire (to 2023)",
    },
}


# ------------------------------------------------------
# GLOBAL CSS TO FORCE DARK UI
# ------------------------------------------------------
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Hind:wght@300;400;500;600;700&display=swap');

    :root {{
        --hs-primary: {PRIMARY_COLOUR};
        --hs-secondary: {SECONDARY_COLOUR};
        --hs-bg: {BACKGROUND};
        --hs-card: {PANEL_BG};
        --hs-text: {TEXT_COL};
        --hs-subtext: {SUBTEXT_COL};
        --hs-sidebar: {DARK_GREY};
    }}

    html, body, [class*="css"] {{
        font-family: 'Hind', sans-serif;
    }}

    .stApp {{
        background:
            radial-gradient(circle at top right, rgba(167, 215, 48, 0.11) 0%, rgba(14, 17, 23, 0) 35%),
            radial-gradient(circle at bottom left, rgba(134, 213, 248, 0.08) 0%, rgba(14, 17, 23, 0) 40%),
            var(--hs-bg);
        color: var(--hs-text);
    }}
    .block-container {{
        padding-top: 1.8rem;
        padding-bottom: 2rem;
        color: var(--hs-text);
    }}
    h1, h2, h3, h4, h5, h6 {{
        color: var(--hs-text) !important;
        font-weight: 700;
        letter-spacing: 0.1px;
    }}
    p, span, label {{
        color: var(--hs-text) !important;
    }}
    .stCaption, .stMarkdown small {{
        color: var(--hs-subtext) !important;
    }}
    section[data-testid="stSidebar"] > div {{
        background-color: var(--hs-sidebar);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }}
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown span,
    section[data-testid="stSidebar"] label {{
        color: #ffffff !important;
    }}
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    div[data-baseweb="textarea"] > div {{
        background-color: rgba(255, 255, 255, 0.06);
        border-color: rgba(255, 255, 255, 0.16);
    }}
    .stDateInput > div > div,
    .stMultiSelect > div > div,
    .stSelectbox > div > div {{
        background-color: rgba(255, 255, 255, 0.06);
    }}
    .stSlider > div > div > div {{
        background-color: rgba(167, 215, 48, 0.18);
    }}
    .stSlider [data-testid="stTickBar"] > div {{
        background-color: rgba(167, 215, 48, 0.40);
    }}
    .st-bx, .stTextInput, .stNumberInput, .stDateInput, .stSelectbox, .stMultiSelect {{
        color: var(--hs-text) !important;
    }}
    .stButton > button {{
        background-color: var(--hs-primary);
        color: #1d2430;
        font-weight: 700;
        border: none;
        border-radius: 8px;
    }}
    .stButton > button:hover {{
        background-color: var(--hs-secondary);
        color: #ffffff;
    }}
    div[data-testid="metric-container"] {{
        background: linear-gradient(180deg, rgba(27, 34, 43, 0.96) 0%, rgba(22, 29, 37, 0.96) 100%);
        border: 1px solid rgba(255, 255, 255, 0.10);
        border-left: 5px solid var(--hs-primary);
        border-radius: 12px;
        padding: 0.85rem 1rem;
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.24);
    }}
    div[data-testid="metric-container"] label {{
        color: var(--hs-subtext) !important;
        font-size: 0.86rem !important;
        letter-spacing: 0.35px;
        text-transform: uppercase;
    }}
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {{
        color: var(--hs-text) !important;
        font-weight: 700;
        line-height: 1.1;
    }}
    div[data-testid="stDataFrame"] {{
        background-color: rgba(27, 34, 43, 0.96);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 0.2rem;
    }}
    .stPlotlyChart {{
        background-color: rgba(27, 34, 43, 0.45);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        padding: 0.55rem 1.45rem 0.25rem 0.55rem;
        margin-bottom: 1.1rem;
        box-sizing: border-box;
    }}
    .hero-banner {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 1.2rem;
        padding: 1.1rem 1.25rem;
        border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        background: linear-gradient(
            90deg,
            rgba(12, 16, 24, 0.90) 0%,
            rgba(18, 30, 22, 0.88) 72%,
            rgba(29, 52, 33, 0.78) 100%
        );
        margin-bottom: 1.4rem;
    }}
    .hero-copy {{
        max-width: 68%;
    }}
    .hero-title {{
        margin: 0;
        color: var(--hs-text);
        font-size: clamp(2.0rem, 2.8vw, 2.8rem);
        line-height: 1.1;
        font-weight: 700;
    }}
    .hero-subtitle {{
        margin: 0.45rem 0 0 0;
        color: var(--hs-subtext);
        font-size: 1rem;
    }}
    .hero-logos {{
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 1rem;
        flex-wrap: nowrap;
    }}
    .hero-logos img {{
        height: 112px;
        width: auto;
        object-fit: contain;
        filter: drop-shadow(0 6px 14px rgba(0, 0, 0, 0.35));
    }}
    @media (max-width: 1080px) {{
        .hero-banner {{
            flex-direction: column;
            align-items: flex-start;
        }}
        .hero-copy {{
            max-width: 100%;
        }}
        .hero-logos {{
            justify-content: flex-start;
        }}
        .hero-logos img {{
            height: 88px;
        }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# ======================================================
# DATA LOADING
# ======================================================
@st.cache_data
def load_location(name):
    meta = LOCATIONS[name]
    df_local = pd.read_parquet(meta["file"])
    if not isinstance(df_local.index, pd.DatetimeIndex):
        for col in ["Time", "Datetime", "timestamp"]:
            if col in df_local.columns:
                df_local[col] = pd.to_datetime(df_local[col], utc=True)
                df_local = df_local.set_index(col)
                break
        else:
            df_local.index = pd.to_datetime(df_local.index, utc=True)
    df_local = df_local.sort_index()
    return df_local


@st.cache_data
def build_comparison_df():
    """Build a single DataFrame with one flow column per location, all in Kscmh."""
    frames = {}
    for name, meta in LOCATIONS.items():
        raw = load_location(name)
        series = raw[meta["compare_col"]] * meta["compare_scale"]
        frames[name] = series
    return pd.DataFrame(frames)


all_data = {name: load_location(name) for name in LOCATIONS}
compare_df_full = build_comparison_df()


def encode_logo_to_base64(path: Path):
    if not path.exists():
        return ""
    return base64.b64encode(path.read_bytes()).decode("utf-8")


# ======================================================
# SIDEBAR – VIEW MODE
# ======================================================
view_options = ["All Locations"] + list(LOCATIONS.keys())
view_mode = st.sidebar.radio(
    "View",
    options=view_options,
    index=0,
    help="Compare all locations or dive into one",
)
is_compare = view_mode == "All Locations"

st.sidebar.markdown("---")

# ======================================================
# SIDEBAR – DATE RANGE (context-dependent)
# ======================================================
if is_compare:
    global_min = min(d.index.min().date() for d in all_data.values())
    global_max = max(d.index.max().date() for d in all_data.values())
else:
    loc_df_raw = all_data[view_mode]
    global_min = loc_df_raw.index.min().date()
    global_max = loc_df_raw.index.max().date()

st.sidebar.caption("Drag both handles to set the date window")
start_date, end_date = st.sidebar.slider(
    "Date range",
    min_value=global_min,
    max_value=global_max,
    value=(global_min, global_max),
    format="YYYY-MM-DD",
)


# ======================================================
# FILTER DATA
# ======================================================
def filter_by_date(dataframe, start, end):
    mask = (dataframe.index.date >= start) & (dataframe.index.date <= end)
    return dataframe.loc[mask]


if is_compare:
    compare_df = filter_by_date(compare_df_full, start_date, end_date).dropna(how="all")
    # Also filter individual data for stats
    filtered_data = {n: filter_by_date(d, start_date, end_date) for n, d in all_data.items()}
else:
    loc_df = filter_by_date(all_data[view_mode], start_date, end_date)
    # Series selector for individual mode
    all_cols = list(loc_df.columns)
    selected_cols = st.sidebar.multiselect(
        "Select series",
        options=all_cols,
        default=all_cols,
    )
    if not selected_cols:
        st.sidebar.error("Please select at least one series.")
        st.stop()
    loc_df = loc_df[selected_cols]


# Sidebar record count
if is_compare:
    total_recs = sum(len(d) for d in filtered_data.values())
    st.sidebar.markdown(
        f"<p style='color:{SUBTEXT_COL}; font-size:0.9rem;'>"
        f"Total records across all locations: "
        f"<span style='color:{TEXT_COL}; font-weight:600;'>{total_recs:,}</span></p>",
        unsafe_allow_html=True,
    )
else:
    st.sidebar.markdown(
        f"<p style='color:{SUBTEXT_COL}; font-size:0.9rem;'>Records (filtered): "
        f"<span style='color:{TEXT_COL}; font-weight:600;'>{len(loc_df):,}</span><br>"
        f"{loc_df.index.min().date()} → {loc_df.index.max().date()}</p>",
        unsafe_allow_html=True,
    )


# ======================================================
# HEADER
# ======================================================
hs_logo_b64 = encode_logo_to_base64(Path("logo.png"))
wwu_logo_b64 = encode_logo_to_base64(Path("wwu.png"))

logo_html_parts = []
if hs_logo_b64:
    logo_html_parts.append(
        f'<img src="data:image/png;base64,{hs_logo_b64}" alt="HydroStar logo">'
    )
if wwu_logo_b64:
    logo_html_parts.append(
        f'<img src="data:image/png;base64,{wwu_logo_b64}" alt="Wales and West Utilities logo">'
    )

if is_compare:
    hero_title = "Gas Network Flow Explorer"
    hero_subtitle = "HydroStar × Wales &amp; West Utilities · All Locations"
else:
    hero_title = f"{view_mode} Flow Explorer"
    hero_subtitle = f"HydroStar × Wales &amp; West Utilities · {LOCATIONS[view_mode]['description']}"

st.markdown(
    f"""
    <div class="hero-banner">
        <div class="hero-copy">
            <h1 class="hero-title">{hero_title}</h1>
            <p class="hero-subtitle">{hero_subtitle}</p>
        </div>
        <div class="hero-logos">
            {''.join(logo_html_parts)}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ======================================================
# HELPER: DARK PLOTLY LAYOUT
# ======================================================
def apply_dark_layout(fig, title):
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=20, color=TEXT_COL, family="Hind, sans-serif"),
        ),
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_COL, family="Hind, sans-serif"),
        colorway=[PRIMARY_COLOUR, SECONDARY_COLOUR, ACCENT_COLOUR, "#f59e0b", "#e11d48"],
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            x=0,
        ),
        margin=dict(l=66, r=72, t=78, b=62),
        hovermode="x unified",
    )
    fig.update_xaxes(
        gridcolor="rgba(255,255,255,0.08)",
        linecolor="rgba(255,255,255,0.18)",
        automargin=True,
    )
    fig.update_yaxes(
        gridcolor="rgba(255,255,255,0.08)",
        linecolor="rgba(255,255,255,0.18)",
        automargin=True,
    )
    return fig


# ======================================================
# HELPER: SPLIT FLOW / PRESSURE COLUMNS
# ======================================================
def split_series_columns(columns):
    flow_cols = [c for c in columns if "flow" in c.lower()]
    pressure_cols = [c for c in columns if "pressure" in c.lower()]
    other_cols = [c for c in columns if c not in flow_cols + pressure_cols]
    return flow_cols, pressure_cols, other_cols


# ======================================================
# HELPER: BUILD STACKED LINE CHART (individual mode)
# ======================================================
def build_stacked_line_chart(
    plot_df, title, xaxis_title, colour_map, flow_unit="Kscmh", mode="lines", marker_size=7
):
    flow_cols, pressure_cols, other_cols = split_series_columns(plot_df.columns)
    has_two_rows = bool(flow_cols and pressure_cols)
    nrows = 2 if has_two_rows else 1
    flow_scale = 1000.0 if flow_unit == "kScmh" else 1.0

    fig = make_subplots(rows=nrows, cols=1, shared_xaxes=True, vertical_spacing=0.08)

    for col in plot_df.columns:
        base_col = colour_map.get(col, "#6366f1")
        line_style = dict(color=base_col, width=2.4)
        if col in other_cols:
            line_style["dash"] = "dot"

        target_row = 1
        if has_two_rows and col in pressure_cols:
            target_row = 2

        y_vals = plot_df[col]
        trace_name = col
        if col in flow_cols and flow_unit == "kScmh":
            y_vals = y_vals / flow_scale
            trace_name = col.replace("(Scmh)", "(kScmh)")

        trace_kwargs = dict(
            x=plot_df.index,
            y=y_vals,
            mode=mode,
            name=trace_name,
            line=line_style,
        )
        if "markers" in mode:
            trace_kwargs["marker"] = dict(size=marker_size)

        fig.add_trace(go.Scatter(**trace_kwargs), row=target_row, col=1)

    fig.update_layout(xaxis_title=xaxis_title)
    if has_two_rows:
        flow_label = "Flow (kScmh)" if flow_unit == "kScmh" else f"Flow ({flow_unit})"
        fig.update_yaxes(title_text=flow_label, row=1, col=1)
        fig.update_yaxes(title_text="Pressure (Bar)", row=2, col=1)
    else:
        if flow_cols:
            label = "Flow (kScmh)" if flow_unit == "kScmh" else f"Flow ({flow_unit})"
        elif pressure_cols:
            label = "Pressure (Bar)"
        else:
            label = "Value"
        fig.update_yaxes(title_text=label, row=1, col=1)

    return apply_dark_layout(fig, title)


# ======================================================
# HELPER: BUILD COMPARISON LINE CHART
# ======================================================
def build_comparison_chart(plot_df, title, xaxis_title, mode="lines", marker_size=7):
    fig = go.Figure()
    for col in plot_df.columns:
        colour = LOCATION_COLOURS.get(col, "#6366f1")
        trace_kwargs = dict(
            x=plot_df.index,
            y=plot_df[col],
            mode=mode,
            name=col,
            line=dict(color=colour, width=2.4),
        )
        if "markers" in mode:
            trace_kwargs["marker"] = dict(size=marker_size)
        fig.add_trace(go.Scatter(**trace_kwargs))

    fig.update_layout(
        xaxis_title=xaxis_title,
        yaxis_title="Flow (Kscmh)",
    )
    return apply_dark_layout(fig, title)


# ======================================================
# MAP
# ======================================================
st.markdown("## Network locations")

map_lats = [m["lat"] for m in LOCATIONS.values()]
map_lons = [m["lon"] for m in LOCATIONS.values()]
map_names = list(LOCATIONS.keys())
map_descs = [m["description"] for m in LOCATIONS.values()]
map_colours = [LOCATION_COLOURS[n] for n in map_names]
map_active = [is_compare or n == view_mode for n in map_names]
map_sizes = [28 if active else 16 for active in map_active]
map_halo_sizes = [s + 14 for s in map_sizes]
map_ring_sizes = [s + 4 for s in map_sizes]
map_halo_opacity = [0.30 if active else 0.12 for active in map_active]
map_ring_opacity = [0.95 if active else 0.70 for active in map_active]
map_opacities = [0.98 if active else 0.55 for active in map_active]

fig_map = go.Figure()
fig_map.add_trace(
    go.Scattermapbox(
        lat=map_lats,
        lon=map_lons,
        mode="lines",
        line=dict(color="rgba(167, 215, 48, 0.42)", width=2.2),
        hoverinfo="skip",
        showlegend=False,
    )
)
fig_map.add_trace(
    go.Scattermapbox(
        lat=map_lats,
        lon=map_lons,
        mode="markers",
        marker=dict(size=map_halo_sizes, color=map_colours, opacity=map_halo_opacity),
        hoverinfo="skip",
        showlegend=False,
    )
)
fig_map.add_trace(
    go.Scattermapbox(
        lat=map_lats,
        lon=map_lons,
        mode="markers",
        marker=dict(
            size=map_ring_sizes,
            color="rgba(255,255,255,0.92)",
            opacity=map_ring_opacity,
        ),
        hoverinfo="skip",
        showlegend=False,
    )
)
fig_map.add_trace(
    go.Scattermapbox(
        lat=map_lats,
        lon=map_lons,
        mode="markers+text",
        marker=dict(
            size=map_sizes,
            color=map_colours,
            opacity=map_opacities,
        ),
        text=map_names,
        textposition="top center",
        textfont=dict(size=13, color=TEXT_COL, family="Hind, sans-serif"),
        customdata=map_descs,
        hovertemplate="<b>%{text}</b><br>%{customdata}<extra></extra>",
        showlegend=False,
    )
)
fig_map.update_layout(
    mapbox=dict(
        style="carto-positron",
        center=dict(lat=51.3, lon=-3.0),
        zoom=6.6,
        pitch=20,
        bearing=8,
    ),
    margin=dict(l=0, r=0, t=0, b=0),
    height=420,
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TEXT_COL),
)
st.plotly_chart(fig_map, use_container_width=True)

st.caption('Select a location from the sidebar to explore it individually, or stay on "All Locations" to compare.')


# ======================================================
# FREQUENCY / RESOLUTION HELPERS
# ======================================================
FREQ_MAP = {
    "30 minutes": "30min",
    "Hourly": "H",
    "Daily": "D",
    "Weekly": "W",
}
ROLLING_WINDOW_MAP = {
    "30 minutes": 48,
    "Hourly": 24,
    "Daily": 7,
    "Weekly": 4,
}


# ##########################################################################
#                        COMPARE ALL LOCATIONS
# ##########################################################################
if is_compare:

    # --------------------------------------------------
    # Summary statistics
    # --------------------------------------------------
    st.markdown("## Summary statistics")
    st.caption("One representative flow per location, all converted to Kscmh")

    mcols = st.columns(4)
    for i, name in enumerate(LOCATIONS):
        d = filtered_data[name]
        with mcols[i]:
            st.metric(name, f"{len(d):,} records")
            st.caption(f"{d.index.min().date()} → {d.index.max().date()}")

    st.markdown("#### Descriptive statistics (flow in Kscmh)")
    desc = compare_df.describe().T
    st.dataframe(
        desc.style.format(
            {
                "count": "{:,.0f}",
                "mean": "{:,.4f}",
                "std": "{:,.4f}",
                "min": "{:,.4f}",
                "25%": "{:,.4f}",
                "50%": "{:,.4f}",
                "75%": "{:,.4f}",
                "max": "{:,.4f}",
            }
        ),
        use_container_width=True,
        height=min(350, 80 + 28 * len(desc)),
    )

    # --------------------------------------------------
    # 1. Trend over time
    # --------------------------------------------------
    st.markdown("## Trend over time")

    ctrl1, ctrl2 = st.columns(2)
    with ctrl1:
        agg_choice = st.selectbox(
            "Time resolution",
            options=list(FREQ_MAP.keys()),
            index=2,
        )
    with ctrl2:
        smooth_trend = st.checkbox("Smooth trend", value=True)

    resampled = compare_df.resample(FREQ_MAP[agg_choice]).mean()
    if smooth_trend:
        resampled = resampled.rolling(
            window=ROLLING_WINDOW_MAP[agg_choice], min_periods=1
        ).median()

    fig_trend = build_comparison_chart(
        resampled,
        f"Flow Comparison – {agg_choice.lower()} averages",
        "Time",
    )
    if smooth_trend:
        st.caption(
            f"Smoothed with rolling median ({ROLLING_WINDOW_MAP[agg_choice]} points)."
        )
    st.plotly_chart(fig_trend, use_container_width=True)

    # --------------------------------------------------
    # 2. Daily averages
    # --------------------------------------------------
    st.markdown("## Daily averages")

    daily = compare_df.resample("D").mean()
    fig_daily = build_comparison_chart(daily, "Daily Average Flow", "Year")
    st.plotly_chart(fig_daily, use_container_width=True)

    # --------------------------------------------------
    # 3. Monthly seasonality
    # --------------------------------------------------
    st.markdown("## Monthly averages (multi-year seasonality)")

    monthly = compare_df.resample("M").mean()
    fig_monthly = build_comparison_chart(monthly, "Monthly Average Flow", "Year")
    st.plotly_chart(fig_monthly, use_container_width=True)

    # --------------------------------------------------
    # 4. Average by calendar month
    # --------------------------------------------------
    st.markdown("## Average by calendar month")

    month_labels = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    monthly_pat = compare_df.groupby(compare_df.index.month).mean()
    monthly_pat.index = month_labels[: len(monthly_pat)]

    fig_mpat = build_comparison_chart(
        monthly_pat,
        "Average Flow by Calendar Month",
        "Month",
        mode="lines+markers",
        marker_size=8,
    )
    st.plotly_chart(fig_mpat, use_container_width=True)

    # --------------------------------------------------
    # 5. Average by hour of day
    # --------------------------------------------------
    st.markdown("## Average by hour of day")

    hourly_pat = compare_df.groupby(compare_df.index.hour).mean()
    fig_hpat = build_comparison_chart(
        hourly_pat,
        "Average Flow by Hour of Day",
        "Hour",
        mode="lines+markers",
        marker_size=7,
    )
    st.plotly_chart(fig_hpat, use_container_width=True)

    # --------------------------------------------------
    # 6. Yearly distribution (boxplots)
    # --------------------------------------------------
    st.markdown("## Distribution of daily flow by year")

    daily_box = compare_df.resample("D").mean()
    daily_box["Year"] = daily_box.index.year

    fig_box = go.Figure()
    for name in LOCATIONS:
        if name not in daily_box.columns:
            continue
        fig_box.add_trace(
            go.Box(
                x=daily_box["Year"],
                y=daily_box[name],
                name=name,
                marker_color=LOCATION_COLOURS[name],
                boxmean=True,
                boxpoints=False,
            )
        )
    fig_box.update_layout(xaxis_title="Year", yaxis_title="Flow (Kscmh)")
    fig_box = apply_dark_layout(fig_box, "Daily Flow Distribution by Year")
    st.plotly_chart(fig_box, use_container_width=True)

    # --------------------------------------------------
    # 7. Correlation heatmap
    # --------------------------------------------------
    st.markdown("## Correlation between locations")

    corr = compare_df.corr()
    fig_corr = px.imshow(
        corr,
        text_auto=True,
        color_continuous_scale=[
            [0.0, ACCENT_COLOUR],
            [0.5, PANEL_BG],
            [1.0, PRIMARY_COLOUR],
        ],
        aspect="auto",
    )
    fig_corr.update_layout(xaxis_title="", yaxis_title="")
    fig_corr = apply_dark_layout(fig_corr, "Correlation Between Locations")
    st.plotly_chart(fig_corr, use_container_width=True)

    # --------------------------------------------------
    # Raw data
    # --------------------------------------------------
    with st.expander("Show comparison data (first 500 rows)"):
        st.dataframe(compare_df.head(500), use_container_width=True)


# ##########################################################################
#                     INDIVIDUAL LOCATION VIEW
# ##########################################################################
else:
    loc_meta = LOCATIONS[view_mode]
    colour_map = SERIES_COLOUR_MAPS.get(view_mode, {})

    # --------------------------------------------------
    # Summary statistics
    # --------------------------------------------------
    st.markdown("## Summary statistics")

    start_ts = loc_df.index.min().strftime("%Y-%m-%d %H:%M")
    end_ts = loc_df.index.max().strftime("%Y-%m-%d %H:%M")

    st.caption("Current filter KPIs")
    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        st.metric("Start date", start_ts)
    with mc2:
        st.metric("End date", end_ts)
    with mc3:
        st.metric("Total records (filtered)", f"{len(loc_df):,}")

    st.markdown("#### Descriptive statistics")
    desc = loc_df.describe().T
    st.dataframe(
        desc.style.format(
            {
                "count": "{:,.0f}",
                "mean": "{:,.4f}",
                "std": "{:,.4f}",
                "min": "{:,.4f}",
                "25%": "{:,.4f}",
                "50%": "{:,.4f}",
                "75%": "{:,.4f}",
                "max": "{:,.4f}",
            }
        ),
        use_container_width=True,
        height=min(350, 80 + 28 * len(desc)),
    )

    # --------------------------------------------------
    # 1. Trend over time
    # --------------------------------------------------
    st.markdown("## Trend over time")

    ctrl_a, ctrl_b, ctrl_c = st.columns(3)
    with ctrl_a:
        agg_choice = st.selectbox(
            "Time resolution",
            options=list(FREQ_MAP.keys()),
            index=2,
        )
    with ctrl_b:
        trend_view = st.selectbox(
            "Comparison view",
            options=["Separated (actual units)", "Normalized (0-1)"],
            index=0,
        )
    with ctrl_c:
        smooth_trend = st.checkbox("Smooth trend", value=True)

    # Flow unit toggle only for Great Hele (Scmh native)
    flow_unit = loc_meta["flow_unit"]
    if loc_meta["flow_unit"] == "Scmh":
        flow_unit = st.radio(
            "Flow display unit",
            options=["Scmh", "kScmh"],
            horizontal=True,
            index=1,
        )

    freq = FREQ_MAP[agg_choice]
    resampled = loc_df.resample(freq).mean()
    plot_data = resampled.copy()
    if smooth_trend:
        plot_data = plot_data.rolling(
            window=ROLLING_WINDOW_MAP[agg_choice], min_periods=1
        ).median()

    flow_cols, pressure_cols, other_cols = split_series_columns(plot_data.columns)

    if trend_view == "Separated (actual units)":
        flow_scale = 1000.0 if flow_unit == "kScmh" else 1.0
        has_two_rows = bool(flow_cols and pressure_cols)
        nrows = 2 if has_two_rows else 1
        fig_trend = make_subplots(
            rows=nrows, cols=1, shared_xaxes=True, vertical_spacing=0.06
        )

        for col in plot_data.columns:
            base_col = colour_map.get(col, "#6366f1")
            line_style = dict(color=base_col, width=2.2)
            if col in other_cols:
                line_style["dash"] = "dot"

            target_row = 1
            if has_two_rows and col in pressure_cols:
                target_row = 2

            y_vals = plot_data[col]
            trace_name = f"{col} ({agg_choice} avg)"
            if col in flow_cols and flow_unit == "kScmh":
                y_vals = y_vals / flow_scale
                trace_name = f"{col.replace('(Scmh)', '(kScmh)')} ({agg_choice} avg)"

            fig_trend.add_trace(
                go.Scatter(
                    x=plot_data.index,
                    y=y_vals,
                    mode="lines",
                    name=trace_name,
                    line=line_style,
                ),
                row=target_row,
                col=1,
            )

        fig_trend.update_layout(xaxis_title="Time")
        if has_two_rows:
            flabel = f"Flow ({flow_unit})" if flow_cols else "Value"
            fig_trend.update_yaxes(title_text=flabel, row=1, col=1)
            fig_trend.update_yaxes(title_text="Pressure (Bar)", row=2, col=1)
        else:
            if flow_cols:
                flabel = f"Flow ({flow_unit})"
            elif pressure_cols:
                flabel = "Pressure (Bar)"
            else:
                flabel = "Value"
            fig_trend.update_yaxes(title_text=flabel, row=1, col=1)

        fig_trend = apply_dark_layout(
            fig_trend, f"{view_mode} – {agg_choice.lower()} averages"
        )
    else:
        span = (plot_data.max() - plot_data.min()).replace(0, pd.NA)
        normalized = ((plot_data - plot_data.min()) / span).fillna(0.0)
        fig_trend = go.Figure()
        for col in normalized.columns:
            base_col = colour_map.get(col, "#6366f1")
            fig_trend.add_trace(
                go.Scatter(
                    x=normalized.index,
                    y=normalized[col],
                    mode="lines",
                    name=f"{col} ({agg_choice} avg)",
                    line=dict(color=base_col, width=2.2),
                )
            )
        fig_trend.update_layout(
            xaxis_title="Time", yaxis_title="Normalized value (0-1)"
        )
        fig_trend = apply_dark_layout(
            fig_trend, f"{view_mode} – {agg_choice.lower()} averages (normalized)"
        )
        st.caption("Each series is scaled independently to 0-1 for shape comparison.")

    if smooth_trend:
        st.caption(
            f"Smoothed with rolling median ({ROLLING_WINDOW_MAP[agg_choice]} points)."
        )
    st.plotly_chart(fig_trend, use_container_width=True)

    # --------------------------------------------------
    # 2. Daily averages
    # --------------------------------------------------
    st.markdown("## Daily averages")

    daily = loc_df.resample("D").mean()
    fig_daily = build_stacked_line_chart(
        daily,
        f"{view_mode} – Daily Averages",
        "Year",
        colour_map,
        flow_unit=flow_unit,
    )
    st.plotly_chart(fig_daily, use_container_width=True)

    # --------------------------------------------------
    # 3. Monthly seasonality
    # --------------------------------------------------
    st.markdown("## Monthly averages (multi-year seasonality)")

    monthly = loc_df.resample("M").mean()
    fig_monthly = build_stacked_line_chart(
        monthly,
        f"{view_mode} – Monthly Averages",
        "Year",
        colour_map,
        flow_unit=flow_unit,
    )
    st.plotly_chart(fig_monthly, use_container_width=True)

    # --------------------------------------------------
    # 4. Average by calendar month
    # --------------------------------------------------
    st.markdown("## Average by calendar month")

    month_labels = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    monthly_pat = loc_df.groupby(loc_df.index.month).mean()
    monthly_pat.index = month_labels[: len(monthly_pat)]

    fig_mpat = build_stacked_line_chart(
        monthly_pat,
        f"{view_mode} – Average by Month",
        "Month",
        colour_map,
        flow_unit=flow_unit,
        mode="lines+markers",
        marker_size=8,
    )
    st.plotly_chart(fig_mpat, use_container_width=True)

    # --------------------------------------------------
    # 5. Average by hour of day
    # --------------------------------------------------
    st.markdown("## Average by hour of day")

    hourly_pat = loc_df.groupby(loc_df.index.hour).mean()
    fig_hpat = build_stacked_line_chart(
        hourly_pat,
        f"{view_mode} – Average by Hour of Day",
        "Hour",
        colour_map,
        flow_unit=flow_unit,
        mode="lines+markers",
        marker_size=7,
    )
    st.plotly_chart(fig_hpat, use_container_width=True)

    # --------------------------------------------------
    # 6. Yearly distribution (boxplots)
    # --------------------------------------------------
    st.markdown("## Distribution of daily values by year")

    df_year = loc_df.resample("D").mean()
    df_year["Year"] = df_year.index.year
    value_cols = [c for c in df_year.columns if c != "Year"]
    flow_yr, pressure_yr, other_yr = split_series_columns(value_cols)

    flow_scale = 1000.0 if flow_unit == "kScmh" else 1.0
    first_group = flow_yr + other_yr
    if first_group:
        fig_box_f = go.Figure()
        for col in first_group:
            y_vals = df_year[col] / flow_scale if col in flow_yr else df_year[col]
            plot_name = col.replace("(Scmh)", f"({flow_unit})") if col in flow_yr else col
            fig_box_f.add_trace(
                go.Box(
                    x=df_year["Year"],
                    y=y_vals,
                    name=plot_name,
                    marker_color=colour_map.get(col, "#6366f1"),
                    boxmean=True,
                    boxpoints=False,
                )
            )
        ylab = f"Flow ({flow_unit})" if flow_yr else "Value"
        fig_box_f.update_layout(xaxis_title="Year", yaxis_title=ylab)
        fig_box_f = apply_dark_layout(
            fig_box_f, "Flow Distribution by Year" if flow_yr else "Distribution by Year"
        )
        st.plotly_chart(fig_box_f, use_container_width=True)

    if pressure_yr:
        fig_box_p = go.Figure()
        for col in pressure_yr:
            fig_box_p.add_trace(
                go.Box(
                    x=df_year["Year"],
                    y=df_year[col],
                    name=col,
                    marker_color=colour_map.get(col, "#6366f1"),
                    boxmean=True,
                    boxpoints=False,
                )
            )
        fig_box_p.update_layout(xaxis_title="Year", yaxis_title="Pressure (Bar)")
        fig_box_p = apply_dark_layout(fig_box_p, "Pressure Distribution by Year")
        st.plotly_chart(fig_box_p, use_container_width=True)

    # --------------------------------------------------
    # 7. Correlation heatmap
    # --------------------------------------------------
    if len(loc_df.columns) > 1:
        st.markdown("## Correlation between series")

        corr = loc_df.corr()
        fig_corr = px.imshow(
            corr,
            text_auto=True,
            color_continuous_scale=[
                [0.0, ACCENT_COLOUR],
                [0.5, PANEL_BG],
                [1.0, PRIMARY_COLOUR],
            ],
            aspect="auto",
        )
        fig_corr.update_layout(xaxis_title="", yaxis_title="")
        fig_corr = apply_dark_layout(fig_corr, "Correlation Between Series")
        st.plotly_chart(fig_corr, use_container_width=True)

    # --------------------------------------------------
    # Raw data
    # --------------------------------------------------
    with st.expander("Show raw data (first 500 rows)"):
        st.dataframe(loc_df.head(500), use_container_width=True)
