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
        # NOTE: Village centre is ~50.81, -3.43; gas infrastructure coords may differ.
        # Verify against WWU site records if map placement looks wrong.
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
        # Verified by WWU: EX5 1AF / OS grid 298460, 090745 → near Broadclyst, Devon.
        "lat": 50.759,
        "lon": -3.407,
        "compare_col": "Enfield flow (F1)",
        "compare_scale": 1 / 1000,  # Scmh → Kscmh
        "flow_unit": "Scmh",
        "has_pressure": True,
        "description": "Flow & outlet pressure · Devon",
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
    # Biomethane comparison display-name keys
    "Enfield \u2014 Flow (Kscmh)":    "#7c3aed",
    "Charlton \u2014 Flow (Kscmh)":   "#0d9488",
    "Great Hele \u2014 Flow (Kscmh)": "#9bc53d",
    "Enfield \u2014 Pressure (Bar)":    "#a78bfa",
    "Charlton \u2014 Pressure (Bar)":   "#2dd4bf",
    "Great Hele \u2014 Pressure (Bar)": "#c5e67a",
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


# ======================================================
# OUTLIER DETECTION – 3×IQR per column
# ======================================================
@st.cache_data(max_entries=8)
def compute_iqr_bounds(name: str) -> dict:
    """Return per-column (lower, upper) 3×IQR bounds computed on the full dataset.

    Bounds are fixed from the entire dataset so they don't shift as the user
    scrolls the date range slider — this keeps the definition of "outlier"
    stable and transparent.
    """
    df = load_location(name)
    bounds = {}
    for col in df.select_dtypes(include="number").columns:
        q1 = float(df[col].quantile(0.25))
        q3 = float(df[col].quantile(0.75))
        iqr = q3 - q1
        bounds[col] = (q1 - 3.0 * iqr, q3 + 3.0 * iqr)
    return bounds


def apply_outlier_filter(df: pd.DataFrame, bounds: dict) -> pd.DataFrame:
    """Mask outlier values to NaN per column (rows are kept, not dropped).

    Masking per-column rather than dropping rows ensures that a pressure
    outlier doesn't also erase a perfectly valid simultaneous flow reading.
    """
    df = df.copy()
    for col, (lo, hi) in bounds.items():
        if col in df.columns:
            df.loc[(df[col] < lo) | (df[col] > hi), col] = float("nan")
    return df


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
view_options = ["All Locations", "Biomethane Sites"] + list(LOCATIONS.keys())
view_mode = st.sidebar.radio(
    "View",
    options=view_options,
    index=0,
    help="Compare all locations, explore biomethane injection sites, or dive into one",
)
is_compare = view_mode == "All Locations"
is_biomethane = view_mode == "Biomethane Sites"

st.sidebar.markdown("---")

# ======================================================
# SIDEBAR – DATE RANGE (context-dependent)
# ======================================================
BIOMETHANE_SITES = ["Enfield", "Charlton", "Great Hele"]

if is_compare:
    global_min, global_max = get_compare_date_bounds()
elif is_biomethane:
    _bm_mins, _bm_maxs = [], []
    for _s in BIOMETHANE_SITES:
        _df_tmp = load_location(_s)
        _bm_mins.append(_df_tmp.index.min().date())
        _bm_maxs.append(_df_tmp.index.max().date())
    global_min, global_max = min(_bm_mins), max(_bm_maxs)
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

st.sidebar.markdown("---")
remove_outliers = st.sidebar.toggle(
    "Remove outliers (3×IQR)",
    value=True,
    help=(
        "For each series, the app finds the middle 50% of values "
        "(the IQR) and hides readings below Q1 - 3×IQR or above "
        "Q3 + 3×IQR."
    ),
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


def _get_compare_series_filtered(name: str, filter_outliers: bool) -> pd.Series:
    """Return the compare series for a location, optionally with outliers masked.

    Bounds are computed from the series itself (full dataset) so this works for
    all COMPARE_SERIES keys, including those like 'Enfield flow (F1)' that don't
    match a LOCATIONS key directly.
    """
    series = load_compare_series(name)
    if filter_outliers:
        q1 = float(series.quantile(0.25))
        q3 = float(series.quantile(0.75))
        iqr = q3 - q1
        lo, hi = q1 - 3.0 * iqr, q3 + 3.0 * iqr
        series = series.copy()
        series[(series < lo) | (series > hi)] = float("nan")
    return series


@st.cache_data(max_entries=8)
def build_compare_summary_data(start, end, filter_outliers: bool = True):
    rows = []
    total_recs = 0

    for name in COMPARE_SERIES:
        series = filter_by_date(
            _get_compare_series_filtered(name, filter_outliers), start, end
        ).dropna()
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
def build_compare_resampled_df(freq, start, end, filter_outliers: bool = True):
    frames = {}
    for name in COMPARE_SERIES:
        series = filter_by_date(
            _get_compare_series_filtered(name, filter_outliers), start, end
        )
        if freq != "1min":
            series = series.resample(freq).mean()
        frames[name] = series.astype("float32")
    return pd.DataFrame(frames).astype("float32").dropna(how="all")


@st.cache_data(max_entries=8)
def build_compare_pattern_df(pattern, start, end, filter_outliers: bool = True):
    frames = {}
    for name in COMPARE_SERIES:
        series = filter_by_date(
            _get_compare_series_filtered(name, filter_outliers), start, end
        ).dropna()
        if pattern == "month":
            grouped = series.groupby(series.index.month).mean()
        else:
            grouped = series.groupby(series.index.hour).mean()
        frames[name] = grouped.astype("float32")
    return pd.DataFrame(frames).astype("float32")


@st.cache_data(max_entries=16)
def build_bm_comparison_df(freq, start, end, filter_outliers: bool = True):
    """Six-column DataFrame for biomethane cross-site comparison.

    Columns (all display-name keyed so chart builders pick up colours automatically):
      Enfield — Flow (Kscmh), Charlton — Flow (Kscmh), Great Hele — Flow (Kscmh)
      Enfield — Pressure (Bar), Charlton — Pressure (Bar), Great Hele — Pressure (Bar)
    """
    ec_raw = pd.read_parquet(
        "enfield_charlton_cleaned.parquet",
        columns=["Enfield flow (F1)", "Enfield outlet (IP1)",
                 "Charlton flow (F1)", "Charlton outlet (MP1)"],
    )
    gh_raw = pd.read_parquet(
        "great_hele_combined.parquet",
        columns=["Flow (Scmh)", "Pressure (Bar)"],
    )
    # Ensure DatetimeIndex with timezone, mirroring load_location logic
    for _df in [ec_raw, gh_raw]:
        if not isinstance(_df.index, pd.DatetimeIndex):
            for _c in ["Time", "Datetime", "timestamp"]:
                if _c in _df.columns:
                    _df[_c] = pd.to_datetime(_df[_c], utc=True)
                    _df = _df.set_index(_c)
                    break
            else:
                _df.index = pd.to_datetime(_df.index, utc=True)
        elif _df.index.tz is None:
            _df.index = _df.index.tz_localize("UTC")
        _df.sort_index(inplace=True)

    ec_raw = filter_by_date(ec_raw, start, end)
    gh_raw = filter_by_date(gh_raw, start, end)

    if filter_outliers:
        for _df2 in [ec_raw, gh_raw]:
            for _col in _df2.select_dtypes("number").columns:
                _q1 = float(_df2[_col].quantile(0.25))
                _q3 = float(_df2[_col].quantile(0.75))
                _iqr = _q3 - _q1
                _df2.loc[(_df2[_col] < _q1 - 3 * _iqr) | (_df2[_col] > _q3 + 3 * _iqr), _col] = float("nan")

    frames = {}
    for raw_col, new_col, scale in [
        ("Enfield flow (F1)",     "Enfield \u2014 Flow (Kscmh)",    1 / 1000),
        ("Charlton flow (F1)",    "Charlton \u2014 Flow (Kscmh)",   1 / 1000),
        ("Enfield outlet (IP1)",  "Enfield \u2014 Pressure (Bar)",  1.0),
        ("Charlton outlet (MP1)", "Charlton \u2014 Pressure (Bar)", 1.0),
    ]:
        if raw_col in ec_raw.columns:
            s = ec_raw[raw_col] * scale
            frames[new_col] = (s.resample(freq).mean() if freq != "1min" else s).astype("float32")
    for raw_col, new_col, scale in [
        ("Flow (Scmh)",    "Great Hele \u2014 Flow (Kscmh)",    1 / 1000),
        ("Pressure (Bar)", "Great Hele \u2014 Pressure (Bar)", 1.0),
    ]:
        if raw_col in gh_raw.columns:
            s = gh_raw[raw_col] * scale
            frames[new_col] = (s.resample(freq).mean() if freq != "1min" else s).astype("float32")

    return pd.DataFrame(frames).dropna(how="all")


@st.cache_data(max_entries=8)
def build_bm_comparison_pattern_df(pattern, start, end, filter_outliers: bool = True):
    """Group the biomethane comparison DataFrame by month (1-12) or hour (0-23)."""
    full_df = build_bm_comparison_df("1min", start, end, filter_outliers)
    result = {}
    for col in full_df.columns:
        s = full_df[col].dropna()
        if pattern == "month":
            result[col] = s.groupby(s.index.month).mean().astype("float32")
        else:
            result[col] = s.groupby(s.index.hour).mean().astype("float32")
    return pd.DataFrame(result)


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
    compare_total_recs, compare_summary = build_compare_summary_data(start_date, end_date, remove_outliers)
elif is_biomethane:
    pass  # biomethane page loads its own data per site below
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

    # Apply outlier filter (masks values to NaN, keeps row timestamps intact)
    if remove_outliers:
        _null_before = int(loc_df.isnull().sum().sum())
        _iqr_bounds = compute_iqr_bounds(view_mode)
        loc_df = apply_outlier_filter(loc_df, _iqr_bounds)
        _null_after = int(loc_df.isnull().sum().sum())
        _n_masked = _null_after - _null_before
        if _n_masked > 0:
            st.sidebar.caption(f"↳ {_n_masked:,} outlier readings masked")


# Sidebar record count
if is_compare:
    st.sidebar.markdown(
        f"<p style='color:{SUBTEXT_COL}; font-size:0.9rem;'>"
        f"Total records across all locations: "
        f"<span style='color:{TEXT_COL}; font-weight:600;'>{compare_total_recs:,}</span></p>",
        unsafe_allow_html=True,
    )
elif is_biomethane:
    st.sidebar.markdown(
        f"<p style='color:{SUBTEXT_COL}; font-size:0.9rem;'>"
        f"Biomethane injection sites: "
        f"<span style='color:{TEXT_COL}; font-weight:600;'>Enfield · Charlton · Great Hele</span></p>",
        unsafe_allow_html=True,
    )
else:
    _sidebar_count_col = (
        LOCATIONS[view_mode]["compare_col"]
        if LOCATIONS[view_mode]["compare_col"] in loc_df.columns
        else loc_df.columns[0]
    )
    _sidebar_count = int(loc_df[_sidebar_count_col].count())
    _sidebar_min = loc_df[_sidebar_count_col].first_valid_index()
    _sidebar_max = loc_df[_sidebar_count_col].last_valid_index()
    st.sidebar.markdown(
        f"<p style='color:{SUBTEXT_COL}; font-size:0.9rem;'>Records (filtered): "
        f"<span style='color:{TEXT_COL}; font-weight:600;'>{_sidebar_count:,}</span><br>"
        f"{_sidebar_min.date() if _sidebar_min else '–'} → {_sidebar_max.date() if _sidebar_max else '–'}</p>",
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
elif is_biomethane:
    hero_title = "Biomethane Injection Sites"
    hero_subtitle = "HydroStar × Wales &amp; West Utilities · Enfield · Charlton · Great Hele"
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


def is_native_scmh_series(col, loc_flow_unit=None):
    """Return True if this column holds data in Scmh (not kScmh).

    Detects via column name when the unit is embedded (e.g. "Flow (Scmh)"),
    and falls back to the location-level flow_unit when the column name has
    no unit suffix (e.g. "Charlton flow (F1)" on a Scmh location).
    """
    col_lower = col.lower()
    # Column name explicitly says kscmh → definitely not native Scmh
    if "kscmh" in col_lower:
        return False
    # Column name explicitly says scmh → native Scmh
    if "scmh" in col_lower:
        return True
    # No unit in the name — fall back to location metadata
    if loc_flow_unit == "Scmh":
        # Only treat flow columns this way, not pressure/outlet columns
        if "flow" in col_lower and "pressure" not in col_lower and "outlet" not in col_lower:
            return True
    return False


def get_display_series_name(col, flow_unit, loc_flow_unit=None):
    display_name = SERIES_DISPLAY_NAMES.get(col, col)
    if flow_unit == "kScmh" and is_native_scmh_series(col, loc_flow_unit):
        display_name = display_name.replace("(Scmh)", "(kScmh)")
    return display_name


def get_display_series_values(series, col, flow_unit, loc_flow_unit=None):
    if flow_unit == "kScmh" and is_native_scmh_series(col, loc_flow_unit):
        return series / 1000.0
    return series


def get_display_value(value, col, flow_unit, loc_flow_unit=None):
    if pd.isna(value):
        return value
    if flow_unit == "kScmh" and is_native_scmh_series(col, loc_flow_unit):
        return value / 1000.0
    return value


def get_flow_axis_label(flow_cols, flow_unit, loc_flow_unit=None):
    if not flow_cols:
        return "Value"

    col_lower = [c.lower() for c in flow_cols]
    has_mcmd = any("mcm/d" in c for c in col_lower)
    has_kscmh = any("kscmh" in c for c in col_lower)
    # A column is Scmh if it says "scmh" OR if the location is a Scmh location
    has_scmh = any(
        ("scmh" in c and "kscmh" not in c)
        or (loc_flow_unit == "Scmh" and "flow" in c and "kscmh" not in c)
        for c in col_lower
    )

    if has_mcmd and (has_kscmh or has_scmh):
        return "Flow (mixed units)"
    if has_mcmd:
        return "Flow (mcm/d)"
    if flow_unit == "kScmh" and (has_scmh or loc_flow_unit == "Scmh"):
        return "Flow (kScmh)"
    if has_kscmh:
        return "Flow (Kscmh)"
    return f"Flow ({flow_unit})"


def get_series_axis_label(col, flow_unit, loc_flow_unit=None):
    col_lower = col.lower()
    if "pressure" in col_lower or "outlet" in col_lower:
        return "Pressure (Bar)"
    if "mcm/d" in col_lower:
        return "Flow (mcm/d)"
    if "kscmh" in col_lower:
        return "Flow (Kscmh)"
    if is_native_scmh_series(col, loc_flow_unit):
        return "Flow (kScmh)" if flow_unit == "kScmh" else "Flow (Scmh)"
    if "flow" in col_lower:
        return f"Flow ({flow_unit})"
    return "Value"


def build_yearly_box_plot(
    df_year,
    selected_col,
    title,
    colour,
    flow_unit="Kscmh",
    loc_flow_unit=None,
):
    plot_name = get_display_series_name(selected_col, flow_unit, loc_flow_unit)
    y_vals = get_display_series_values(
        df_year[selected_col], selected_col, flow_unit, loc_flow_unit
    )
    stats_df = pd.DataFrame({"Year": df_year.index.year, "Value": y_vals}).dropna()
    if stats_df.empty:
        return None

    grouped = stats_df.groupby("Year")["Value"]
    summary = grouped.agg(count="count", mean="mean", min="min", max="max")
    quantiles = grouped.quantile([0.25, 0.5, 0.75]).unstack()
    quantiles = quantiles.rename(columns={0.25: "q1", 0.5: "median", 0.75: "q3"})
    summary = summary.join(quantiles)

    iqr = summary["q3"] - summary["q1"]
    lower_bounds = summary["q1"] - 1.5 * iqr
    upper_bounds = summary["q3"] + 1.5 * iqr
    lower_fences = []
    upper_fences = []
    for year, year_values in grouped:
        inlier_values = year_values[
            (year_values >= lower_bounds.loc[year])
            & (year_values <= upper_bounds.loc[year])
        ]
        if inlier_values.empty:
            lower_fences.append(float(year_values.min()))
            upper_fences.append(float(year_values.max()))
        else:
            lower_fences.append(float(inlier_values.min()))
            upper_fences.append(float(inlier_values.max()))

    summary["lowerfence"] = lower_fences
    summary["upperfence"] = upper_fences
    summary = summary.reset_index()
    summary["Year"] = summary["Year"].astype(str)

    fig = go.Figure()
    fig.add_trace(
        go.Box(
            x=summary["Year"],
            q1=summary["q1"],
            median=summary["median"],
            q3=summary["q3"],
            lowerfence=summary["lowerfence"],
            upperfence=summary["upperfence"],
            mean=summary["mean"],
            customdata=summary[
                ["count", "min", "q1", "median", "q3", "max", "mean"]
            ].to_numpy(),
            hovertemplate=(
                "<b>Year %{x}</b><br>"
                "Count %{customdata[0]:,.0f}<br>"
                "Min %{customdata[1]:,.4f}<br>"
                "Q1 %{customdata[2]:,.4f}<br>"
                "Median %{customdata[3]:,.4f}<br>"
                "Q3 %{customdata[4]:,.4f}<br>"
                "Max %{customdata[5]:,.4f}<br>"
                "Mean %{customdata[6]:,.4f}<extra></extra>"
            ),
            name=plot_name,
            marker_color=colour,
            line=dict(color=colour),
            fillcolor=blend_hex(colour, PANEL_BG, 0.30),
            boxmean=True,
            boxpoints=False,
        )
    )
    fig.update_layout(
        xaxis_title="Year",
        yaxis_title=get_series_axis_label(selected_col, flow_unit, loc_flow_unit),
    )
    fig.update_xaxes(
        type="category",
        categoryorder="array",
        categoryarray=summary["Year"].tolist(),
    )
    return apply_dark_layout(fig, title)


def build_descriptive_stats(df, flow_unit="Kscmh", loc_flow_unit=None):
    display_df = pd.DataFrame(index=df.index)
    for col in df.select_dtypes(include="number").columns:
        display_name = get_display_series_name(col, flow_unit, loc_flow_unit)
        display_df[display_name] = get_display_series_values(
            df[col], col, flow_unit, loc_flow_unit
        )

    desc = display_df.describe().T
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


def get_season_window_bounds(season, season_year, tz=None):
    season_year = int(season_year)
    if season == "Winter":
        start = pd.Timestamp(year=season_year - 1, month=12, day=1)
        end = pd.Timestamp(year=season_year, month=3, day=1) - pd.Timedelta(days=1)
    elif season == "Spring":
        start = pd.Timestamp(year=season_year, month=3, day=1)
        end = pd.Timestamp(year=season_year, month=6, day=1) - pd.Timedelta(days=1)
    elif season == "Summer":
        start = pd.Timestamp(year=season_year, month=6, day=1)
        end = pd.Timestamp(year=season_year, month=9, day=1) - pd.Timedelta(days=1)
    else:
        start = pd.Timestamp(year=season_year, month=9, day=1)
        end = pd.Timestamp(year=season_year, month=12, day=1) - pd.Timedelta(days=1)
    if tz is not None:
        start = start.tz_localize(tz)
        end = end.tz_localize(tz)
    return start.normalize(), end.normalize()


def build_seasonal_summary_df(series, col, flow_unit, loc_flow_unit=None):
    display_series = get_display_series_values(
        series.dropna(), col, flow_unit, loc_flow_unit
    )
    if display_series.empty:
        return pd.DataFrame()

    daily = display_series.resample("D").mean().dropna()
    if daily.empty:
        return pd.DataFrame()

    seasonal_df = daily.to_frame(name="Value")
    seasonal_df["Season"] = seasonal_df.index.month.map(SEASON_BY_MONTH)
    seasonal_df["SeasonYear"] = (
        seasonal_df.index.year + (seasonal_df.index.month == 12).astype(int)
    )

    seasonal_summary = (
        seasonal_df.groupby(["SeasonYear", "Season"])
        .agg(
            MeanValue=("Value", "mean"),
            ObservedDays=("Value", "count"),
        )
        .reset_index()
    )
    if seasonal_summary.empty:
        return seasonal_summary

    series_tz = daily.index.tz
    available_start = daily.index.min().normalize()
    available_end = daily.index.max().normalize()

    window_starts = []
    window_ends = []
    expected_days = []
    for season_year, season in zip(
        seasonal_summary["SeasonYear"], seasonal_summary["Season"]
    ):
        season_start, season_end = get_season_window_bounds(
            season, season_year, tz=series_tz
        )
        overlap_start = max(season_start, available_start)
        overlap_end = min(season_end, available_end)
        if overlap_end < overlap_start:
            window_starts.append(pd.NaT)
            window_ends.append(pd.NaT)
            expected_days.append(0)
        else:
            window_starts.append(overlap_start)
            window_ends.append(overlap_end)
            expected_days.append((overlap_end - overlap_start).days + 1)

    seasonal_summary["WindowStart"] = window_starts
    seasonal_summary["WindowEnd"] = window_ends
    seasonal_summary["ExpectedDays"] = expected_days
    seasonal_summary["CoveragePct"] = (
        100.0 * seasonal_summary["ObservedDays"] / seasonal_summary["ExpectedDays"]
    ).fillna(0.0)
    seasonal_summary["MarkerSize"] = (
        7.0
        + 4.5
        * seasonal_summary["CoveragePct"].clip(lower=45.0, upper=100.0).sub(45.0)
        / 55.0
    )
    seasonal_summary["Season"] = pd.Categorical(
        seasonal_summary["Season"], categories=SEASON_ORDER, ordered=True
    )
    seasonal_summary = seasonal_summary.sort_values(
        ["SeasonYear", "Season"]
    ).reset_index(drop=True)
    return seasonal_summary


def build_seasonal_trend_chart(series, col, title, base_colour, flow_unit, loc_flow_unit=None):
    seasonal_summary = build_seasonal_summary_df(
        series, col, flow_unit, loc_flow_unit
    )
    if seasonal_summary.empty:
        return None, seasonal_summary

    season_colours = get_location_season_colours(base_colour)
    full_years = list(
        range(
            int(seasonal_summary["SeasonYear"].min()),
            int(seasonal_summary["SeasonYear"].max()) + 1,
        )
    )
    yaxis_label = get_series_axis_label(col, flow_unit, loc_flow_unit)
    fig = go.Figure()
    for season in SEASON_ORDER:
        season_frame = (
            seasonal_summary[seasonal_summary["Season"] == season]
            .set_index("SeasonYear")
            .reindex(full_years)
        )
        if season_frame["MeanValue"].notna().sum() == 0:
            continue

        window_start_labels = season_frame["WindowStart"].apply(
            lambda ts: ts.strftime("%Y-%m-%d") if pd.notna(ts) else ""
        )
        window_end_labels = season_frame["WindowEnd"].apply(
            lambda ts: ts.strftime("%Y-%m-%d") if pd.notna(ts) else ""
        )
        customdata = pd.DataFrame(
            {
                "window_start": window_start_labels,
                "window_end": window_end_labels,
                "observed_days": season_frame["ObservedDays"].fillna(0.0),
                "expected_days": season_frame["ExpectedDays"].fillna(0.0),
                "coverage_pct": season_frame["CoveragePct"].fillna(0.0),
            }
        ).to_numpy()

        fig.add_trace(
            go.Scatter(
                x=full_years,
                y=season_frame["MeanValue"],
                mode="lines+markers",
                name=season,
                line=dict(
                    color=season_colours[season],
                    width=2.8,
                    dash=SEASON_LINE_DASHES[season],
                ),
                marker=dict(
                    size=season_frame["MarkerSize"].fillna(0.0).tolist(),
                    symbol=SEASON_MARKER_SYMBOLS[season],
                    color=season_colours[season],
                    line=dict(
                        color=blend_hex(season_colours[season], TEXT_COL, 0.22),
                        width=1.1,
                    ),
                ),
                customdata=customdata,
                connectgaps=False,
                hovertemplate=(
                    f"<b>{season}</b><br>"
                    "Season year %{x}<br>"
                    f"{yaxis_label} %{{y:,.4f}}<br>"
                    "Window %{customdata[0]} → %{customdata[1]}<br>"
                    "Observed %{customdata[2]:,.0f} of %{customdata[3]:,.0f} days<br>"
                    "Coverage %{customdata[4]:.1f}%<extra></extra>"
                ),
            )
        )

    if not fig.data:
        return None, seasonal_summary

    fig.update_layout(
        xaxis_title="Season year",
        yaxis_title=yaxis_label,
        legend_title_text="Season",
    )
    fig = apply_dark_layout(fig, title)
    fig.update_xaxes(
        tickmode="array",
        tickvals=full_years,
        ticktext=[str(year) for year in full_years],
    )
    return fig, seasonal_summary


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
# HELPER: THRESHOLD EXPLORER CHART
# ======================================================
def build_threshold_explorer_chart(
    df,
    threshold_col,
    pct,
    side,
    title,
    colour_map,
    flow_unit="Kscmh",
    loc_flow_unit=None,
    freq="D",
    comparison_view="Separated (actual units)",
    trace_name_suffix="",
):
    """
    Filter df to rows where threshold_col is in the chosen extreme (top/bottom/both
    percentile), optionally resample, then plot all columns.

    Returns (fig, cutoff_label, n_rows_in_filter, raw_points, plotted_points, thin_step).
    """
    q = pct / 100.0
    if side.startswith("Top"):
        cutoff = float(df[threshold_col].quantile(1.0 - q))
        mask = df[threshold_col] >= cutoff
        display_cutoff = get_display_value(
            cutoff, threshold_col, flow_unit, loc_flow_unit
        )
        cutoff_lines = [
            {
                "value": display_cutoff,
                "annotation_text": f"Threshold (≥ {display_cutoff:,.3g}, P{100 - pct})",
                "annotation_position": "top right",
            }
        ]
        cutoff_label = f"≥ {display_cutoff:,.3g} (P{100 - pct})"
    elif side.startswith("Bottom"):
        cutoff = float(df[threshold_col].quantile(q))
        mask = df[threshold_col] <= cutoff
        display_cutoff = get_display_value(
            cutoff, threshold_col, flow_unit, loc_flow_unit
        )
        cutoff_lines = [
            {
                "value": display_cutoff,
                "annotation_text": f"Threshold (≤ {display_cutoff:,.3g}, P{pct})",
                "annotation_position": "bottom right",
            }
        ]
        cutoff_label = f"≤ {display_cutoff:,.3g} (P{pct})"
    else:  # Both extremes
        lo = float(df[threshold_col].quantile(q))
        hi = float(df[threshold_col].quantile(1.0 - q))
        mask = (df[threshold_col] <= lo) | (df[threshold_col] >= hi)
        display_lo = get_display_value(lo, threshold_col, flow_unit, loc_flow_unit)
        display_hi = get_display_value(hi, threshold_col, flow_unit, loc_flow_unit)
        cutoff_lines = [
            {
                "value": display_lo,
                "annotation_text": f"Lower threshold (≤ {display_lo:,.3g}, P{pct})",
                "annotation_position": "bottom right",
            },
            {
                "value": display_hi,
                "annotation_text": f"Upper threshold (≥ {display_hi:,.3g}, P{100 - pct})",
                "annotation_position": "top right",
            },
        ]
        cutoff_label = f"≤ {display_lo:,.3g} or ≥ {display_hi:,.3g} (P{pct} / P{100 - pct})"

    filtered = df[mask]
    n_filtered = int(mask.sum())

    if filtered.empty or n_filtered == 0:
        return None, cutoff_label, 0, 0, 0, 1

    if freq != "1min":
        plot_df = filtered.resample(freq).mean().dropna(how="all")
    else:
        plot_df = filtered.dropna(how="all")

    if plot_df.empty:
        return None, cutoff_label, n_filtered, 0, 0, 1

    raw_points = len(plot_df)
    plot_df, thin_step = thin_time_series(plot_df)
    plotted_points = len(plot_df)

    if plot_df.empty:
        return None, cutoff_label, n_filtered, raw_points, 0, thin_step

    default_colour = get_colour_fallback(colour_map)
    time_hover_format = "%Y-%m-%d %H:%M" if freq in {"1min", "15min", "30min", "h"} else "%Y-%m-%d"

    if comparison_view == "Separated (actual units)":
        flow_cols, pressure_cols, _ = split_series_columns(plot_df.columns)
        has_two_rows = bool(flow_cols and pressure_cols)
        nrows = 2 if has_two_rows else 1
        flow_label = get_flow_axis_label(flow_cols, flow_unit, loc_flow_unit)

        fig = make_subplots(rows=nrows, cols=1, shared_xaxes=True, vertical_spacing=0.08)

        for col in plot_df.columns:
            base_col = colour_map.get(col, default_colour)
            is_pressure = col in pressure_cols
            row = 2 if (has_two_rows and is_pressure) else 1
            y_vals = get_display_series_values(plot_df[col], col, flow_unit, loc_flow_unit)
            display_name = (
                f"{get_display_series_name(col, flow_unit, loc_flow_unit)}{trace_name_suffix}"
            )
            fig.add_trace(
                go.Scatter(
                    x=plot_df.index,
                    y=y_vals,
                    mode="lines",
                    name=display_name,
                    line=dict(color=base_col, width=2.2),
                    hovertemplate=(
                        f"<b>{display_name}</b><br>%{{x|{time_hover_format}}}"
                        f"<br>%{{y:,.3g}}<extra></extra>"
                    ),
                ),
                row=row,
                col=1,
            )

            if col == threshold_col:
                for cutoff_line in cutoff_lines:
                    fig.add_hline(
                        y=cutoff_line["value"],
                        line_dash="dash",
                        line_color=ACCENT_COLOUR,
                        annotation_text=cutoff_line["annotation_text"],
                        annotation_position=cutoff_line["annotation_position"],
                        annotation_font_color=ACCENT_COLOUR,
                        row=row,
                        col=1,
                    )

        fig.update_yaxes(title_text=flow_label, row=1, col=1)
        if has_two_rows:
            fig.update_yaxes(title_text="Bar", row=2, col=1)
    else:
        span = (plot_df.max() - plot_df.min()).replace(0, pd.NA)
        normalized = ((plot_df - plot_df.min()) / span).fillna(0.0)
        fig = go.Figure()
        for col in normalized.columns:
            base_col = colour_map.get(col, default_colour)
            display_name = (
                f"{get_display_series_name(col, flow_unit, loc_flow_unit)}{trace_name_suffix}"
            )
            fig.add_trace(
                go.Scatter(
                    x=normalized.index,
                    y=normalized[col],
                    mode="lines",
                    name=display_name,
                    line=dict(color=base_col, width=2.2),
                    hovertemplate=(
                        f"<b>{display_name}</b><br>%{{x|{time_hover_format}}}"
                        f"<br>%{{y:,.3f}}<extra></extra>"
                    ),
                )
            )

        fig.update_layout(xaxis_title="Time", yaxis_title="Normalized value (0-1)")

    fig = apply_dark_layout(fig, title)
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig, cutoff_label, n_filtered, raw_points, plotted_points, thin_step


# ======================================================
# HELPER: BUILD STACKED LINE CHART (individual mode)
# ======================================================
def build_stacked_line_chart(
    plot_df, title, xaxis_title, colour_map, flow_unit="Kscmh", mode="lines", marker_size=7,
    loc_flow_unit=None,
):
    flow_cols, pressure_cols, other_cols = split_series_columns(plot_df.columns)
    has_two_rows = bool(flow_cols and pressure_cols)
    nrows = 2 if has_two_rows else 1
    flow_label = get_flow_axis_label(flow_cols, flow_unit, loc_flow_unit)
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
        trace_name = get_display_series_name(col, flow_unit, loc_flow_unit)
        if col in flow_cols:
            y_vals = get_display_series_values(y_vals, col, flow_unit, loc_flow_unit)

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


def build_comparison_chart_normalised(plot_df, title, xaxis_title, mode="lines", marker_size=7):
    """Same as build_comparison_chart but each series is scaled to [0, 1] so
    locations with very different absolute flows can be compared visually."""
    span = (plot_df.max() - plot_df.min()).replace(0, pd.NA)
    norm_df = ((plot_df - plot_df.min()) / span).fillna(0.0)
    fig = go.Figure()
    for col in norm_df.columns:
        colour = COMPARE_SERIES_COLOURS.get(col, LOCATION_COLOURS.get(col, "#6366f1"))
        raw_min = float(plot_df[col].min()) if col in plot_df.columns else 0
        raw_max = float(plot_df[col].max()) if col in plot_df.columns else 0
        trace_kwargs = dict(
            x=norm_df.index,
            y=norm_df[col],
            mode=mode,
            name=col,
            line=dict(color=colour, width=2.4),
            customdata=plot_df[[col]].values,
            hovertemplate=(
                f"<b>{col}</b><br>%{{x}}<br>"
                f"Normalised: %{{y:.3f}}<br>"
                f"Actual: %{{customdata[0]:,.4f}} Kscmh<extra></extra>"
            ),
        )
        if "markers" in trace_kwargs.get("mode", ""):
            trace_kwargs["marker"] = dict(size=marker_size)
        fig.add_trace(go.Scatter(**trace_kwargs))

    fig.update_layout(
        xaxis_title=xaxis_title,
        yaxis_title="Normalised flow (0 = min, 1 = max per series)",
    )
    fig = apply_dark_layout(fig, title)
    fig.add_annotation(
        text="Each series scaled to its own min/max — hover to see actual Kscmh values",
        xref="paper", yref="paper", x=0, y=-0.13,
        showarrow=False, font=dict(size=11, color=SUBTEXT_COL), xanchor="left",
    )
    return fig


def build_comparison_chart_small_multiples(plot_df, title, xaxis_title, mode="lines", marker_size=7):
    """One subplot per series, each with its own independent y-axis."""
    cols = [c for c in plot_df.columns if plot_df[c].notna().any()]
    n = len(cols)
    if n == 0:
        return go.Figure()

    ncols = 2
    nrows = math.ceil(n / ncols)
    subplot_titles = cols

    fig = make_subplots(
        rows=nrows,
        cols=ncols,
        shared_xaxes=True,
        subplot_titles=subplot_titles,
        vertical_spacing=0.10,
        horizontal_spacing=0.08,
    )

    for idx, col in enumerate(cols):
        row = idx // ncols + 1
        col_pos = idx % ncols + 1
        colour = COMPARE_SERIES_COLOURS.get(col, LOCATION_COLOURS.get(col, "#6366f1"))
        trace_kwargs = dict(
            x=plot_df.index,
            y=plot_df[col],
            mode=mode,
            name=col,
            line=dict(color=colour, width=2.2),
            showlegend=False,
        )
        if "markers" in mode:
            trace_kwargs["marker"] = dict(size=marker_size)
        fig.add_trace(go.Scatter(**trace_kwargs), row=row, col=col_pos)
        fig.update_yaxes(title_text="Kscmh", row=row, col=col_pos,
                         gridcolor="rgba(255,255,255,0.08)",
                         linecolor="rgba(255,255,255,0.18)")

    height = 260 * nrows + 80
    fig.update_layout(
        height=height,
        template="plotly_dark",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_COL, family="Hind, sans-serif"),
        title=dict(text=title, font=dict(size=20, color=TEXT_COL, family="Hind, sans-serif")),
        margin=dict(l=66, r=72, t=90, b=62),
        hovermode="x unified",
    )
    fig.update_xaxes(
        title_text=xaxis_title,
        gridcolor="rgba(255,255,255,0.08)",
        linecolor="rgba(255,255,255,0.18)",
        automargin=True,
    )
    for annotation in fig.layout.annotations:
        annotation.font = dict(color=TEXT_COL, size=13, family="Hind, sans-serif")
    return fig


CHART_VIEW_OPTIONS = [
    "All series — shared axis",
    "Normalised (0–1 per series)",
    "Small multiples (separate panels)",
]


def render_comparison_chart(plot_df, title, xaxis_title, chart_view, mode="lines", marker_size=7):
    """Dispatch to the right chart builder based on the chart_view dropdown value."""
    if chart_view == "Normalised (0–1 per series)":
        return build_comparison_chart_normalised(plot_df, title, xaxis_title, mode, marker_size)
    if chart_view == "Small multiples (separate panels)":
        return build_comparison_chart_small_multiples(plot_df, title, xaxis_title, mode, marker_size)
    return build_comparison_chart(plot_df, title, xaxis_title, mode, marker_size)


def build_dual_axis_chart(
    df,
    flow_cols,
    pressure_cols,
    title,
    colour_map,
    flow_label="Flow (Kscmh)",
    pressure_label="Pressure (Bar)",
    flow_unit="Kscmh",
    loc_flow_unit=None,
    xaxis_title="Time",
):
    """Dual y-axis chart: flow series on the left axis, pressure on the right.

    Uses secondary_y subplots so both axes are independent and clearly labelled,
    matching the style seen in the reference matplotlib charts.
    """
    from plotly.subplots import make_subplots

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    default_colour = next(iter(colour_map.values()), "#6366f1")

    for col in flow_cols:
        if col not in df.columns:
            continue
        colour = colour_map.get(col, default_colour)
        y_vals = get_display_series_values(df[col], col, flow_unit, loc_flow_unit)
        display_name = get_display_series_name(col, flow_unit, loc_flow_unit)
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=y_vals,
                mode="lines",
                name=display_name,
                line=dict(color=colour, width=2.2),
                hovertemplate=f"<b>{display_name}</b><br>%{{x|%Y-%m-%d %H:%M}}<br>%{{y:,.4f}}<extra></extra>",
            ),
            secondary_y=False,
        )

    for col in pressure_cols:
        if col not in df.columns:
            continue
        colour = colour_map.get(col, default_colour)
        display_name = get_display_series_name(col, flow_unit, loc_flow_unit)
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[col],
                mode="lines",
                name=display_name,
                line=dict(color=colour, width=2.2, dash="dot"),
                hovertemplate=f"<b>{display_name}</b><br>%{{x|%Y-%m-%d %H:%M}}<br>%{{y:,.4f}} Bar<extra></extra>",
            ),
            secondary_y=True,
        )

    fig.update_yaxes(
        title_text=flow_label,
        secondary_y=False,
        gridcolor="rgba(255,255,255,0.08)",
        linecolor="rgba(255,255,255,0.18)",
    )
    fig.update_yaxes(
        title_text=pressure_label,
        secondary_y=True,
        gridcolor="rgba(255,255,255,0.04)",
        linecolor="rgba(255,255,255,0.12)",
        showgrid=False,
    )
    fig.update_xaxes(
        title_text=xaxis_title,
        gridcolor="rgba(255,255,255,0.08)",
        linecolor="rgba(255,255,255,0.18)",
        automargin=True,
    )
    fig = apply_dark_layout(fig, title)
    return fig


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
map_active = [is_compare or (is_biomethane and n in BIOMETHANE_SITES) or n == view_mode for n in map_names]
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
    "Monthly": "MS",
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

        ctrl1, ctrl2, ctrl3, ctrl4 = st.columns(4)
        with ctrl4:
            trend_location = st.selectbox(
                "Series to show",
                options=["All series"] + list(COMPARE_SERIES.keys()),
                index=0,
                key="compare_trend_location",
            )
        with ctrl3:
            agg_choice = st.selectbox(
                "Data granularity",
                options=list(FREQ_MAP.keys()),
                index=list(FREQ_MAP.keys()).index("Daily"),
            )
        with ctrl2:
            trend_chart_view = st.selectbox(
                "Chart view",
                options=CHART_VIEW_OPTIONS,
                index=0,
                key="trend_chart_view",
                help=(
                    "All series — shared axis: compare absolute flow values.\n"
                    "Normalised: scale each series to 0–1 so seasonal patterns are equally visible.\n"
                    "Small multiples: one panel per series, each with its own y-axis."
                ),
            )

        compare_trend_df = build_compare_resampled_df(
            FREQ_MAP[agg_choice], start_date, end_date, remove_outliers
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

        fig_trend = render_comparison_chart(plot_data, trend_title, "Time", trend_chart_view)
        st.caption(focus_caption)
        if thin_step > 1:
            st.caption(
                f"To keep things fast, this chart shows {len(plot_data):,} of {raw_points:,} points."
            )
        st.plotly_chart(fig_trend, width="stretch")

    elif compare_section == "Daily averages":
        st.markdown("## Daily averages")
        daily_chart_view = st.selectbox(
            "Chart view",
            options=CHART_VIEW_OPTIONS,
            index=0,
            key="daily_chart_view",
            help=(
                "All series — shared axis: compare absolute flow values.\n"
                "Normalised: scale each series to 0–1 so seasonal patterns are equally visible.\n"
                "Small multiples: one panel per series, each with its own y-axis."
            ),
        )
        compare_daily = build_compare_resampled_df("D", start_date, end_date, remove_outliers)
        fig_daily = render_comparison_chart(compare_daily, "Daily Average Flow", "Date", daily_chart_view)
        st.plotly_chart(fig_daily, width="stretch")

    elif compare_section == "Monthly averages":
        st.markdown("## Monthly averages (multi-year seasonality)")
        monthly_chart_view = st.selectbox(
            "Chart view",
            options=CHART_VIEW_OPTIONS,
            index=0,
            key="monthly_chart_view",
            help=(
                "All series — shared axis: compare absolute flow values.\n"
                "Normalised: scale each series to 0–1 so seasonal patterns are equally visible.\n"
                "Small multiples: one panel per series, each with its own y-axis."
            ),
        )
        compare_monthly = build_compare_resampled_df("MS", start_date, end_date, remove_outliers)
        fig_monthly = render_comparison_chart(
            compare_monthly, "Monthly Average Flow", "Date", monthly_chart_view
        )
        st.plotly_chart(fig_monthly, width="stretch")

    elif compare_section == "Average by calendar month":
        st.markdown("## Average by calendar month")
        cal_month_chart_view = st.selectbox(
            "Chart view",
            options=CHART_VIEW_OPTIONS,
            index=0,
            key="cal_month_chart_view",
            help=(
                "All series — shared axis: compare absolute flow values.\n"
                "Normalised: scale each series to 0–1 so seasonal patterns are equally visible.\n"
                "Small multiples: one panel per series, each with its own y-axis."
            ),
        )
        month_labels = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ]
        monthly_pat = build_compare_pattern_df("month", start_date, end_date, remove_outliers)
        monthly_pat.index = month_labels[: len(monthly_pat)]
        fig_mpat = render_comparison_chart(
            monthly_pat,
            "Average Flow by Calendar Month",
            "Month",
            cal_month_chart_view,
            mode="lines+markers",
            marker_size=8,
        )
        st.plotly_chart(fig_mpat, width="stretch")

    elif compare_section == "Average by hour of day":
        st.markdown("## Average by hour of day")
        hourly_chart_view = st.selectbox(
            "Chart view",
            options=CHART_VIEW_OPTIONS,
            index=0,
            key="hourly_chart_view",
            help=(
                "All series — shared axis: compare absolute flow values.\n"
                "Normalised: scale each series to 0–1 so seasonal patterns are equally visible.\n"
                "Small multiples: one panel per series, each with its own y-axis."
            ),
        )
        compare_hourly_pat = build_compare_pattern_df("hour", start_date, end_date, remove_outliers)
        fig_hpat = render_comparison_chart(
            compare_hourly_pat,
            "Average Flow by Hour of Day",
            "Hour",
            hourly_chart_view,
            mode="lines+markers",
            marker_size=7,
        )
        st.plotly_chart(fig_hpat, width="stretch")

    elif compare_section == "Distribution of daily flow by year":
        st.markdown("## Distribution of daily flow by year")
        compare_daily_box = build_compare_resampled_df("D", start_date, end_date, remove_outliers)
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
        if fig_box is None:
            st.info("No data is available for that series in the selected date range.")
        else:
            st.caption("Built from precomputed yearly box statistics for faster loading.")
            st.plotly_chart(fig_box, width="stretch")

    elif compare_section == "Correlation between flow series":
        st.markdown("## Correlation between flow series")
        compare_corr = build_compare_resampled_df("D", start_date, end_date, remove_outliers).corr()
        st.caption("Computed from daily mean flow series to keep compare mode responsive.")
        fig_corr = build_correlation_heatmap(compare_corr, "Correlation Between Flow Series")
        st.plotly_chart(fig_corr, width="stretch")

    else:
        st.markdown("## Raw data")
        compare_raw = build_compare_resampled_df("1min", start_date, end_date, remove_outliers)
        with st.expander("Show comparison data (first and last 100 rows)", expanded=True):
            show_head_tail_dataframe(compare_raw)


# ##########################################################################
#                     INDIVIDUAL LOCATION VIEW
# ##########################################################################
elif not is_biomethane:
    loc_meta = LOCATIONS[view_mode]
    colour_map = SERIES_COLOUR_MAPS.get(view_mode, {})
    default_colour = get_colour_fallback(
        colour_map, LOCATION_COLOURS.get(view_mode, "#6366f1")
    )

    # --------------------------------------------------
    # Summary statistics
    # --------------------------------------------------
    st.markdown("## Summary statistics")

    _kpi_col = loc_meta["compare_col"] if loc_meta["compare_col"] in loc_df.columns else loc_df.columns[0]
    _first_valid = loc_df[_kpi_col].first_valid_index()
    _last_valid = loc_df[_kpi_col].last_valid_index()
    start_ts = _first_valid.strftime("%Y-%m-%d %H:%M") if _first_valid is not None else "N/A"
    end_ts = _last_valid.strftime("%Y-%m-%d %H:%M") if _last_valid is not None else "N/A"

    st.caption("Current filter KPIs")
    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        st.metric("Start date", start_ts)
    with mc2:
        st.metric("End date", end_ts)
    with mc3:
        # Use non-null count on the primary compare column so locations
        # where data starts later (e.g. Charlton from 2022) don't report
        # the full index length which includes NaN-filled rows.
        _count_col = loc_meta["compare_col"] if loc_meta["compare_col"] in loc_df.columns else loc_df.columns[0]
        st.metric("Total records (filtered)", f"{int(loc_df[_count_col].count()):,}")

    flow_unit = loc_meta["flow_unit"]
    if loc_meta["flow_unit"] == "Scmh":
        flow_unit = st.session_state.get(f"{view_mode}_flow_unit", "kScmh")

    st.markdown("#### Descriptive statistics")
    desc = build_descriptive_stats(
        loc_df,
        flow_unit=flow_unit,
        loc_flow_unit=loc_meta["flow_unit"],
    )
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

    if loc_meta["flow_unit"] == "Scmh":
        flow_unit = st.radio(
            "Flow display unit",
            options=["Scmh", "kScmh"],
            horizontal=True,
            index=0 if flow_unit == "Scmh" else 1,
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
        f"Annual non-null record counts for {get_display_series_name(record_count_col, flow_unit=loc_meta['flow_unit'], loc_flow_unit=loc_meta['flow_unit'])} in the selected date range."
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
    # Threshold Explorer
    # --------------------------------------------------
    st.markdown("## Threshold Explorer")

    numeric_cols = list(loc_df.select_dtypes(include="number").columns)
    st.caption(
        "Filter to timestamps where one selected series sits in an extreme percentile band, then compare how the other series behave."
    )
    if not numeric_cols:
        st.info("No numeric series are available for threshold exploration.")
    else:
        te_ctrl_a, te_ctrl_b, te_ctrl_c = st.columns(3)
        with te_ctrl_a:
            threshold_col = st.selectbox(
                "Threshold column",
                options=numeric_cols,
                format_func=lambda c: get_display_series_name(
                    c, flow_unit, loc_meta["flow_unit"]
                ),
                key=f"{view_mode}_te_col",
            )
        with te_ctrl_b:
            threshold_pct = st.number_input(
                "Percentile (%)",
                min_value=1,
                max_value=49,
                value=10,
                step=1,
                key=f"{view_mode}_te_pct",
                help="10 means the top 10%, bottom 10%, or both extremes depending on the option you choose.",
            )
        with te_ctrl_c:
            threshold_side = st.selectbox(
                "Which extreme?",
                options=[
                    "Top (above threshold)",
                    "Bottom (below threshold)",
                    "Both extremes",
                ],
                index=0,
                key=f"{view_mode}_te_side",
            )

        te_ctrl_d, te_ctrl_e, te_ctrl_f = st.columns(3)
        with te_ctrl_d:
            threshold_base, threshold_focus_caption = select_time_focus(
                loc_df, key_prefix=f"{view_mode}_te"
            )
        with te_ctrl_e:
            threshold_agg_choice = st.selectbox(
                "Data granularity",
                options=list(FREQ_MAP.keys()),
                index=list(FREQ_MAP.keys()).index("Daily"),
                key=f"{view_mode}_te_agg",
            )
        with te_ctrl_f:
            threshold_view = st.selectbox(
                "Comparison view",
                options=["Separated (actual units)", "Normalized (0-1)"],
                index=0,
                key=f"{view_mode}_te_view",
            )

        if threshold_base.empty:
            st.info("No data in this period. Pick a different year/month/day.")
        else:
            threshold_col_display = get_display_series_name(
                threshold_col, flow_unit, loc_meta["flow_unit"]
            )
            threshold_focus_text = {
                "Top (above threshold)": f"top {int(threshold_pct)}%",
                "Bottom (below threshold)": f"bottom {int(threshold_pct)}%",
                "Both extremes": f"top and bottom {int(threshold_pct)}%",
            }[threshold_side]
            threshold_title = (
                f"{view_mode} – Trends when {threshold_col_display} is in the "
                f"{threshold_focus_text}"
            )
            if threshold_view == "Normalized (0-1)":
                threshold_title += " (normalized)"

            trace_name_suffix = (
                "" if threshold_agg_choice == "1min" else f" ({threshold_agg_choice} avg)"
            )
            (
                fig_thresh,
                cutoff_label,
                n_filtered,
                raw_points,
                plotted_points,
                thin_step,
            ) = build_threshold_explorer_chart(
                df=threshold_base,
                threshold_col=threshold_col,
                pct=int(threshold_pct),
                side=threshold_side,
                title=threshold_title,
                colour_map=colour_map,
                flow_unit=flow_unit,
                loc_flow_unit=loc_meta["flow_unit"],
                freq=FREQ_MAP[threshold_agg_choice],
                comparison_view=threshold_view,
                trace_name_suffix=trace_name_suffix,
            )
            if fig_thresh is None:
                st.info("No data points meet the threshold condition for this period.")
            else:
                pct_of_total = (
                    n_filtered / max(int(threshold_base[threshold_col].count()), 1)
                ) * 100
                aggregation_caption = (
                    "showing raw filtered timestamps"
                    if threshold_agg_choice == "1min"
                    else f"aggregated to {threshold_agg_choice.lower()} means"
                )
                st.caption(threshold_focus_caption)
                st.caption(
                    f"Threshold: **{threshold_col_display} {cutoff_label}** · "
                    f"{n_filtered:,} readings ({pct_of_total:.1f}% of current period) · "
                    f"{aggregation_caption}"
                )
                if threshold_view == "Normalized (0-1)":
                    st.caption("Each series is scaled independently to 0-1 for shape comparison.")
                if thin_step > 1:
                    st.caption(
                        f"To keep things fast, this chart shows {plotted_points:,} of {raw_points:,} points."
                    )
                st.plotly_chart(fig_thresh, width="stretch")

    # --------------------------------------------------
    # Trend over time
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
        loc_flow_unit = loc_meta["flow_unit"]
        flow_label = get_flow_axis_label(flow_cols, flow_unit, loc_flow_unit)
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
            trace_name = f"{get_display_series_name(col, flow_unit, loc_flow_unit)} ({agg_choice} avg)"
            if col in flow_cols:
                y_vals = get_display_series_values(y_vals, col, flow_unit, loc_flow_unit)

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
        loc_flow_unit = loc_meta["flow_unit"]
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
                    name=f"{get_display_series_name(col, flow_unit, loc_flow_unit)} ({agg_choice} avg)",
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
    # Seasonal trend by year
    # --------------------------------------------------
    st.markdown("## Seasonal trend by year")

    seasonal_col = st.selectbox(
        "Column to compare across seasons",
        options=list(loc_df.columns),
        format_func=lambda col: get_display_series_name(col, flow_unit, loc_meta["flow_unit"]),
        key=f"{view_mode}_seasonal_col",
    )
    st.caption(
        "Each point shows the mean of daily averages within that season. Winter groups December with the following January and February."
    )
    fig_seasonal, seasonal_summary = build_seasonal_trend_chart(
        loc_df[seasonal_col],
        seasonal_col,
        f"{view_mode} – {get_display_series_name(seasonal_col, flow_unit, loc_meta['flow_unit'])} Seasonal Trend",
        LOCATION_COLOURS.get(view_mode, default_colour),
        flow_unit,
        loc_flow_unit=loc_meta["flow_unit"],
    )
    if fig_seasonal is None:
        st.info("No seasonal data is available for that column in the selected date range.")
    else:
        st.caption(
            "Hover any point to see the seasonal window and how many daily means contributed to that average. Larger markers indicate higher day coverage within that season."
        )
        partial_points = int((seasonal_summary["CoveragePct"] < 99.9).sum())
        if partial_points > 0:
            st.caption(
                f"{partial_points} season-year point(s) have partial coverage because of the selected date range or missing data."
            )
        st.plotly_chart(fig_seasonal, width="stretch")

    loc_flow_unit = loc_meta["flow_unit"]

    # --------------------------------------------------
    # 2. Daily averages
    # --------------------------------------------------
    st.markdown("## Daily averages")

    daily = loc_df.resample("D").mean().dropna(how="all")
    fig_daily = build_stacked_line_chart(
        daily,
        f"{view_mode} – Daily Averages",
        "Date",
        colour_map,
        flow_unit=flow_unit,
        loc_flow_unit=loc_flow_unit,
    )
    st.plotly_chart(fig_daily, width="stretch")

    # --------------------------------------------------
    # 3. Monthly seasonality
    # --------------------------------------------------
    st.markdown("## Monthly averages (multi-year seasonality)")

    monthly = loc_df.resample("MS").mean().dropna(how="all")
    fig_monthly = build_stacked_line_chart(
        monthly,
        f"{view_mode} – Monthly Averages",
        "Date",
        colour_map,
        flow_unit=flow_unit,
        loc_flow_unit=loc_flow_unit,
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
        loc_flow_unit=loc_flow_unit,
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
        loc_flow_unit=loc_flow_unit,
        mode="lines+markers",
        marker_size=7,
    )
    st.plotly_chart(fig_hpat, width="stretch")

    # --------------------------------------------------
    # 6. Yearly distribution (boxplots)
    # --------------------------------------------------
    st.markdown("## Distribution of values by year")

    value_cols = list(loc_df.columns)

    selected_box_col = st.selectbox(
        "Series to show",
        options=value_cols,
        format_func=lambda col: get_display_series_name(col, flow_unit, loc_flow_unit),
        key=f"{view_mode}_box_series",
    )
    fig_box = build_yearly_box_plot(
        loc_df,
        selected_box_col,
        f"{view_mode} – {get_display_series_name(selected_box_col, flow_unit, loc_flow_unit)} Distribution by Year",
        colour_map.get(selected_box_col, default_colour),
        flow_unit=flow_unit,
        loc_flow_unit=loc_flow_unit,
    )
    if fig_box is None:
        st.info("No data is available for that series in the selected date range.")
    else:
        st.caption("Built from precomputed yearly box statistics for faster loading.")
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


# ##########################################################################
#                     BIOMETHANE INJECTION SITES PAGE
# ##########################################################################
elif is_biomethane:

    # ------------------------------------------------------------------
    # Site metadata: which columns are flow, which are pressure, colours
    # ------------------------------------------------------------------
    BM_SITES = {
        "Enfield": {
            "flow_cols": ["Enfield flow (F1)"],
            "pressure_cols": ["Enfield outlet (IP1)"],
            "flow_unit": "Scmh",      # native unit in parquet
            "flow_label": "Flow (Kscmh)",
            "pressure_label": "Outlet pressure (Bar)",
            "flow_scale": 1 / 1000,   # Scmh → Kscmh for display
        },
        "Charlton": {
            "flow_cols": ["Charlton flow (F1)"],
            "pressure_cols": ["Charlton outlet (MP1)"],
            "flow_unit": "Scmh",
            "flow_label": "Flow (Kscmh)",
            "pressure_label": "Outlet pressure (Bar)",
            "flow_scale": 1 / 1000,
        },
        "Great Hele": {
            "flow_cols": ["Flow (Scmh)"],
            "pressure_cols": ["Pressure (Bar)"],
            "flow_unit": "Scmh",
            "flow_label": "Flow (Kscmh)",
            "pressure_label": "Pressure (Bar)",
            "flow_scale": 1 / 1000,
        },
    }

    # Colour maps per site (reuse existing SERIES_COLOUR_MAPS where available)
    BM_COLOUR_MAPS = {
        site: SERIES_COLOUR_MAPS.get(site, {}) for site in BM_SITES
    }

    # ------------------------------------------------------------------
    # Load & filter all three site DataFrames
    # ------------------------------------------------------------------
    bm_dfs_raw = {}
    for site in BM_SITES:
        _raw = load_location(site)
        _filtered = filter_by_date(_raw, start_date, end_date)
        if remove_outliers:
            _bounds = compute_iqr_bounds(site)
            _filtered = apply_outlier_filter(_filtered, _bounds)
        bm_dfs_raw[site] = _filtered

    # ------------------------------------------------------------------
    # Helper: apply flow scale to produce display-ready Kscmh values
    # ------------------------------------------------------------------
    def _bm_display_df(site, df):
        """Return a copy of df with flow columns converted to Kscmh."""
        meta = BM_SITES[site]
        df = df.copy()
        for col in meta["flow_cols"]:
            if col in df.columns:
                df[col] = df[col] * meta["flow_scale"]
        return df

    # ------------------------------------------------------------------
    # Helper: dual-axis resample + chart for one site
    # ------------------------------------------------------------------
    def _bm_dual_chart(site, df, title, freq="D", xaxis_title="Date"):
        meta = BM_SITES[site]
        cmap = BM_COLOUR_MAPS[site]
        all_cols = meta["flow_cols"] + meta["pressure_cols"]
        available = [c for c in all_cols if c in df.columns]
        if not available or df.empty:
            return None
        sub = df[available]
        if freq != "1min":
            sub = sub.resample(freq).mean().dropna(how="all")
        sub, _ = thin_time_series(sub)
        sub = _bm_display_df(site, sub)
        return build_dual_axis_chart(
            sub,
            flow_cols=[c for c in meta["flow_cols"] if c in sub.columns],
            pressure_cols=[c for c in meta["pressure_cols"] if c in sub.columns],
            title=title,
            colour_map=cmap,
            flow_label=meta["flow_label"],
            pressure_label=meta["pressure_label"],
            xaxis_title=xaxis_title,
        )

    # ------------------------------------------------------------------
    # Helper: dual-axis pattern chart (group by month or hour)
    # ------------------------------------------------------------------
    def _bm_pattern_chart(site, df, groupby, title, xaxis_title):
        meta = BM_SITES[site]
        cmap = BM_COLOUR_MAPS[site]
        all_cols = meta["flow_cols"] + meta["pressure_cols"]
        available = [c for c in all_cols if c in df.columns]
        if not available or df.empty:
            return None
        sub = df[available].dropna(how="all")
        if groupby == "month":
            pat = sub.groupby(sub.index.month).mean()
        else:
            pat = sub.groupby(sub.index.hour).mean()
        pat = _bm_display_df(site, pat)
        return build_dual_axis_chart(
            pat,
            flow_cols=[c for c in meta["flow_cols"] if c in pat.columns],
            pressure_cols=[c for c in meta["pressure_cols"] if c in pat.columns],
            title=title,
            colour_map=cmap,
            flow_label=meta["flow_label"],
            pressure_label=meta["pressure_label"],
            xaxis_title=xaxis_title,
        )

    # ------------------------------------------------------------------
    # Summary statistics KPIs
    # ------------------------------------------------------------------
    st.markdown("## Summary statistics")
    st.caption("All flow values displayed in Kscmh · Pressure in Bar")

    for site in BM_SITES:
        meta = BM_SITES[site]
        df_site = bm_dfs_raw[site]
        colour = LOCATION_COLOURS.get(site, "#6366f1")
        st.markdown(
            f"<h4 style='color:{colour}; margin-bottom:0.2rem;'>{site}</h4>",
            unsafe_allow_html=True,
        )
        kpi_cols_site = meta["flow_cols"] + meta["pressure_cols"]
        kpi_cols_site = [c for c in kpi_cols_site if c in df_site.columns]
        if not kpi_cols_site or df_site.empty:
            st.info(f"No data for {site} in the selected date range.")
            continue

        mc = st.columns(len(kpi_cols_site) + 2)
        first_valid = df_site[kpi_cols_site[0]].first_valid_index()
        last_valid = df_site[kpi_cols_site[0]].last_valid_index()
        with mc[0]:
            st.metric("Start", first_valid.strftime("%Y-%m-%d") if first_valid else "–")
        with mc[1]:
            st.metric("End", last_valid.strftime("%Y-%m-%d") if last_valid else "–")
        for idx, col in enumerate(kpi_cols_site):
            with mc[idx + 2]:
                val = df_site[col].dropna()
                if col in meta["flow_cols"]:
                    display_val = val * meta["flow_scale"]
                    label = SERIES_DISPLAY_NAMES.get(col, col) + " mean (Kscmh)"
                else:
                    display_val = val
                    label = SERIES_DISPLAY_NAMES.get(col, col) + " mean (Bar)"
                st.metric(label, f"{float(display_val.mean()):,.4f}" if not display_val.empty else "–")

        # Descriptive stats table
        disp_df = df_site[kpi_cols_site].copy()
        for col in meta["flow_cols"]:
            if col in disp_df.columns:
                disp_df[col] = disp_df[col] * meta["flow_scale"]
        rename_map = {c: SERIES_DISPLAY_NAMES.get(c, c) for c in disp_df.columns}
        disp_df = disp_df.rename(columns=rename_map)
        desc = disp_df.describe().T
        if "50%" in desc.columns:
            desc.insert(2, "median", desc.pop("50%"))
        show_stretch_dataframe(
            desc.style.format(
                {"count": "{:,.0f}"}
                | {col: "{:,.4f}" for col in desc.columns if col != "count"}
            ),
            height=min(300, 80 + 28 * len(desc)),
        )
        st.markdown("")

    # ------------------------------------------------------------------
    # Section selector
    # ------------------------------------------------------------------
    st.markdown("## Analysis")
    bm_section = st.selectbox(
        "Section",
        options=[
            "Choose a section",
            "Flow comparison",
            "Pressure comparison",
            "Flow and pressure per site",
            "Average by calendar month",
            "Average by hour of day",
            "Flow vs pressure scatter",
            "Seasonal trend by year",
            "Distribution by year",
            "Correlation between sites",
            "Raw data",
        ],
        key="bm_section",
    )

    # Shorthand column name lists used across sections
    _BM_FLOW_COLS = [
        "Enfield \u2014 Flow (Kscmh)",
        "Charlton \u2014 Flow (Kscmh)",
        "Great Hele \u2014 Flow (Kscmh)",
    ]
    _BM_PRES_COLS = [
        "Enfield \u2014 Pressure (Bar)",
        "Charlton \u2014 Pressure (Bar)",
        "Great Hele \u2014 Pressure (Bar)",
    ]

    if bm_section == "Choose a section":
        st.info("Pick a section above to load its charts.")

    # ------------------------------------------------------------------
    elif bm_section == "Flow comparison":
        st.markdown("## Flow comparison")
        st.caption(
            "Injection flow from all three sites on one chart. "
            "All values in Kscmh (thousands of standard cubic metres per hour)."
        )
        bm_fc_ctrl1, bm_fc_ctrl2 = st.columns(2)
        with bm_fc_ctrl1:
            bm_fc_agg = st.selectbox(
                "Data granularity",
                options=list(FREQ_MAP.keys()),
                index=list(FREQ_MAP.keys()).index("Daily"),
                key="bm_fc_agg",
            )
        with bm_fc_ctrl2:
            bm_fc_view = st.selectbox(
                "Chart view",
                options=CHART_VIEW_OPTIONS,
                index=0,
                key="bm_fc_view",
                help=(
                    "All series on one axis: compare absolute Kscmh values.\n"
                    "Normalised: scale each site to 0-1 to compare seasonal patterns.\n"
                    "Small multiples: one panel per site with its own axis."
                ),
            )
        bm_fc_df = build_bm_comparison_df(FREQ_MAP[bm_fc_agg], start_date, end_date, remove_outliers)
        bm_fc_plot = bm_fc_df[[c for c in _BM_FLOW_COLS if c in bm_fc_df.columns]]
        bm_fc_plot, _ = thin_time_series(bm_fc_plot)
        if bm_fc_plot.empty:
            st.info("No flow data in the selected date range.")
        else:
            fig_bm_fc = render_comparison_chart(
                bm_fc_plot,
                f"Biomethane Flow Comparison — {bm_fc_agg.lower()} averages",
                "Time",
                bm_fc_view,
            )
            st.plotly_chart(fig_bm_fc, width="stretch")

    # ------------------------------------------------------------------
    elif bm_section == "Pressure comparison":
        st.markdown("## Pressure comparison")
        st.caption(
            "Outlet pressure from all three sites on one chart. "
            "All values in Bar."
        )
        bm_pc_ctrl1, bm_pc_ctrl2 = st.columns(2)
        with bm_pc_ctrl1:
            bm_pc_agg = st.selectbox(
                "Data granularity",
                options=list(FREQ_MAP.keys()),
                index=list(FREQ_MAP.keys()).index("Daily"),
                key="bm_pc_agg",
            )
        with bm_pc_ctrl2:
            bm_pc_view = st.selectbox(
                "Chart view",
                options=CHART_VIEW_OPTIONS,
                index=0,
                key="bm_pc_view",
                help=(
                    "All series on one axis: compare absolute Bar values.\n"
                    "Normalised: scale each site to 0-1 to compare patterns.\n"
                    "Small multiples: one panel per site with its own axis."
                ),
            )
        bm_pc_df = build_bm_comparison_df(FREQ_MAP[bm_pc_agg], start_date, end_date, remove_outliers)
        bm_pc_plot = bm_pc_df[[c for c in _BM_PRES_COLS if c in bm_pc_df.columns]]
        bm_pc_plot, _ = thin_time_series(bm_pc_plot)
        if bm_pc_plot.empty:
            st.info("No pressure data in the selected date range.")
        else:
            fig_bm_pc = render_comparison_chart(
                bm_pc_plot,
                f"Biomethane Pressure Comparison — {bm_pc_agg.lower()} averages",
                "Time",
                bm_pc_view,
            )
            fig_bm_pc.update_layout(yaxis_title="Outlet Pressure (Bar)")
            st.plotly_chart(fig_bm_pc, width="stretch")

    # ------------------------------------------------------------------
    elif bm_section == "Flow and pressure per site":
        st.markdown("## Flow and pressure per site")
        st.caption(
            "Flow on the left axis (solid line) and outlet pressure on the right axis "
            "(dotted line) shown together for each site. "
            "Use this to see how pressure and flow move together at each location."
        )
        bm_da_agg = st.selectbox(
            "Data granularity",
            options=list(FREQ_MAP.keys()),
            index=list(FREQ_MAP.keys()).index("Daily"),
            key="bm_da_agg",
        )
        for site in BM_SITES:
            fig = _bm_dual_chart(
                site,
                bm_dfs_raw[site],
                f"{site} — {bm_da_agg.lower()} averages",
                freq=FREQ_MAP[bm_da_agg],
                xaxis_title="Time",
            )
            if fig is None:
                st.info(f"No data for {site} in the selected date range.")
            else:
                st.plotly_chart(fig, width="stretch")

    # ------------------------------------------------------------------
    elif bm_section == "Average by calendar month":
        st.markdown("## Average by calendar month")
        st.caption(
            "Average flow and average pressure for each calendar month, "
            "calculated across all years in the selected date range. "
            "This shows the typical seasonal pattern for each site."
        )
        month_labels = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ]
        bm_cal_view = st.selectbox(
            "Chart view", options=CHART_VIEW_OPTIONS, index=0, key="bm_cal_view",
        )
        pat_df = build_bm_comparison_pattern_df("month", start_date, end_date, remove_outliers)
        pat_df.index = month_labels[: len(pat_df)]

        bm_cal_flow = pat_df[[c for c in _BM_FLOW_COLS if c in pat_df.columns]]
        bm_cal_pres = pat_df[[c for c in _BM_PRES_COLS if c in pat_df.columns]]

        if not bm_cal_flow.empty:
            fig_bm_cal_f = render_comparison_chart(
                bm_cal_flow,
                "Average Flow by Calendar Month",
                "Month",
                bm_cal_view,
                mode="lines+markers",
                marker_size=8,
            )
            st.plotly_chart(fig_bm_cal_f, width="stretch")
        if not bm_cal_pres.empty:
            fig_bm_cal_p = render_comparison_chart(
                bm_cal_pres,
                "Average Outlet Pressure by Calendar Month",
                "Month",
                bm_cal_view,
                mode="lines+markers",
                marker_size=8,
            )
            fig_bm_cal_p.update_layout(yaxis_title="Outlet Pressure (Bar)")
            st.plotly_chart(fig_bm_cal_p, width="stretch")

    # ------------------------------------------------------------------
    elif bm_section == "Average by hour of day":
        st.markdown("## Average by hour of day")
        st.caption(
            "Average flow and pressure for each hour of the day, "
            "across all days in the selected date range."
        )
        bm_hr_view = st.selectbox(
            "Chart view", options=CHART_VIEW_OPTIONS, index=0, key="bm_hr_view",
        )
        hr_pat_df = build_bm_comparison_pattern_df("hour", start_date, end_date, remove_outliers)
        bm_hr_flow = hr_pat_df[[c for c in _BM_FLOW_COLS if c in hr_pat_df.columns]]
        bm_hr_pres = hr_pat_df[[c for c in _BM_PRES_COLS if c in hr_pat_df.columns]]

        if not bm_hr_flow.empty:
            fig_bm_hr_f = render_comparison_chart(
                bm_hr_flow,
                "Average Flow by Hour of Day",
                "Hour of day (0-23)",
                bm_hr_view,
                mode="lines+markers",
                marker_size=7,
            )
            st.plotly_chart(fig_bm_hr_f, width="stretch")
        if not bm_hr_pres.empty:
            fig_bm_hr_p = render_comparison_chart(
                bm_hr_pres,
                "Average Outlet Pressure by Hour of Day",
                "Hour of day (0-23)",
                bm_hr_view,
                mode="lines+markers",
                marker_size=7,
            )
            fig_bm_hr_p.update_layout(yaxis_title="Outlet Pressure (Bar)")
            st.plotly_chart(fig_bm_hr_p, width="stretch")

    # ------------------------------------------------------------------
    elif bm_section == "Flow vs pressure scatter":
        st.markdown("## Flow vs pressure scatter")
        st.caption(
            "Each dot is one averaged reading. "
            "The shape of each site's cluster shows how pressure responds to changes in flow."
        )

        sc_ctrl1, sc_ctrl2 = st.columns(2)
        with sc_ctrl1:
            bm_sc_agg = st.selectbox(
                "Aggregate to",
                options=["Daily", "Hourly"],
                index=0,
                key="bm_sc_agg",
            )
        with sc_ctrl2:
            bm_sc_view = st.selectbox(
                "Chart view",
                options=[
                    "All sites on one chart",
                    "One chart per site (actual values)",
                    "One chart per site (normalised 0-1)",
                ],
                index=1,
                key="bm_sc_view",
                help=(
                    "All sites on one chart: compare absolute flow and pressure values directly. "
                    "Works best when the sites have similar pressure ranges.\n"
                    "One chart per site (actual values): each site is a separate full chart "
                    "with its own axes — no overlap, works well in full screen.\n"
                    "One chart per site (normalised): both axes scaled to 0-1 per site so "
                    "you can compare the shape of the relationship without the scale difference."
                ),
            )
        sc_freq = "D" if bm_sc_agg == "Daily" else "h"
        SC_MAX_POINTS = 10_000  # per site — keeps the browser responsive

        if bm_sc_agg == "Hourly":
            st.caption(
                "Hourly data is downsampled to at most 10,000 points per site to keep "
                "the chart responsive. Daily averages give a cleaner picture."
            )

        # Build one data dict per site
        sc_site_data = {}
        for site in BM_SITES:
            meta = BM_SITES[site]
            df_site = bm_dfs_raw[site]
            flow_col = next((c for c in meta["flow_cols"] if c in df_site.columns), None)
            pres_col = next((c for c in meta["pressure_cols"] if c in df_site.columns), None)
            if flow_col is None or pres_col is None or df_site.empty:
                continue
            sub = df_site[[flow_col, pres_col]].dropna().resample(sc_freq).mean().dropna()
            if sub.empty:
                continue
            # Thin to SC_MAX_POINTS using uniform stride so the point cloud
            # remains representative rather than just taking the first N rows.
            if len(sub) > SC_MAX_POINTS:
                step = math.ceil(len(sub) / SC_MAX_POINTS)
                sub = sub.iloc[::step]
            sc_site_data[site] = {
                "flow": sub[flow_col] * meta["flow_scale"],
                "pres": sub[pres_col],
                "colour": LOCATION_COLOURS.get(site, "#6366f1"),
            }

        if not sc_site_data:
            st.info("No data available for the selected date range.")

        elif bm_sc_view == "All sites on one chart":
            fig_bm_sc = go.Figure()
            for site, sd in sc_site_data.items():
                fig_bm_sc.add_trace(
                    go.Scatter(
                        x=sd["flow"], y=sd["pres"],
                        mode="markers", name=site,
                        marker=dict(size=5, color=sd["colour"], opacity=0.65),
                        hovertemplate=(
                            f"<b>{site}</b><br>"
                            f"Flow: %{{x:,.3f}} Kscmh<br>"
                            f"Pressure: %{{y:,.3f}} Bar<extra></extra>"
                        ),
                    )
                )
            fig_bm_sc.update_layout(xaxis_title="Flow (Kscmh)", yaxis_title="Outlet Pressure (Bar)")
            fig_bm_sc = apply_dark_layout(
                fig_bm_sc, f"Flow vs Outlet Pressure — all sites ({bm_sc_agg.lower()})"
            )
            st.plotly_chart(fig_bm_sc, width="stretch")

        elif bm_sc_view == "One chart per site (actual values)":
            for site, sd in sc_site_data.items():
                fig_s = go.Figure()
                fig_s.add_trace(
                    go.Scatter(
                        x=sd["flow"], y=sd["pres"],
                        mode="markers", name=site,
                        marker=dict(size=5, color=sd["colour"], opacity=0.65),
                        showlegend=False,
                        hovertemplate=(
                            f"<b>{site}</b><br>"
                            f"Flow: %{{x:,.3f}} Kscmh<br>"
                            f"Pressure: %{{y:,.3f}} Bar<extra></extra>"
                        ),
                    )
                )
                fig_s.update_layout(xaxis_title="Flow (Kscmh)", yaxis_title="Outlet Pressure (Bar)")
                fig_s = apply_dark_layout(
                    fig_s, f"{site} — Flow vs Outlet Pressure ({bm_sc_agg.lower()})"
                )
                st.plotly_chart(fig_s, width="stretch")

        else:  # One chart per site (normalised 0-1)
            st.caption(
                "Both axes are scaled to 0-1 per site so the shape of the relationship "
                "can be compared without the scale difference getting in the way."
            )
            for site, sd in sc_site_data.items():
                f_min, f_max = sd["flow"].min(), sd["flow"].max()
                p_min, p_max = sd["pres"].min(), sd["pres"].max()
                f_norm = (sd["flow"] - f_min) / max(f_max - f_min, 1e-9)
                p_norm = (sd["pres"] - p_min) / max(p_max - p_min, 1e-9)
                fig_s = go.Figure()
                fig_s.add_trace(
                    go.Scatter(
                        x=f_norm, y=p_norm,
                        mode="markers", name=site,
                        marker=dict(size=5, color=sd["colour"], opacity=0.65),
                        showlegend=False,
                        hovertemplate=(
                            f"<b>{site}</b><br>"
                            f"Flow (norm): %{{x:.3f}}<br>"
                            f"Pressure (norm): %{{y:.3f}}<extra></extra>"
                        ),
                    )
                )
                fig_s.update_layout(
                    xaxis_title="Flow (0 = min, 1 = max)",
                    yaxis_title="Pressure (0 = min, 1 = max)",
                )
                fig_s = apply_dark_layout(
                    fig_s, f"{site} — Flow vs Outlet Pressure, normalised ({bm_sc_agg.lower()})"
                )
                st.plotly_chart(fig_s, width="stretch")

    # ------------------------------------------------------------------
    elif bm_section == "Seasonal trend by year":
        st.markdown("## Seasonal trend by year")
        st.caption(
            "Mean daily value per season per year for one site. "
            "Winter groups December with the following January and February. "
            "Larger markers mean more days of data contributed to that season average."
        )
        bm_seas_site = st.selectbox(
            "Site", options=list(BM_SITES.keys()), key="bm_seas_site"
        )
        meta = BM_SITES[bm_seas_site]
        df_site = bm_dfs_raw[bm_seas_site]
        colour = LOCATION_COLOURS.get(bm_seas_site, "#6366f1")
        all_cols = meta["flow_cols"] + meta["pressure_cols"]
        for col in [c for c in all_cols if c in df_site.columns]:
            series = df_site[col].dropna()
            if col in meta["flow_cols"]:
                series = series * meta["flow_scale"]
                y_label = meta["flow_label"]
            else:
                y_label = meta["pressure_label"]
            display_name = SERIES_DISPLAY_NAMES.get(col, col)
            fig_seas, seas_summary = build_seasonal_trend_chart(
                series,
                col,
                f"{bm_seas_site} — {display_name} — Seasonal Trend",
                colour,
                flow_unit="Kscmh",
                loc_flow_unit=None,
            )
            if fig_seas is None:
                st.info(f"No seasonal data for {display_name}.")
            else:
                fig_seas.update_yaxes(title_text=y_label)
                partial = int((seas_summary["CoveragePct"] < 99.9).sum())
                if partial:
                    st.caption(f"{partial} season-year point(s) have partial coverage.")
                st.plotly_chart(fig_seas, width="stretch")

    # ------------------------------------------------------------------
    elif bm_section == "Distribution by year":
        st.markdown("## Distribution of values by year")
        st.caption(
            "Box plots showing the spread of daily averages for each year. "
            "The box covers the middle 50% of values; the line inside is the median."
        )
        bm_box_site = st.selectbox(
            "Site", options=list(BM_SITES.keys()), key="bm_box_site"
        )
        meta = BM_SITES[bm_box_site]
        df_site = bm_dfs_raw[bm_box_site]
        colour = LOCATION_COLOURS.get(bm_box_site, "#6366f1")
        available_cols = [c for c in meta["flow_cols"] + meta["pressure_cols"] if c in df_site.columns]
        if not available_cols or df_site.empty:
            st.info(f"No data for {bm_box_site} in the selected date range.")
        else:
            bm_box_col = st.selectbox(
                "Series",
                options=available_cols,
                format_func=lambda c: SERIES_DISPLAY_NAMES.get(c, c),
                key="bm_box_col",
            )
            display_df_box = df_site.copy()
            if bm_box_col in meta["flow_cols"]:
                display_df_box[bm_box_col] = display_df_box[bm_box_col] * meta["flow_scale"]
            fig_box = build_yearly_box_plot(
                display_df_box,
                bm_box_col,
                f"{bm_box_site} — {SERIES_DISPLAY_NAMES.get(bm_box_col, bm_box_col)} — Distribution by Year",
                BM_COLOUR_MAPS[bm_box_site].get(bm_box_col, colour),
                flow_unit="Kscmh",
            )
            if fig_box is None:
                st.info("No data available for that series in the selected date range.")
            else:
                st.caption("Built from precomputed yearly box statistics.")
                st.plotly_chart(fig_box, width="stretch")

    # ------------------------------------------------------------------
    elif bm_section == "Correlation between sites":
        st.markdown("## Correlation between sites")
        st.caption(
            "Pearson correlation between daily averages across all three sites. "
            "A value of 1 means two series always move together. "
            "A value of 0 means no relationship. A value of -1 means they move in opposite directions."
        )
        bm_corr_df = build_bm_comparison_df("D", start_date, end_date, remove_outliers).corr()
        fig_bm_corr = build_correlation_heatmap(
            bm_corr_df, "Correlation between biomethane sites — daily averages"
        )
        st.plotly_chart(fig_bm_corr, width="stretch")

    # ------------------------------------------------------------------
    elif bm_section == "Raw data":
        st.markdown("## Raw data")
        for site in BM_SITES:
            colour = LOCATION_COLOURS.get(site, "#6366f1")
            st.markdown(
                f"<h4 style='color:{colour};'>{site}</h4>", unsafe_allow_html=True
            )
            with st.expander(f"Show {site} raw data (first and last 100 rows)", expanded=False):
                show_head_tail_dataframe(bm_dfs_raw[site])
