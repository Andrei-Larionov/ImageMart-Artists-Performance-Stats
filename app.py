import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# =========================================================
# Page config
# =========================================================
st.set_page_config(
    page_title="Artist Job Buckets Dashboard",
    layout="wide",
)


# =========================================================
# Minimal password wall (Streamlit Secrets)
# =========================================================
# In Streamlit Cloud -> App settings -> Secrets:
# APP_PASSWORD = "your_password_here"

if "authed" not in st.session_state:
    st.session_state.authed = False

if not st.session_state.authed:
    st.title("🔒 Access required")
    st.caption("Please enter the shared password to continue.")

    pw = st.text_input("Password", type="password")

    if st.button("Enter"):
        if pw == st.secrets["APP_PASSWORD"]:
            st.session_state.authed = True
            st.rerun()
        else:
            st.error("Incorrect password")

    st.stop()


# =========================================================
# App header
# =========================================================
st.title("Artist job time distributions (bucketed)")
st.caption("Pick a dataset and an artist to view the distribution. Labels show count + % share.")


# =========================================================
# Fixed bucket order (hardcoded)
# =========================================================
BUCKET_ORDER = [
    "00-10", "11-20", "21-30", "31-40", "41-50",
    "51-60", "61-70", "71-80", "81-90", "91-100", "z100+"
]

BUCKET_ORDER_DISPLAY = [b.replace("z100+", "100+") for b in BUCKET_ORDER]


# =========================================================
# Files (expected to be in repo root)
# =========================================================
COMPLETE_CSV = Path("time_to_complete.csv")
START_CSV = Path("time_to_start.csv")


# =========================================================
# Load data (cached)
# =========================================================
@st.cache_data(show_spinner=False)
def load_dataset(csv_path: str) -> pd.DataFrame:
    p = Path(csv_path)
    if not p.exists():
        raise FileNotFoundError(
            f"Missing file: {p}. Put it in the same folder as app.py (repo root)."
        )

    df = pd.read_csv(p)

    expected = {"artist", "bucket", "jobs_count"}
    if not expected.issubset(set(df.columns)):
        raise ValueError(
            f"{p} must have columns: artist, bucket, jobs_count. Found: {list(df.columns)}"
        )

    df = df.copy()
    df["jobs_count"] = pd.to_numeric(df["jobs_count"], errors="coerce").fillna(0).astype(int)

    # Enforce bucket ordering
    df["bucket"] = pd.Categorical(df["bucket"], categories=BUCKET_ORDER, ordered=True)

    return df


def ensure_all_buckets(artist_data: pd.DataFrame) -> pd.DataFrame:
    """Ensure every bucket exists for the artist (missing buckets become 0)."""
    full = pd.DataFrame({"bucket": BUCKET_ORDER})
    full["bucket"] = pd.Categorical(full["bucket"], categories=BUCKET_ORDER, ordered=True)

    out = (
        full.merge(artist_data[["bucket", "jobs_count"]], on="bucket", how="left")
        .fillna({"jobs_count": 0})
    )
    out["jobs_count"] = out["jobs_count"].astype(int)
    return out


def add_percent_share(df: pd.DataFrame) -> pd.DataFrame:
    """Add pct_share and label columns based on total jobs for selected artist."""
    out = df.copy()
    total = int(out["jobs_count"].sum())
    if total > 0:
        out["pct_share"] = out["jobs_count"] / total * 100.0
    else:
        out["pct_share"] = 0.0

    # Nice label for chart: "58 (12.3%)"
    out["label"] = out.apply(lambda r: f"{int(r['jobs_count'])} ({r['pct_share']:.1f}%)", axis=1)

    # Display-friendly bucket label (turn z100+ into 100+)
    out["bucket_label"] = out["bucket"].astype(str).replace({"z100+": "100+"})

    return out


def build_chart(plot_df: pd.DataFrame, artist: str, dataset_label: str):
    fig = px.bar(
        plot_df,
        x="bucket_label",
        y="jobs_count",
        text="label",
        title=f"{dataset_label} distribution — {artist}",
        category_orders={"bucket_label": BUCKET_ORDER_DISPLAY},
    )

    # Force categorical axis so Plotly doesn't treat labels like dates/times
    fig.update_xaxes(type="category")

    # Make tooltips show both count and share cleanly
    fig.update_traces(
        hovertemplate=(
            "<b>Bucket:</b> %{x}<br>"
            "<b>Jobs:</b> %{y}<br>"
            "<b>Share:</b> %{customdata[0]:.1f}%<extra></extra>"
        ),
        customdata=plot_df[["pct_share"]].to_numpy(),
        textposition="outside",
        cliponaxis=False,
    )

    fig.update_layout(
        xaxis_title="Hours (bucket)",
        yaxis_title="Jobs count",
        height=520,
        bargap=0.25,
        margin=dict(l=40, r=40, t=60, b=40),
    )

    return fig


# =========================================================
# Load both datasets
# =========================================================
try:
    df_complete = load_dataset(str(COMPLETE_CSV))
    df_start = load_dataset(str(START_CSV))
except Exception as e:
    st.error(str(e))
    st.stop()

DATASETS = {
    "Time to complete": df_complete,
    "Time to start": df_start,
}


# =========================================================
# Controls (dataset switch + artist select)
# =========================================================
all_artists = sorted(
    set(df_complete["artist"].unique().tolist()) | set(df_start["artist"].unique().tolist())
)

left, right = st.columns([2, 3])

with left:
    selected_dataset_name = st.radio(
        "Dataset",
        options=list(DATASETS.keys()),
        horizontal=True,
    )

with right:
    selected_artist = st.selectbox("Artist", all_artists)

current_df = DATASETS[selected_dataset_name]


# =========================================================
# Filter & normalize for selected artist
# =========================================================
artist_raw = current_df[current_df["artist"] == selected_artist].copy()

if artist_raw.empty:
    # Artist not present in this dataset: show zeros
    artist_df = pd.DataFrame({"bucket": BUCKET_ORDER, "jobs_count": [0] * len(BUCKET_ORDER)})
    artist_df["bucket"] = pd.Categorical(artist_df["bucket"], categories=BUCKET_ORDER, ordered=True)
else:
    artist_df = ensure_all_buckets(artist_raw)

artist_df = add_percent_share(artist_df)


# =========================================================
# Metrics
# =========================================================
total_jobs = int(artist_df["jobs_count"].sum())
over_100 = int(artist_df.loc[artist_df["bucket"] == "z100+", "jobs_count"].sum())

m1, m2, m3 = st.columns(3)
m1.metric("Total jobs (selected dataset)", f"{total_jobs}")
m2.metric("100+ hour jobs", f"{over_100}")
m3.metric("100+ share", f"{(over_100 / total_jobs * 100):.1f}%" if total_jobs else "—")


# =========================================================
# Always-on animation (fixed speed, no UI controls)
# =========================================================
placeholder = st.empty()
ANIMATION_SLEEP_SECONDS = 0.07

for i in range(1, len(artist_df) + 1):
    partial = artist_df.iloc[:i].copy()
    placeholder.plotly_chart(
        build_chart(partial, selected_artist, selected_dataset_name),
        use_container_width=True,
    )
    time.sleep(ANIMATION_SLEEP_SECONDS)


# =========================================================
# Data table (counts + % share)
# =========================================================
with st.expander("Show underlying data"):
    table_df = artist_df[["bucket_label", "jobs_count", "pct_share"]].copy()
    table_df = table_df.rename(
        columns={
            "bucket_label": "bucket",
            "jobs_count": "jobs_count",
            "pct_share": "pct_share_percent",
        }
    )
    table_df["pct_share_percent"] = table_df["pct_share_percent"].map(lambda x: round(float(x), 2))
    st.dataframe(table_df, use_container_width=True)
