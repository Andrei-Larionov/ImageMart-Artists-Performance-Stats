import io
import time

import pandas as pd
import plotly.express as px
import streamlit as st


# =========================================================
# Page config
# =========================================================
st.set_page_config(
    page_title="Artist Job Completion Dashboard",
    layout="wide"
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
st.title("Artist job completion distribution")
st.caption("Bucketed job completion times (hours)")


# =========================================================
# Fixed bucket order (hardcoded)
# =========================================================
BUCKET_ORDER = [
    "00-10", "11-20", "21-30", "31-40", "41-50",
    "51-60", "61-70", "71-80", "81-90", "91-100", "z100+"
]


# =========================================================
# Hardcoded TSV data
# =========================================================
RAW_TSV = """artist\tbucket\tjobs_count
Anastasia\t00-10\t41
Anastasia\t11-20\t143
Anastasia\t21-30\t27
Anastasia\t31-40\t18
Anastasia\t41-50\t8
Anastasia\t51-60\t1
Anastasia\t61-70\t2
Anastasia\t91-100\t1
Anastasia\tz100+\t3
Elena N.\t00-10\t67
Elena N.\t11-20\t153
Elena N.\t21-30\t255
Elena N.\t31-40\t33
Elena N.\t41-50\t38
Elena N.\t51-60\t15
Elena N.\t61-70\t54
Elena N.\t71-80\t61
Elena N.\t81-90\t11
Elena N.\t91-100\t21
Elena N.\tz100+\t71
Elena P.\t00-10\t329
Elena P.\t11-20\t557
Elena P.\t21-30\t105
Elena P.\t31-40\t126
Elena P.\t41-50\t172
Elena P.\t51-60\t38
Elena P.\t61-70\t156
Elena P.\t71-80\t20
Elena P.\t81-90\t58
Elena P.\t91-100\t35
Elena P.\tz100+\t51
Fedosey\t00-10\t70
Fedosey\t11-20\t14
Fedosey\t21-30\t70
Fedosey\t31-40\t56
Fedosey\t41-50\t40
Fedosey\t51-60\t60
Fedosey\t61-70\t11
Fedosey\t71-80\t73
Fedosey\t81-90\t30
Fedosey\t91-100\t50
Fedosey\tz100+\t237
Ksenia\t00-10\t117
Ksenia\t11-20\t43
Ksenia\t21-30\t72
Ksenia\t31-40\t20
Ksenia\t41-50\t30
Ksenia\t51-60\t14
Ksenia\t61-70\t10
Ksenia\t71-80\t12
Ksenia\t81-90\t1
Ksenia\t91-100\t14
Ksenia\tz100+\t33
Maksim\t00-10\t58
Maksim\t11-20\t44
Maksim\t21-30\t113
Maksim\t31-40\t46
Maksim\t41-50\t114
Maksim\t51-60\t49
Maksim\t61-70\t58
Maksim\t71-80\t48
Maksim\t81-90\t16
Maksim\t91-100\t33
Maksim\tz100+\t60
Oksana\t00-10\t765
Oksana\t11-20\t248
Oksana\t21-30\t66
Oksana\t31-40\t12
Oksana\t41-50\t11
Oksana\t51-60\t2
Oksana\t61-70\t6
Oksana\t71-80\t3
Oksana\t81-90\t2
Oksana\t91-100\t5
Oksana\tz100+\t21
Olga B\t00-10\t98
Olga B\t11-20\t43
Olga B\t21-30\t159
Olga B\t31-40\t41
Olga B\t41-50\t147
Olga B\t51-60\t80
Olga B\t61-70\t77
Olga B\t71-80\t93
Olga B\t81-90\t44
Olga B\t91-100\t77
Olga B\tz100+\t113
Yulia\t00-10\t97
Yulia\t11-20\t176
Yulia\t21-30\t61
Yulia\t31-40\t27
Yulia\t41-50\t15
Yulia\t51-60\t7
Yulia\t61-70\t9
Yulia\t81-90\t1
Yulia\tz100+\t9
"""


# =========================================================
# Load & normalize data
# =========================================================
df = pd.read_csv(io.StringIO(RAW_TSV), sep="\t")
df["jobs_count"] = df["jobs_count"].astype(int)

df["bucket"] = pd.Categorical(
    df["bucket"],
    categories=BUCKET_ORDER,
    ordered=True
)


# =========================================================
# Controls
# =========================================================
artists = sorted(df["artist"].unique())

c1, c2 = st.columns([2, 3])

with c1:
    selected_artist = st.selectbox("Artist", artists)

with c2:
    animate = st.checkbox("Animate bars", value=True)


# =========================================================
# Prepare artist data (ensure all buckets exist)
# =========================================================
artist_df = df[df["artist"] == selected_artist][["bucket", "jobs_count"]]

full = pd.DataFrame({"bucket": BUCKET_ORDER})
full["bucket"] = pd.Categorical(full["bucket"], BUCKET_ORDER, ordered=True)

artist_df = (
    full
    .merge(artist_df, on="bucket", how="left")
    .fillna({"jobs_count": 0})
)

artist_df["jobs_count"] = artist_df["jobs_count"].astype(int)


# =========================================================
# Metrics
# =========================================================
total_jobs = artist_df["jobs_count"].sum()
over_100 = artist_df.loc[artist_df["bucket"] == "z100+", "jobs_count"].sum()

m1, m2, m3 = st.columns(3)
m1.metric("Total completed jobs", total_jobs)
m2.metric("100+ hour jobs", over_100)
m3.metric("100+ share", f"{(over_100 / total_jobs * 100):.1f}%" if total_jobs else "—")


# =========================================================
# Chart function
# =========================================================
def build_chart(data):
    plot_df = data.copy()
    plot_df["bucket"] = plot_df["bucket"].astype(str).replace({"z100+": "100+"})

    fig = px.bar(
        plot_df,
        x="bucket",
        y="jobs_count",
        text="jobs_count",
        title=f"Completion time distribution — {selected_artist}"
    )

    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(
        xaxis_title="Hours to complete",
        yaxis_title="Jobs count",
        height=520,
        bargap=0.25
    )

    return fig


# =========================================================
# Render chart (animated or static)
# =========================================================
placeholder = st.empty()

if not animate:
    placeholder.plotly_chart(build_chart(artist_df), use_container_width=True)
else:
    for i in range(1, len(artist_df) + 1):
        partial = artist_df.iloc[:i]
        placeholder.plotly_chart(build_chart(partial), use_container_width=True)
        time.sleep(0.07)


# =========================================================
# Data table (optional)
# =========================================================
with st.expander("Show underlying data"):
    display_df = artist_df.copy()
    display_df["bucket"] = display_df["bucket"].astype(str).replace({"z100+": "100+"})
    st.dataframe(display_df, use_container_width=True)
