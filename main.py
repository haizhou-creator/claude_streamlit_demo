import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NBA All Seasons Dashboard",
    page_icon="🏀",
    layout="wide",
)

# ── Palette ───────────────────────────────────────────────────────────────────
PRIMARY   = "#1D428A"   # NBA blue
ACCENT    = "#C8102E"   # NBA red
NEUTRAL   = "#F5F7FA"
TEXT_DARK = "#1A1A2E"

st.markdown(f"""
<style>
  [data-testid="stAppViewContainer"] {{ background-color: {NEUTRAL}; }}
  [data-testid="stSidebar"]          {{ background-color: #FFFFFF; border-right: 1px solid #E0E4EA; }}
  h1, h2, h3 {{ color: {TEXT_DARK}; }}
  .metric-card {{
    background: #FFFFFF;
    border-left: 4px solid {PRIMARY};
    border-radius: 6px;
    padding: 14px 18px;
    box-shadow: 0 1px 4px rgba(0,0,0,.07);
  }}
  .metric-card .label {{ font-size: 12px; color: #6B7280; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }}
  .metric-card .value {{ font-size: 28px; font-weight: 700; color: {PRIMARY}; margin-top: 2px; }}
</style>
""", unsafe_allow_html=True)


# ── Data ──────────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("data/nba_all_seasons.csv", index_col=0)
    df.columns = df.columns.str.strip()
    df["draft_year"]   = pd.to_numeric(df["draft_year"],   errors="coerce")
    df["draft_round"]  = pd.to_numeric(df["draft_round"],  errors="coerce")
    df["draft_number"] = pd.to_numeric(df["draft_number"], errors="coerce")
    df["season_start"] = df["season"].str[:4].astype(int)
    return df

df = load_data()

STAT_LABELS = {
    "pts":        "Points per Game",
    "reb":        "Rebounds per Game",
    "ast":        "Assists per Game",
    "net_rating": "Net Rating",
    "usg_pct":    "Usage %",
    "ts_pct":     "True Shooting %",
    "ast_pct":    "Assist %",
    "gp":         "Games Played",
}

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.image(
    "https://upload.wikimedia.org/wikipedia/en/thumb/0/03/National_Basketball_Association_logo.svg/200px-National_Basketball_Association_logo.svg.png",
    width=80,
)
st.sidebar.title("Filters")

player_search = st.sidebar.text_input("Search player", placeholder="e.g. LeBron James")

all_teams = sorted(df["team_abbreviation"].dropna().unique())
teams_sel = st.sidebar.multiselect("Team", all_teams, placeholder="All teams")

all_countries = sorted(df["country"].dropna().unique())
countries_sel = st.sidebar.multiselect("Country / Nationality", all_countries, placeholder="All countries")

seasons = sorted(df["season"].unique())
season_range = st.sidebar.select_slider(
    "Season range",
    options=seasons,
    value=(seasons[0], seasons[-1]),
)

stat_for_ranking = st.sidebar.selectbox(
    "Stat for Top Players chart",
    options=list(STAT_LABELS.keys()),
    format_func=lambda x: STAT_LABELS[x],
    index=0,
)

top_n = st.sidebar.slider("Top N players", 5, 30, 10)

# ── Apply filters ─────────────────────────────────────────────────────────────
filtered = df[
    df["season"].between(season_range[0], season_range[1])
].copy()

if player_search:
    filtered = filtered[filtered["player_name"].str.contains(player_search, case=False, na=False)]

if teams_sel:
    filtered = filtered[filtered["team_abbreviation"].isin(teams_sel)]

if countries_sel:
    filtered = filtered[filtered["country"].isin(countries_sel)]

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🏀 NBA All Seasons Dashboard")
st.caption(f"Showing **{len(filtered):,}** player-season records · {season_range[0]} – {season_range[1]}")

# ── KPI cards ─────────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)

def metric_card(col, label, value):
    col.markdown(
        f'<div class="metric-card"><div class="label">{label}</div>'
        f'<div class="value">{value}</div></div>',
        unsafe_allow_html=True,
    )

metric_card(k1, "Players",         f"{filtered['player_name'].nunique():,}")
metric_card(k2, "Avg PTS",         f"{filtered['pts'].mean():.1f}")
metric_card(k3, "Avg REB",         f"{filtered['reb'].mean():.1f}")
metric_card(k4, "Avg AST",         f"{filtered['ast'].mean():.1f}")
metric_card(k5, "Nationalities",   f"{filtered['country'].nunique()}")

st.markdown("<br>", unsafe_allow_html=True)

# ── Row 1: Top players  |  Stat trend ─────────────────────────────────────────
col_a, col_b = st.columns([1, 1])

with col_a:
    st.subheader(f"Top {top_n} Players — {STAT_LABELS[stat_for_ranking]}")
    top_players = (
        filtered.groupby("player_name")[stat_for_ranking]
        .mean()
        .nlargest(top_n)
        .reset_index()
        .sort_values(stat_for_ranking)
    )
    fig_top = px.bar(
        top_players,
        x=stat_for_ranking,
        y="player_name",
        orientation="h",
        color=stat_for_ranking,
        color_continuous_scale=[[0, "#AEC6E8"], [1, PRIMARY]],
        labels={"player_name": "", stat_for_ranking: STAT_LABELS[stat_for_ranking]},
        template="simple_white",
    )
    fig_top.update_layout(
        coloraxis_showscale=False,
        margin=dict(l=0, r=10, t=10, b=10),
        height=350,
    )
    st.plotly_chart(fig_top, use_container_width=True)

with col_b:
    st.subheader("League-Average Stats by Season")
    stat_trend_cols = ["pts", "reb", "ast"]
    trend = (
        filtered.groupby("season")[stat_trend_cols]
        .mean()
        .reset_index()
    )
    fig_trend = go.Figure()
    colors_line = [PRIMARY, ACCENT, "#2E8B57"]
    for col_name, color in zip(stat_trend_cols, colors_line):
        fig_trend.add_trace(go.Scatter(
            x=trend["season"], y=trend[col_name],
            mode="lines+markers",
            name=STAT_LABELS[col_name],
            line=dict(color=color, width=2),
            marker=dict(size=5),
        ))
    fig_trend.update_layout(
        xaxis=dict(tickangle=-45, tickfont=dict(size=10)),
        legend=dict(orientation="h", y=1.1),
        margin=dict(l=0, r=10, t=30, b=10),
        height=350,
        template="simple_white",
    )
    st.plotly_chart(fig_trend, use_container_width=True)

# ── Row 2: Country breakdown  |  Height vs Weight scatter ─────────────────────
col_c, col_d = st.columns([1, 1])

with col_c:
    st.subheader("Players by Country (Top 15)")
    country_counts = (
        filtered.groupby("country")["player_name"]
        .nunique()
        .nlargest(15)
        .reset_index()
        .rename(columns={"player_name": "players"})
        .sort_values("players")
    )
    fig_country = px.bar(
        country_counts,
        x="players",
        y="country",
        orientation="h",
        color="players",
        color_continuous_scale=[[0, "#AEC6E8"], [1, PRIMARY]],
        labels={"country": "", "players": "Unique Players"},
        template="simple_white",
    )
    fig_country.update_layout(
        coloraxis_showscale=False,
        margin=dict(l=0, r=10, t=10, b=10),
        height=380,
    )
    st.plotly_chart(fig_country, use_container_width=True)

with col_d:
    st.subheader("Height vs Weight")
    scatter_data = filtered.dropna(subset=["player_height", "player_weight", "pts"])
    fig_scatter = px.scatter(
        scatter_data,
        x="player_weight",
        y="player_height",
        color="pts",
        color_continuous_scale=[[0, "#E8F0FE"], [0.5, "#4C72B0"], [1, ACCENT]],
        hover_data=["player_name", "team_abbreviation", "season"],
        labels={
            "player_weight": "Weight (kg)",
            "player_height": "Height (cm)",
            "pts":           "Avg PTS",
        },
        opacity=0.65,
        template="simple_white",
    )
    fig_scatter.update_traces(marker_size=5)
    fig_scatter.update_layout(
        coloraxis_colorbar=dict(title="Avg PTS", thickness=12),
        margin=dict(l=0, r=10, t=10, b=10),
        height=380,
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

# ── Row 3: Draft analysis  |  Stat distribution ───────────────────────────────
col_e, col_f = st.columns([1, 1])

with col_e:
    st.subheader("Draft Round vs Avg Points")
    draft_df = filtered.dropna(subset=["draft_round"])
    draft_df = draft_df[draft_df["draft_round"].isin([1, 2])]
    draft_df["draft_round"] = draft_df["draft_round"].astype(int).astype(str)
    fig_box = px.box(
        draft_df,
        x="draft_round",
        y="pts",
        color="draft_round",
        color_discrete_map={"1": PRIMARY, "2": ACCENT},
        labels={"draft_round": "Draft Round", "pts": "Points per Game"},
        template="simple_white",
        points=False,
    )
    fig_box.update_layout(
        showlegend=False,
        margin=dict(l=0, r=10, t=10, b=10),
        height=330,
    )
    st.plotly_chart(fig_box, use_container_width=True)

with col_f:
    st.subheader(f"Distribution — {STAT_LABELS[stat_for_ranking]}")
    hist_data = filtered[stat_for_ranking].dropna()
    fig_hist = px.histogram(
        x=hist_data,
        nbins=40,
        color_discrete_sequence=[PRIMARY],
        labels={"x": STAT_LABELS[stat_for_ranking], "count": "Players"},
        template="simple_white",
    )
    fig_hist.update_traces(marker_line_width=0.3, marker_line_color="white")
    fig_hist.update_layout(
        margin=dict(l=0, r=10, t=10, b=10),
        height=330,
    )
    st.plotly_chart(fig_hist, use_container_width=True)

# ── Player table ──────────────────────────────────────────────────────────────
st.subheader("Player Records")
display_cols = ["player_name", "team_abbreviation", "country", "season", "age",
                "gp", "pts", "reb", "ast", "net_rating", "ts_pct", "usg_pct"]
table = (
    filtered[display_cols]
    .rename(columns={
        "player_name":        "Player",
        "team_abbreviation":  "Team",
        "country":            "Country",
        "season":             "Season",
        "age":                "Age",
        "gp":                 "GP",
        "pts":                "PTS",
        "reb":                "REB",
        "ast":                "AST",
        "net_rating":         "Net Rtg",
        "ts_pct":             "TS%",
        "usg_pct":            "USG%",
    })
    .sort_values("PTS", ascending=False)
    .reset_index(drop=True)
)

st.dataframe(
    table.style.format({
        "Age":     "{:.0f}",
        "PTS":     "{:.1f}",
        "REB":     "{:.1f}",
        "AST":     "{:.1f}",
        "Net Rtg": "{:.1f}",
        "TS%":     "{:.3f}",
        "USG%":    "{:.3f}",
    }),
    use_container_width=True,
    height=400,
)

st.caption("Data: NBA All Seasons dataset · Dashboard built with Streamlit & Plotly")
