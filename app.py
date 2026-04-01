import base64
import math
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
st.set_option("client.toolbarMode", "viewer")


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
    "Great Hele": "#9bc53d",
    "High Bickington": "#e91e8c",
    "Whitminster": "#4ea8de",
    "Malmesbury": "#f77f00",
    "Aylesbeare": "#d7263d",
    "Enfield": "#7c3aed",
    "Charlton": "#0d9488",
}

# Per-location series colour maps (used in individual mode)
SERIES_COLOUR_MAPS = {
    "Great Hele": {
        "Flow (Scmh)": "#9bc53d",
        "Pressure (Bar)": "#c5e67a",
    },
    "High Bickington": {
        "Flow (Kscmh) F1": "#a3105e",
        "Flow (Kscmh) F2": "#e91e8c",
        "Flow (Kscmh) F3": "#f48dbf",
    },
    "Whitminster": {
        "Flow (Kscmh)": "#4ea8de",
    },
    "Malmesbury": {
        "Flow (Kscmh)": "#f77f00",
    },
    "Aylesbeare": {
        "Aylesbeare F1 mcm/d": "#8f1d2c",
        "Aylesbeare IP Inferred mcm/d": "#d7263d",
        "Aylesbeare IP Inferred Kscmh": "#f26a7c",
    },
    "Enfield": {
        "Enfield flow (F1)": "#5b21b6",
        "Enfield outlet (IP1)": "#a78bfa",
    },
    "Charlton": {
        "Charlton flow (F1)": "#0a7c72",
        "Charlton outlet (MP1)": "#2dd4bf",
    },
}

SERIES_DISPLAY_NAMES = {
    "Enfield outlet (IP1)": "Enfield outlet pressure (IP1)",
    "Charlton outlet (MP1)": "Charlton outlet pressure (MP1)",
    "Enfield flow (F1)": "Enfield flow (F1)",
    "Charlton flow (F1)": "Charlton flow (F1)",
}

SEASON_ORDER = ["Spring", "Summer", "Autumn", "Winter"]
SEASON_BY_MONTH = {
    12: "Winter",
    1: "Winter",
    2: "Winter",
    3: "Spring",
    4: "Spring",
    5: "Spring",
    6: "Summer",
    7: "Summer",
    8: "Summer",
    9: "Autumn",
    10: "Autumn",
    11: "Autumn",
}
SEASON_ANCHOR_COLOURS = {
    "Spring": "#74c476",
    "Summer": "#f6c453",
    "Autumn": "#d97706",
    "Winter": "#60a5fa",
}
SEASON_LINE_DASHES = {
    "Spring": "solid",
    "Summer": "dash",
    "Autumn": "dot",
    "Winter": "dashdot",
}
SEASON_MARKER_SYMBOLS = {
    "Spring": "circle",
    "Summer": "diamond",
    "Autumn": "square",
    "Winter": "x",
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
    "Aylesbeare": {
        "file": "Aylesbeare_cleaned.parquet",
        "lat": 50.72,
        "lon": -3.29,
        "compare_col": "Aylesbeare IP Inferred Kscmh",
        "compare_scale": 1.0,
        "flow_unit": "Kscmh",
        "has_pressure": False,
        "description": "Flow · Devon (inferred + F1)",
    },
    "Enfield": {
        "file": "enfield_charlton_cleaned.parquet",
        "lat": 51.62,
        "lon": -2.20,
        "compare_col": "Enfield flow (F1)",
        "compare_scale": 1 / 1000,  # Scmh → Kscmh
        "flow_unit": "Scmh",
        "has_pressure": True,
        "description": "Flow & outlet pressure · Gloucestershire",
        "columns": ["Enfield outlet (IP1)", "Enfield flow (F1)"],
    },
    "Charlton": {
        "file": "enfield_charlton_cleaned.parquet",
        "lat": 51.58,
        "lon": -2.12,
        "compare_col": "Charlton flow (F1)",
        "compare_scale": 1 / 1000,  # Scmh → Kscmh
        "flow_unit": "Scmh",
        "has_pressure": True,
        "description": "Flow & outlet pressure · Gloucestershire",
        "columns": ["Charlton outlet (MP1)", "Charlton flow (F1)"],
    },
}


COMPARE_SERIES = {
    "Great Hele": {
        "file": LOCATIONS["Great Hele"]["file"],
        "col": "Flow (Scmh)",
        "scale": 1 / 1000,
    },
    "High Bickington": {
        "file": LOCATIONS["High Bickington"]["file"],
        "col": "Flow (Kscmh) F1",
        "scale": 1.0,
    },
    "Whitminster": {
        "file": LOCATIONS["Whitminster"]["file"],
        "col": "Flow (Kscmh)",
        "scale": 1.0,
    },
    "Malmesbury": {
        "file": LOCATIONS["Malmesbury"]["file"],
        "col": "Flow (Kscmh)",
        "scale": 1.0,
    },
    "Aylesbeare": {
        "file": LOCATIONS["Aylesbeare"]["file"],
        "col": "Aylesbeare IP Inferred Kscmh",
        "scale": 1.0,
    },
    "Enfield flow (F1)": {
        "file": LOCATIONS["Enfield"]["file"],
        "col": "Enfield flow (F1)",
        "scale": 1 / 1000,
    },
    "Charlton flow (F1)": {
        "file": LOCATIONS["Charlton"]["file"],
        "col": "Charlton flow (F1)",
        "scale": 1 / 1000,
    },
}

COMPARE_SERIES_COLOURS = {
    "Great Hele": LOCATION_COLOURS["Great Hele"],
    "High Bickington": LOCATION_COLOURS["High Bickington"],
    "Whitminster": LOCATION_COLOURS["Whitminster"],
    "Malmesbury": LOCATION_COLOURS["Malmesbury"],
    "Aylesbeare": LOCATION_COLOURS["Aylesbeare"],
    "Enfield flow (F1)": "#5b21b6",
    "Charlton flow (F1)": "#0d9488",
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
    .stPlotlyChart .js-plotly-plot .plotly .modebar {{
        right: 2.8rem !important;
    }}
    div[data-testid="stElementContainer"] > div[data-testid="stElementToolbar"] {{
        top: 0.35rem !important;
        right: 0.45rem !important;
        z-index: 30 !important;
        opacity: 1 !important;
        visibility: visible !important;
        pointer-events: auto !important;
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
@st.cache_data(max_entries=8)
def load_location(name):
    meta = LOCATIONS[name]
    read_cols = meta.get("columns", None)
    df_local = pd.read_parquet(meta["file"], columns=read_cols)
    if not isinstance(df_local.index, pd.DatetimeIndex):
        for col in ["Time", "Datetime", "timestamp"]:
            if col in df_local.columns:
                df_local[col] = pd.to_datetime(df_local[col], utc=True)
                df_local = df_local.set_index(col)
                break
        else:
            df_local.index = pd.to_datetime(df_local.index, utc=True)
    df_local = df_local.sort_index()
    float_cols = df_local.select_dtypes(include=["float64"]).columns
    if len(float_cols) > 0:
        df_local[float_cols] = df_local[float_cols].astype("float32")
    return df_local


@st.cache_data
def load_compare_series(name):
    """Load one compare-mode flow series in Kscmh."""
    meta = COMPARE_SERIES[name]
    df_small = pd.read_parquet(meta["file"], columns=[meta["col"]])
    if not isinstance(df_small.index, pd.DatetimeIndex):
        for col in ["Time", "Datetime", "timestamp"]:
            if col in df_small.columns:
                df_small[col] = pd.to_datetime(df_small[col], utc=True)
                df_small = df_small.set_index(col)
                break
        else:
            df_small.index = pd.to_datetime(df_small.index, utc=True)
    series = (df_small[meta["col"]] * meta["scale"]).astype("float32")
    return series.sort_index()


@st.cache_data
def build_comparison_df():
    """Build a single DataFrame with one compare series per column, all in Kscmh."""
    frames = {}
    for name in COMPARE_SERIES:
        frames[name] = load_compare_series(name)
    return pd.DataFrame(frames).astype("float32")


def get_location_cache_signature():
    """Track metadata changes so Streamlit caches refresh when sites are added or updated."""
    location_sig = tuple(
        (
            name,
            meta["file"],
            meta["compare_col"],
            meta["compare_scale"],
            meta["flow_unit"],
        )
        for name, meta in LOCATIONS.items()
    )
    compare_sig = tuple(
        (name, meta["file"], meta["col"], meta["scale"])
        for name, meta in COMPARE_SERIES.items()
    )
    return location_sig + compare_sig


def refresh_location_caches():
    current_signature = get_location_cache_signature()
    if st.session_state.get("_location_cache_signature") == current_signature:
        return

    load_location.clear()
    load_compare_series.clear()
    build_comparison_df.clear()
    st.session_state["_location_cache_signature"] = current_signature


refresh_location_caches()


def encode_logo_to_base64(path: Path):
    if not path.exists():
        return ""
    return base64.b64encode(path.read_bytes()).decode("utf-8")


@st.cache_data
def get_compare_date_bounds():
    mins = []
    maxs = []
    for name in COMPARE_SERIES:
        series = load_compare_series(name)
        mins.append(series.index.min())
        maxs.append(series.index.max())
    return min(mins).date(), max(maxs).date()


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
    global_min, global_max = get_compare_date_bounds()
else:
    loc_df_raw = load_location(view_mode)
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
    if dataframe.empty:
        return dataframe

    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)

    if dataframe.index.tz is not None:
        start_ts = start_ts.tz_localize(dataframe.index.tz)
        end_ts = end_ts.tz_localize(dataframe.index.tz)

    return dataframe.loc[start_ts:end_ts]


@st.cache_data(max_entries=8)
def build_compare_summary_data(start, end):
    rows = []
    total_recs = 0

    for name in COMPARE_SERIES:
        series = filter_by_date(load_compare_series(name), start, end).dropna()
        count = int(series.count())
        total_recs += count

        if count == 0:
            rows.append(
                {
                    "Series": name,
                    "count": 0,
                    "start": None,
                    "end": None,
                    "mean": pd.NA,
                    "median": pd.NA,
                    "std": pd.NA,
                    "min": pd.NA,
                    "25%": pd.NA,
                    "75%": pd.NA,
                    "max": pd.NA,
                }
            )
            continue

        desc = series.describe()
        rows.append(
            {
                "Series": name,
                "count": count,
                "start": series.index.min().date(),
                "end": series.index.max().date(),
                "mean": desc["mean"],
                "median": desc["50%"],
                "std": desc["std"],
                "min": desc["min"],
                "25%": desc["25%"],
                "75%": desc["75%"],
                "max": desc["max"],
            }
        )

    summary_df = pd.DataFrame(rows).set_index("Series")
    return total_recs, summary_df


@st.cache_data(max_entries=16)
def build_compare_resampled_df(freq, start, end):
    frames = {}
    for name in COMPARE_SERIES:
        series = filter_by_date(load_compare_series(name), start, end)
        if freq != "1min":
            series = series.resample(freq).mean()
        frames[name] = series.astype("float32")
    return pd.DataFrame(frames).astype("float32").dropna(how="all")


@st.cache_data(max_entries=8)
def build_compare_pattern_df(pattern, start, end):
    frames = {}
    for name in COMPARE_SERIES:
        series = filter_by_date(load_compare_series(name), start, end).dropna()
        if pattern == "month":
            grouped = series.groupby(series.index.month).mean()
        else:
            grouped = series.groupby(series.index.hour).mean()
        frames[name] = grouped.astype("float32")
    return pd.DataFrame(frames).astype("float32")


def thin_time_series(dataframe, max_points=50000):
    """Downsample very dense trend charts to keep Plotly responsive."""
    if len(dataframe) <= max_points:
        return dataframe, 1
    step = (len(dataframe) + max_points - 1) // max_points
    return dataframe.iloc[::step], step


def select_time_focus(dataframe, key_prefix):
    """Simple period focus selector for trend charts."""
    focus_mode = st.selectbox(
        "Period to view",
        options=["All selected dates", "One year", "One month", "One day"],
        key=f"{key_prefix}_focus_mode",
    )
    if dataframe.empty or focus_mode == "All selected dates":
        return dataframe, "Showing all selected dates."

    years = sorted(dataframe.index.year.unique())
    year = st.selectbox("Year", options=years, index=len(years) - 1, key=f"{key_prefix}_year")
    year_df = dataframe[dataframe.index.year == year]
    if focus_mode == "One year":
        return year_df, f"Showing {year}."

    month_opts = sorted(year_df.index.month.unique())
    month = st.selectbox(
        "Month",
        options=month_opts,
        format_func=lambda m: pd.Timestamp(year=2000, month=int(m), day=1).strftime("%B"),
        key=f"{key_prefix}_month",
    )
    month_df = year_df[year_df.index.month == month]
    month_name = pd.Timestamp(year=2000, month=int(month), day=1).strftime("%B")
    if focus_mode == "One month":
        return month_df, f"Showing {month_name} {year}."

    day_opts = sorted(month_df.index.day.unique())
    day = st.selectbox("Day", options=day_opts, key=f"{key_prefix}_day")
    day_df = month_df[month_df.index.day == day]
    return day_df, f"Showing {year}-{int(month):02d}-{int(day):02d}."


if is_compare:
    compare_total_recs, compare_summary = build_compare_summary_data(start_date, end_date)
else:
    loc_df_full = filter_by_date(loc_df_raw, start_date, end_date)
    if loc_df_full.empty:
        st.warning("No data in the selected date range. Expand the date range to continue.")
        st.stop()
    # Series selector for individual mode
    all_cols = list(loc_df_full.columns)
    selected_cols = st.sidebar.multiselect(
        "Select series",
        options=all_cols,
        default=all_cols,
        format_func=lambda col: SERIES_DISPLAY_NAMES.get(col, col),
    )
    if not selected_cols:
        st.sidebar.error("Please select at least one series.")
        st.stop()
    loc_df = loc_df_full[selected_cols]


# Sidebar record count
if is_compare:
    st.sidebar.markdown(
        f"<p style='color:{SUBTEXT_COL}; font-size:0.9rem;'>"
        f"Total records across all locations: "
        f"<span style='color:{TEXT_COL}; font-weight:600;'>{compare_total_recs:,}</span></p>",
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
        colorway=list(LOCATION_COLOURS.values()),
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
    flow_cols = [
        c
        for c in columns
        if any(token in c.lower() for token in ("flow", "scmh", "kscmh", "mcm/d"))
    ]
    pressure_cols = [c for c in columns if "pressure" in c.lower() or "outlet" in c.lower()]
    other_cols = [c for c in columns if c not in flow_cols + pressure_cols]
    return flow_cols, pressure_cols, other_cols


def is_native_scmh_series(col):
    col_lower = col.lower()
    return "scmh" in col_lower and "kscmh" not in col_lower


def get_display_series_name(col, flow_unit):
    display_name = SERIES_DISPLAY_NAMES.get(col, col)
    if flow_unit == "kScmh" and is_native_scmh_series(col):
        display_name = display_name.replace("(Scmh)", "(kScmh)")
    return display_name


def get_display_series_values(series, col, flow_unit):
    if flow_unit == "kScmh" and is_native_scmh_series(col):
        return series / 1000.0
    return series


def get_flow_axis_label(flow_cols, flow_unit):
    if not flow_cols:
        return "Value"

    col_lower = [c.lower() for c in flow_cols]
    has_mcmd = any("mcm/d" in c for c in col_lower)
    has_kscmh = any("kscmh" in c for c in col_lower)
    has_scmh = any("scmh" in c and "kscmh" not in c for c in col_lower)

    if has_mcmd and (has_kscmh or has_scmh):
        return "Flow (mixed units)"
    if has_mcmd:
        return "Flow (mcm/d)"
    if flow_unit == "kScmh":
        return "Flow (kScmh)"
    return f"Flow ({flow_unit})"


def get_series_axis_label(col, flow_unit):
    col_lower = col.lower()
    if "pressure" in col_lower or "outlet" in col_lower:
        return "Pressure (Bar)"
    if "mcm/d" in col_lower:
        return "Flow (mcm/d)"
    if "kscmh" in col_lower:
        return "Flow (Kscmh)"
    if is_native_scmh_series(col):
        return "Flow (kScmh)" if flow_unit == "kScmh" else "Flow (Scmh)"
    if "flow" in col_lower:
        return f"Flow ({flow_unit})"
    return "Value"


def build_yearly_box_plot(df_year, selected_col, title, colour, flow_unit="Kscmh"):
    plot_name = get_display_series_name(selected_col, flow_unit)
    y_vals = get_display_series_values(df_year[selected_col], selected_col, flow_unit)

    fig = go.Figure()
    fig.add_trace(
        go.Box(
            x=df_year["Year"],
            y=y_vals,
            name=plot_name,
            marker_color=colour,
            boxmean=True,
            boxpoints=False,
        )
    )
    fig.update_layout(
        xaxis_title="Year",
        yaxis_title=get_series_axis_label(selected_col, flow_unit),
    )
    return apply_dark_layout(fig, title)


def build_descriptive_stats(df):
    desc = df.describe().T
    if "50%" in desc.columns:
        desc.insert(2, "median", desc.pop("50%"))
    return desc


def build_yearly_record_count_chart(series, title, colour):
    yearly_counts = series.groupby(series.index.year).count()
    yearly_counts.index = yearly_counts.index.astype(str)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=yearly_counts.index,
            y=yearly_counts.values,
            marker=dict(
                color=colour,
                line=dict(color=blend_hex(colour, BACKGROUND, 0.45), width=1.1),
            ),
            text=[f"{int(val):,}" for val in yearly_counts.values],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="Year %{x}<br>Records %{y:,}<extra></extra>",
            showlegend=False,
        )
    )
    fig.update_layout(xaxis_title="Year", yaxis_title="Records", showlegend=False)
    fig.update_yaxes(rangemode="tozero", tickformat=",d")
    return apply_dark_layout(fig, title)


def show_stretch_dataframe(data, **kwargs):
    try:
        st.dataframe(data, width="stretch", **kwargs)
    except TypeError:
        st.dataframe(data, use_container_width=True, **kwargs)


def show_head_tail_dataframe(df, head_rows=100, tail_rows=100):
    st.caption(f"First {head_rows} rows")
    show_stretch_dataframe(df.head(head_rows))
    st.caption(f"Last {tail_rows} rows")
    show_stretch_dataframe(df.tail(tail_rows))


def hex_to_rgb(colour):
    colour = colour.lstrip("#")
    return tuple(int(colour[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def blend_hex(colour_a, colour_b, amount):
    rgb_a = hex_to_rgb(colour_a)
    rgb_b = hex_to_rgb(colour_b)
    blended = tuple(
        round((1 - amount) * channel_a + amount * channel_b)
        for channel_a, channel_b in zip(rgb_a, rgb_b)
    )
    return rgb_to_hex(blended)


def get_location_season_colours(base_colour):
    return {
        season: blend_hex(base_colour, anchor, 0.58)
        for season, anchor in SEASON_ANCHOR_COLOURS.items()
    }


def build_seasonal_trend_chart(series, col, title, base_colour, flow_unit):
    display_series = get_display_series_values(series.dropna(), col, flow_unit)
    if display_series.empty:
        return None

    daily = display_series.resample("D").mean().dropna()
    if daily.empty:
        return None

    seasonal_df = daily.to_frame(name="value")
    seasonal_df["Season"] = [SEASON_BY_MONTH[m] for m in seasonal_df.index.month]
    seasonal_df["SeasonYear"] = (
        seasonal_df.index.year + (seasonal_df.index.month == 12).astype(int)
    )
    seasonal_avg = (
        seasonal_df.groupby(["SeasonYear", "Season"])["value"]
        .mean()
        .unstack("Season")
        .reindex(columns=SEASON_ORDER)
        .dropna(how="all")
    )

    if seasonal_avg.empty:
        return None

    season_colours = get_location_season_colours(base_colour)
    fig = go.Figure()
    for season in SEASON_ORDER:
        if season not in seasonal_avg.columns:
            continue
        season_vals = seasonal_avg[season].dropna()
        if season_vals.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=season_vals.index,
                y=season_vals.values,
                mode="lines+markers",
                name=season,
                line=dict(
                    color=season_colours[season],
                    width=2.6,
                    dash=SEASON_LINE_DASHES[season],
                ),
                marker=dict(size=8, symbol=SEASON_MARKER_SYMBOLS[season]),
                hovertemplate=(
                    f"{season}<br>Season year %{{x}}<br>"
                    f"{get_series_axis_label(col, flow_unit)} %{{y:,.4f}}<extra></extra>"
                ),
            )
        )

    if not fig.data:
        return None

    fig.update_layout(
        xaxis_title="Season year",
        yaxis_title=get_series_axis_label(col, flow_unit),
    )
    return apply_dark_layout(fig, title)


def get_location_correlation_scale(base_colour):
    negative_base = "#7cc7ff"
    zero_base = blend_hex(PANEL_BG, TEXT_COL, 0.06)
    positive_mid = blend_hex(base_colour, BACKGROUND, 0.34)
    positive_high = blend_hex(base_colour, TEXT_COL, 0.12)
    return [
        [0.0, blend_hex(negative_base, BACKGROUND, 0.24)],
        [0.5, zero_base],
        [0.75, positive_mid],
        [1.0, positive_high],
    ]


def build_correlation_heatmap(corr_df, title, base_colour=None):
    color_scale = (
        get_location_correlation_scale(base_colour)
        if base_colour
        else [
            [0.0, ACCENT_COLOUR],
            [0.5, PANEL_BG],
            [1.0, PRIMARY_COLOUR],
        ]
    )
    fig = px.imshow(
        corr_df,
        text_auto=True,
        color_continuous_scale=color_scale,
        zmin=-1,
        zmax=1,
        aspect="auto",
    )
    fig.update_layout(xaxis_title="", yaxis_title="")
    fig = apply_dark_layout(fig, title)
    fig.update_coloraxes(colorbar_title="Correlation")
    return fig


# ======================================================
# HELPER: BUILD STACKED LINE CHART (individual mode)
# ======================================================
def build_stacked_line_chart(
    plot_df, title, xaxis_title, colour_map, flow_unit="Kscmh", mode="lines", marker_size=7
):
    flow_cols, pressure_cols, other_cols = split_series_columns(plot_df.columns)
    has_two_rows = bool(flow_cols and pressure_cols)
    nrows = 2 if has_two_rows else 1
    flow_label = get_flow_axis_label(flow_cols, flow_unit)
    default_colour = get_colour_fallback(colour_map)

    fig = make_subplots(rows=nrows, cols=1, shared_xaxes=True, vertical_spacing=0.08)

    for col in plot_df.columns:
        base_col = colour_map.get(col, default_colour)
        line_style = dict(color=base_col, width=2.4)
        if col in other_cols:
            line_style["dash"] = "dot"

        target_row = 1
        if has_two_rows and col in pressure_cols:
            target_row = 2

        y_vals = plot_df[col]
        trace_name = get_display_series_name(col, flow_unit)
        if col in flow_cols:
            y_vals = get_display_series_values(y_vals, col, flow_unit)

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
        fig.update_yaxes(title_text=flow_label, row=1, col=1)
        fig.update_yaxes(title_text="Pressure (Bar)", row=2, col=1)
    else:
        if flow_cols:
            label = flow_label
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
        colour = COMPARE_SERIES_COLOURS.get(col, LOCATION_COLOURS.get(col, "#6366f1"))
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


def get_colour_fallback(colour_map, default="#6366f1"):
    return next(iter(colour_map.values()), default)


def chunk_list(items, size):
    return [items[i : i + size] for i in range(0, len(items), size)]


def get_map_distance_km(lat_a, lon_a, lat_b, lon_b):
    mean_lat = math.radians((lat_a + lat_b) / 2)
    dx = (lon_b - lon_a) * 111.32 * math.cos(mean_lat)
    dy = (lat_b - lat_a) * 110.57
    return math.hypot(dx, dy)


def get_text_anchor(lat_offset, lon_offset):
    if abs(lat_offset) < 1e-6:
        return "middle right" if lon_offset >= 0 else "middle left"
    if abs(lon_offset) < 1e-6:
        return "top center" if lat_offset >= 0 else "bottom center"
    if lat_offset >= 0 and lon_offset >= 0:
        return "top right"
    if lat_offset >= 0 and lon_offset < 0:
        return "top left"
    if lat_offset < 0 and lon_offset >= 0:
        return "bottom right"
    return "bottom left"


def get_map_display_points(locations, cluster_threshold_km=8.0, spread_radius_km=7.0):
    points = [
        {
            "name": name,
            "lat": meta["lat"],
            "lon": meta["lon"],
            "description": meta["description"],
        }
        for name, meta in locations.items()
    ]

    clusters = []
    visited = set()
    for idx in range(len(points)):
        if idx in visited:
            continue
        stack = [idx]
        cluster = []
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            cluster.append(current)
            for other in range(len(points)):
                if other in visited or other == current:
                    continue
                if get_map_distance_km(
                    points[current]["lat"],
                    points[current]["lon"],
                    points[other]["lat"],
                    points[other]["lon"],
                ) <= cluster_threshold_km:
                    stack.append(other)
        clusters.append(sorted(cluster, key=lambda i: points[i]["name"]))

    for cluster in clusters:
        if len(cluster) == 1:
            points[cluster[0]]["display_lat"] = points[cluster[0]]["lat"]
            points[cluster[0]]["display_lon"] = points[cluster[0]]["lon"]
            points[cluster[0]]["textposition"] = "top center"
            continue

        center_lat = sum(points[i]["lat"] for i in cluster) / len(cluster)
        center_lon = sum(points[i]["lon"] for i in cluster) / len(cluster)
        lon_scale = max(111.32 * math.cos(math.radians(center_lat)), 1e-6)
        radius_km = spread_radius_km + 1.2 * max(len(cluster) - 2, 0)
        start_angle = -math.pi / 4 if len(cluster) == 2 else -math.pi / 2

        for offset_idx, point_idx in enumerate(cluster):
            angle = start_angle + (2 * math.pi * offset_idx / len(cluster))
            lat_offset = (radius_km / 110.57) * math.sin(angle)
            lon_offset = (radius_km / lon_scale) * math.cos(angle)
            points[point_idx]["display_lat"] = center_lat + lat_offset
            points[point_idx]["display_lon"] = center_lon + lon_offset
            points[point_idx]["textposition"] = get_text_anchor(lat_offset, lon_offset)

    return points


# ======================================================
# MAP
# ======================================================
st.markdown("## Network locations")

map_points = get_map_display_points(LOCATIONS)
map_lats = [p["display_lat"] for p in map_points]
map_lons = [p["display_lon"] for p in map_points]
map_names = [p["name"] for p in map_points]
map_descs = [p["description"] for p in map_points]
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
        mode="markers",
        marker=dict(
            size=map_sizes,
            color=map_colours,
            opacity=map_opacities,
        ),
        customdata=map_descs,
        text=map_names,
        hovertemplate="<b>%{text}</b><br>%{customdata}<extra></extra>",
        showlegend=False,
    )
)
for point in map_points:
    fig_map.add_trace(
        go.Scattermapbox(
            lat=[point["display_lat"]],
            lon=[point["display_lon"]],
            mode="text",
            text=[point["name"]],
            textposition=point["textposition"],
            textfont=dict(size=13, color=TEXT_COL, family="Hind, sans-serif"),
            hoverinfo="skip",
            showlegend=False,
        )
    )
fig_map.update_layout(
    mapbox=dict(
        style="carto-positron",
        center=dict(lat=51.3, lon=-3.0),
        zoom=6.6,
        pitch=0,
        bearing=0,
    ),
    margin=dict(l=0, r=0, t=0, b=0),
    height=420,
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TEXT_COL),
)
st.plotly_chart(fig_map, width="stretch")

st.caption('Select a location from the sidebar to explore it individually, or stay on "All Locations" to compare.')


# ======================================================
# FREQUENCY / RESOLUTION HELPERS
# ======================================================
FREQ_MAP = {
    "1min": "1min",
    "15min": "15min",
    "30min": "30min",
    "Hourly": "h",
    "Daily": "D",
    "Weekly": "W",
    "Monthly": "ME",
}


# ##########################################################################
#                        COMPARE ALL LOCATIONS
# ##########################################################################
if is_compare:

    # --------------------------------------------------
    # Summary statistics
    # --------------------------------------------------
    st.markdown("## Summary statistics")
    st.caption("Comparable flow series across the network, all converted to Kscmh")

    compare_desc = compare_summary[
        ["count", "mean", "median", "std", "min", "25%", "75%", "max"]
    ]

    for row_names in chunk_list(list(COMPARE_SERIES.keys()), 3):
        mcols = st.columns(3)
        for col_idx, name in enumerate(row_names):
            site_summary = compare_summary.loc[name]
            count = int(site_summary["count"])
            with mcols[col_idx]:
                st.metric(name, f"{count:,} records")
                if count > 0:
                    st.caption(f"{site_summary['start']} → {site_summary['end']}")
                else:
                    st.caption("No data in selected range")

    st.markdown("#### Descriptive statistics (flow in Kscmh)")
    show_stretch_dataframe(
        compare_desc.style.format(
            {
                "count": "{:,.0f}",
                "mean": "{:,.4f}",
                "median": "{:,.4f}",
                "std": "{:,.4f}",
                "min": "{:,.4f}",
                "25%": "{:,.4f}",
                "75%": "{:,.4f}",
                "max": "{:,.4f}",
            }
        ),
        height=min(350, 80 + 28 * len(compare_desc)),
    )

    # --------------------------------------------------
    # Compare analysis
    # --------------------------------------------------
    st.markdown("## Compare analysis")
    compare_section = st.selectbox(
        "Section",
        options=[
            "Choose a section",
            "Trend over time",
            "Daily averages",
            "Monthly averages",
            "Average by calendar month",
            "Average by hour of day",
            "Distribution of daily flow by year",
            "Correlation between flow series",
            "Raw data",
        ],
        key="compare_section",
    )

    if compare_section == "Choose a section":
        st.info("Choose one analysis section to load. This keeps the Streamlit Cloud app responsive.")

    elif compare_section == "Trend over time":
        st.markdown("## Trend over time")

        ctrl1, ctrl2, ctrl3 = st.columns(3)
        with ctrl3:
            trend_location = st.selectbox(
                "Series to show",
                options=["All series"] + list(COMPARE_SERIES.keys()),
                index=0,
                key="compare_trend_location",
            )
        with ctrl2:
            agg_choice = st.selectbox(
                "Data granularity",
                options=list(FREQ_MAP.keys()),
                index=list(FREQ_MAP.keys()).index("Daily"),
            )

        compare_trend_df = build_compare_resampled_df(
            FREQ_MAP[agg_choice], start_date, end_date
        )
        trend_source = (
            compare_trend_df
            if trend_location == "All series"
            else compare_trend_df[[trend_location]]
        )

        with ctrl1:
            trend_base, focus_caption = select_time_focus(
                trend_source, key_prefix="cmp_trend"
            )
        if trend_base.empty:
            st.info("No data in this period. Pick a different year/month/day.")
            st.stop()

        raw_points = len(trend_base)
        plot_data, thin_step = thin_time_series(trend_base)

        trend_title = f"Flow Comparison – {agg_choice.lower()} averages"
        if trend_location != "All series":
            trend_title = f"{trend_location} – {agg_choice.lower()} averages"

        fig_trend = build_comparison_chart(
            plot_data,
            trend_title,
            "Time",
        )
        st.caption(focus_caption)
        if thin_step > 1:
            st.caption(
                f"To keep things fast, this chart shows {len(plot_data):,} of {raw_points:,} points."
            )
        st.plotly_chart(fig_trend, width="stretch")

    elif compare_section == "Daily averages":
        st.markdown("## Daily averages")
        compare_daily = build_compare_resampled_df("D", start_date, end_date)
        fig_daily = build_comparison_chart(compare_daily, "Daily Average Flow", "Year")
        st.plotly_chart(fig_daily, width="stretch")

    elif compare_section == "Monthly averages":
        st.markdown("## Monthly averages (multi-year seasonality)")
        compare_monthly = build_compare_resampled_df("ME", start_date, end_date)
        fig_monthly = build_comparison_chart(
            compare_monthly, "Monthly Average Flow", "Year"
        )
        st.plotly_chart(fig_monthly, width="stretch")

    elif compare_section == "Average by calendar month":
        st.markdown("## Average by calendar month")
        month_labels = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ]
        monthly_pat = build_compare_pattern_df("month", start_date, end_date)
        monthly_pat.index = month_labels[: len(monthly_pat)]
        fig_mpat = build_comparison_chart(
            monthly_pat,
            "Average Flow by Calendar Month",
            "Month",
            mode="lines+markers",
            marker_size=8,
        )
        st.plotly_chart(fig_mpat, width="stretch")

    elif compare_section == "Average by hour of day":
        st.markdown("## Average by hour of day")
        compare_hourly_pat = build_compare_pattern_df("hour", start_date, end_date)
        fig_hpat = build_comparison_chart(
            compare_hourly_pat,
            "Average Flow by Hour of Day",
            "Hour",
            mode="lines+markers",
            marker_size=7,
        )
        st.plotly_chart(fig_hpat, width="stretch")

    elif compare_section == "Distribution of daily flow by year":
        st.markdown("## Distribution of daily flow by year")
        compare_daily_box = build_compare_resampled_df("D", start_date, end_date)
        compare_daily_box["Year"] = compare_daily_box.index.year
        box_location = st.selectbox(
            "Series to show",
            options=list(COMPARE_SERIES.keys()),
            key="compare_box_location",
        )
        fig_box = build_yearly_box_plot(
            compare_daily_box,
            box_location,
            f"Daily Flow Distribution by Year – {box_location}",
            COMPARE_SERIES_COLOURS.get(
                box_location, LOCATION_COLOURS.get(box_location, "#6366f1")
            ),
            flow_unit="Kscmh",
        )
        st.plotly_chart(fig_box, width="stretch")

    elif compare_section == "Correlation between flow series":
        st.markdown("## Correlation between flow series")
        compare_corr = build_compare_resampled_df("D", start_date, end_date).corr()
        st.caption("Computed from daily mean flow series to keep compare mode responsive.")
        fig_corr = build_correlation_heatmap(compare_corr, "Correlation Between Flow Series")
        st.plotly_chart(fig_corr, width="stretch")

    else:
        st.markdown("## Raw data")
        compare_raw = build_compare_resampled_df("1min", start_date, end_date)
        with st.expander("Show comparison data (first and last 100 rows)", expanded=True):
            show_head_tail_dataframe(compare_raw)


# ##########################################################################
#                     INDIVIDUAL LOCATION VIEW
# ##########################################################################
else:
    loc_meta = LOCATIONS[view_mode]
    colour_map = SERIES_COLOUR_MAPS.get(view_mode, {})
    default_colour = get_colour_fallback(
        colour_map, LOCATION_COLOURS.get(view_mode, "#6366f1")
    )

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
    desc = build_descriptive_stats(loc_df)
    show_stretch_dataframe(
        desc.style.format(
            {
                "count": "{:,.0f}",
                "mean": "{:,.4f}",
                "median": "{:,.4f}",
                "std": "{:,.4f}",
                "min": "{:,.4f}",
                "25%": "{:,.4f}",
                "75%": "{:,.4f}",
                "max": "{:,.4f}",
            }
        ),
        height=min(350, 80 + 28 * len(desc)),
    )

    flow_unit = loc_meta["flow_unit"]
    if loc_meta["flow_unit"] == "Scmh":
        flow_unit = st.radio(
            "Flow display unit",
            options=["Scmh", "kScmh"],
            horizontal=True,
            index=1,
            key=f"{view_mode}_flow_unit",
        )

    # --------------------------------------------------
    # Records by year
    # --------------------------------------------------
    st.markdown("## Records by year")

    record_count_col = loc_meta["compare_col"]
    if record_count_col not in loc_df_full.columns:
        record_count_col = loc_df_full.columns[0]

    record_series = loc_df_full[record_count_col].dropna()
    record_colour = colour_map.get(record_count_col, default_colour)
    st.caption(
        f"Annual non-null record counts for {get_display_series_name(record_count_col, flow_unit=loc_meta['flow_unit'])} in the selected date range."
    )
    if record_series.empty:
        st.info("No records for that series in the selected date range.")
    else:
        fig_records = build_yearly_record_count_chart(
            record_series,
            f"{view_mode} – Records by Year",
            record_colour,
        )
        st.plotly_chart(fig_records, width="stretch")

    # --------------------------------------------------
    # Seasonal trend by year
    # --------------------------------------------------
    st.markdown("## Seasonal trend by year")

    seasonal_col = st.selectbox(
        "Column to compare across seasons",
        options=list(loc_df.columns),
        format_func=lambda col: get_display_series_name(col, flow_unit),
        key=f"{view_mode}_seasonal_col",
    )
    st.caption(
        "Each point shows the mean of daily averages within that season. Winter groups December with the following January and February."
    )
    fig_seasonal = build_seasonal_trend_chart(
        loc_df[seasonal_col],
        seasonal_col,
        f"{view_mode} – {get_display_series_name(seasonal_col, flow_unit)} Seasonal Trend",
        LOCATION_COLOURS.get(view_mode, default_colour),
        flow_unit,
    )
    if fig_seasonal is None:
        st.info("No seasonal data is available for that column in the selected date range.")
    else:
        st.plotly_chart(fig_seasonal, width="stretch")

    # --------------------------------------------------
    # 1. Trend over time
    # --------------------------------------------------
    st.markdown("## Trend over time")

    ctrl_a, ctrl_b, ctrl_c = st.columns(3)
    with ctrl_a:
        trend_base, focus_caption = select_time_focus(loc_df, key_prefix=f"{view_mode}_trend")
    with ctrl_b:
        agg_choice = st.selectbox(
            "Data granularity",
            options=list(FREQ_MAP.keys()),
            index=list(FREQ_MAP.keys()).index("Daily"),
        )
    with ctrl_c:
        trend_view = st.selectbox(
            "Comparison view",
            options=["Separated (actual units)", "Normalized (0-1)"],
            index=0,
        )
    if trend_base.empty:
        st.info("No data in this period. Pick a different year/month/day.")
        st.stop()

    freq = FREQ_MAP[agg_choice]
    resampled = trend_base.resample(freq).mean().dropna(how="all")
    plot_data = resampled.copy()
    raw_points = len(plot_data)
    plot_data, thin_step = thin_time_series(plot_data)

    flow_cols, pressure_cols, other_cols = split_series_columns(plot_data.columns)

    if trend_view == "Separated (actual units)":
        has_two_rows = bool(flow_cols and pressure_cols)
        nrows = 2 if has_two_rows else 1
        flow_label = get_flow_axis_label(flow_cols, flow_unit)
        fig_trend = make_subplots(
            rows=nrows, cols=1, shared_xaxes=True, vertical_spacing=0.06
        )

        for col in plot_data.columns:
            base_col = colour_map.get(col, default_colour)
            line_style = dict(color=base_col, width=2.2)
            if col in other_cols:
                line_style["dash"] = "dot"

            target_row = 1
            if has_two_rows and col in pressure_cols:
                target_row = 2

            y_vals = plot_data[col]
            trace_name = f"{get_display_series_name(col, flow_unit)} ({agg_choice} avg)"
            if col in flow_cols:
                y_vals = get_display_series_values(y_vals, col, flow_unit)

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
            fig_trend.update_yaxes(title_text=flow_label, row=1, col=1)
            fig_trend.update_yaxes(title_text="Pressure (Bar)", row=2, col=1)
        else:
            if flow_cols:
                flabel = flow_label
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
            base_col = colour_map.get(col, default_colour)
            fig_trend.add_trace(
                go.Scatter(
                    x=normalized.index,
                    y=normalized[col],
                    mode="lines",
                    name=f"{get_display_series_name(col, flow_unit)} ({agg_choice} avg)",
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

    st.caption(focus_caption)
    if thin_step > 1:
        st.caption(
            f"To keep things fast, this chart shows {len(plot_data):,} of {raw_points:,} points."
        )
    st.plotly_chart(fig_trend, width="stretch")

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
    st.plotly_chart(fig_daily, width="stretch")

    # --------------------------------------------------
    # 3. Monthly seasonality
    # --------------------------------------------------
    st.markdown("## Monthly averages (multi-year seasonality)")

    monthly = loc_df.resample("ME").mean()
    fig_monthly = build_stacked_line_chart(
        monthly,
        f"{view_mode} – Monthly Averages",
        "Year",
        colour_map,
        flow_unit=flow_unit,
    )
    st.plotly_chart(fig_monthly, width="stretch")

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
    st.plotly_chart(fig_mpat, width="stretch")

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
    st.plotly_chart(fig_hpat, width="stretch")

    # --------------------------------------------------
    # 6. Yearly distribution (boxplots)
    # --------------------------------------------------
    st.markdown("## Distribution of values by year")

    df_year = loc_df.copy()
    df_year["Year"] = df_year.index.year
    value_cols = [c for c in df_year.columns if c != "Year"]

    selected_box_col = st.selectbox(
        "Series to show",
        options=value_cols,
        format_func=lambda col: get_display_series_name(col, flow_unit),
        key=f"{view_mode}_box_series",
    )
    fig_box = build_yearly_box_plot(
        df_year,
        selected_box_col,
        f"{view_mode} – {get_display_series_name(selected_box_col, flow_unit)} Distribution by Year",
        colour_map.get(selected_box_col, default_colour),
        flow_unit=flow_unit,
    )
    st.plotly_chart(fig_box, width="stretch")

    # --------------------------------------------------
    # 7. Correlation heatmap
    # --------------------------------------------------
    if len(loc_df.columns) > 1:
        st.markdown("## Correlation between series")

        corr = loc_df.corr()
        fig_corr = build_correlation_heatmap(
            corr,
            "Correlation Between Series",
            base_colour=LOCATION_COLOURS.get(view_mode),
        )
        st.plotly_chart(fig_corr, width="stretch")

    # --------------------------------------------------
    # Raw data
    # --------------------------------------------------
    with st.expander("Show raw data (first and last 100 rows)"):
        show_head_tail_dataframe(loc_df)
