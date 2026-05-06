import streamlit as st
from google.cloud import bigquery
import pandas as pd
import pickle
import plotly.graph_objects as go
import plotly.express as px
import matplotlib.pyplot as plt
from matplotlib.patches import Arc

# ── page config ───────────────────────────────────────────
st.set_page_config(
    page_title="NBA Dashboard",
    page_icon="",
    layout="wide"
)

# ── global styles ─────────────────────────────────────────
st.markdown("""
    <style>
    .stApp { background-color: #0a0e1a; }
    section[data-testid="stSidebar"] {
        background-color: #0d1220 !important;
        border-right: 1px solid #1a2035 !important;
        width: 60px !important;
        min-width: 60px !important;
        max-width: 60px !important;
    }
    section[data-testid="stSidebar"] > div:first-child {
        width: 60px !important;
        min-width: 60px !important;
        overflow: hidden !important;
        padding: 12px 4px !important;
    }
    div[data-testid="stSidebarContent"] {
        width: 60px !important;
        padding: 8px 4px !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        gap: 4px !important;
    }
    div[data-testid="stSidebarContent"] .stButton button {
        width: 44px !important;
        height: 44px !important;
        padding: 0 !important;
        font-size: 20px !important;
        border-radius: 10px !important;
    }
    button[data-testid="collapsedControl"] { display: none; }
    .stApp, .stMarkdown, p, li { color: #9ca3af; }
    h1, h2, h3 { color: #f9fafb !important; font-weight: 500 !important; }
    [data-testid="stMetric"] {
        background: #111827;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 12px 16px;
    }
    [data-testid="stMetricLabel"] { color: #6b7280 !important; font-size: 11px !important; text-transform: uppercase; letter-spacing: 0.05em; }
    [data-testid="stMetricValue"] { color: #f9fafb !important; font-size: 22px !important; }
    [data-testid="stMetricDelta"] { font-size: 11px !important; }
    hr { border-color: #1a2035 !important; }
    [data-testid="stSelectbox"] > div > div {
        background: #111827 !important;
        border: 1px solid #1f2937 !important;
        color: #f9fafb !important;
    }
    .stButton button {
        background: #111827 !important;
        border: 1px solid #1f2937 !important;
        color: #9ca3af !important;
        border-radius: 6px !important;
        font-size: 12px !important;
    }
    .stButton button:hover {
        border-color: #6b8cff !important;
        color: #6b8cff !important;
    }
    button[kind="primary"] {
        background: #1a2a6c !important;
        border-color: #6b8cff !important;
        color: #6b8cff !important;
    }
    .stTabs [data-baseweb="tab-list"] { background: #111827; border-radius: 8px; padding: 4px; gap: 2px; }
    .stTabs [data-baseweb="tab"] { background: transparent; color: #6b7280; border-radius: 6px; font-size: 12px; }
    .stTabs [aria-selected="true"] { background: #1a2a6c !important; color: #6b8cff !important; }
    .stTabs [data-baseweb="tab-border"] { display: none; }
    input, textarea { background: #111827 !important; color: #f9fafb !important; border-color: #1f2937 !important; }
    .stApp [data-testid="stCaptionContainer"] p { color: #6b7280 !important; }
    .stApp h2 { margin-top: 1.5rem !important; margin-bottom: 0.5rem !important; }
    [data-testid="stMultiSelect"] > div > div {
        background: #111827 !important;
        border: 1px solid #1f2937 !important;
        color: #f9fafb !important;
    }
    /* html table styles */
    .nba-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
        color: #f9fafb;
        margin-bottom: 8px;
    }
    .nba-table th {
        background: #1f2937;
        color: #9ca3af;
        padding: 8px 12px;
        text-align: left;
        font-weight: 500;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-bottom: 1px solid #374151;
    }
    .nba-table td {
        padding: 8px 12px;
        border-bottom: 1px solid #1f2937;
        color: #f9fafb;
    }
    .nba-table tr:hover td { background: #1a2035; }
    .nba-table .accent { color: #6b8cff; }
    .nba-table .muted { color: #6b7280; }
    .nba-table .positive { color: #34d399; }
    .nba-table .negative { color: #f87171; }
    </style>
""", unsafe_allow_html=True)

# ── nba teams ─────────────────────────────────────────────
NBA_TEAMS = [
    "ATL", "BOS", "BKN", "CHA", "CHI", "CLE", "DAL", "DEN",
    "DET", "GSW", "HOU", "IND", "LAC", "LAL", "MEM", "MIA",
    "MIL", "MIN", "NOP", "NYK", "OKC", "ORL", "PHI", "PHX",
    "POR", "SAC", "SAS", "TOR", "UTA", "WAS"
]

# ── bigquery ──────────────────────────────────────────────
def get_bq_client():
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
    return bigquery.Client(project="nba-dashboard-495409", credentials=creds)

# ── html table renderer ───────────────────────────────────
def render_table(df, index=False):
    if index:
        df = df.copy()
        df.insert(0, '#', range(1, len(df) + 1))
    headers = ''.join([f'<th>{col}</th>' for col in df.columns])
    rows = ''
    for _, row in df.iterrows():
        cells = ''
        for val in row:
            if isinstance(val, float):
                if 0 < abs(val) < 1:
                    formatted = f"{val:.1%}"
                else:
                    formatted = f"{val:.1f}" if val != int(val) else str(int(val))
            else:
                formatted = str(val) if pd.notna(val) else '—'
            cells += f'<td>{formatted}</td>'
        rows += f'<tr>{cells}</tr>'
    html = f'<table class="nba-table"><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table>'
    st.markdown(html, unsafe_allow_html=True)

# ── data loaders ──────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_player_averages():
    bq = get_bq_client()
    df = bq.query("SELECT * FROM `nba-dashboard-495409.nba_stats.player_averages`").to_dataframe()
    df = df[df['team'].isin(NBA_TEAMS)]
    df = df.sort_values('games_played', ascending=False)\
           .drop_duplicates(subset='player_name', keep='first')\
           .reset_index(drop=True)
    df['pts_exact'] = df['pts']
    df['reb_exact'] = df['reb']
    df['ast_exact'] = df['ast']
    df['stl_exact'] = df['stl']
    df['blk_exact'] = df['blk']
    return df

@st.cache_data(ttl=3600)
def load_player_advanced():
    bq = get_bq_client()
    df = bq.query("SELECT * FROM `nba-dashboard-495409.nba_stats.player_advanced_stats`").to_dataframe()
    return df[df['team'].isin(NBA_TEAMS)]\
        .sort_values('games_played', ascending=False)\
        .drop_duplicates(subset='player_name', keep='first')\
        .reset_index(drop=True)

@st.cache_data(ttl=3600)
def load_player_consistency():
    bq = get_bq_client()
    df = bq.query("SELECT * FROM `nba-dashboard-495409.nba_stats.player_consistency`").to_dataframe()
    return df[df['team'].isin(NBA_TEAMS)]\
        .sort_values('games_played', ascending=False)\
        .drop_duplicates(subset='player_name', keep='first')\
        .reset_index(drop=True)

@st.cache_data(ttl=3600)
def load_player_season_highs():
    bq = get_bq_client()
    df = bq.query("SELECT * FROM `nba-dashboard-495409.nba_stats.player_season_highs`").to_dataframe()
    return df[df['team'].isin(NBA_TEAMS)]\
        .sort_values('season_high_pts', ascending=False)\
        .drop_duplicates(subset='player_name', keep='first')\
        .reset_index(drop=True)

@st.cache_data(ttl=3600)
def load_player_vs_opponent():
    bq = get_bq_client()
    df = bq.query("SELECT * FROM `nba-dashboard-495409.nba_stats.player_vs_opponent`").to_dataframe()
    return df[df['opponent'].isin(NBA_TEAMS)]

@st.cache_data(ttl=3600)
def load_player_rolling():
    bq = get_bq_client()
    df = bq.query("SELECT * FROM `nba-dashboard-495409.nba_stats.player_rolling_averages`").to_dataframe()
    return df[df['team'].isin(NBA_TEAMS)]

@st.cache_data(ttl=3600)
def load_team_records():
    bq = get_bq_client()
    df = bq.query("SELECT * FROM `nba-dashboard-495409.nba_stats.team_records`").to_dataframe()
    return df[df['team'].isin(NBA_TEAMS)]

@st.cache_data(ttl=3600)
def load_team_monthly():
    bq = get_bq_client()
    df = bq.query("SELECT * FROM `nba-dashboard-495409.nba_stats.team_monthly_stats`").to_dataframe()
    return df[df['team'].isin(NBA_TEAMS)]

@st.cache_data(ttl=3600)
def load_team_vs_team():
    bq = get_bq_client()
    df = bq.query("SELECT * FROM `nba-dashboard-495409.nba_stats.team_vs_team`").to_dataframe()
    return df[df['team'].isin(NBA_TEAMS) & df['opponent'].isin(NBA_TEAMS)]

@st.cache_data(ttl=3600)
def load_team_advanced():
    bq = get_bq_client()
    df = bq.query("SELECT * FROM `nba-dashboard-495409.nba_stats.team_advanced_stats`").to_dataframe()
    return df[df['team'].isin(NBA_TEAMS)]

@st.cache_data(ttl=3600)
def load_team_advanced_season():
    bq = get_bq_client()
    return bq.query("SELECT * FROM `nba-dashboard-495409.nba_stats.team_advanced_season`").to_dataframe()

@st.cache_data(ttl=3600)
def load_team_shot_zones():
    bq = get_bq_client()
    df = bq.query("SELECT * FROM `nba-dashboard-495409.nba_stats.team_shot_zones`").to_dataframe()
    return df[df['team'].isin(NBA_TEAMS)]

@st.cache_data(ttl=3600)
def load_team_game_results():
    bq = get_bq_client()
    df = bq.query("SELECT * FROM `nba-dashboard-495409.nba_stats.team_game_results`").to_dataframe()
    return df[df['team'].isin(NBA_TEAMS) & df['opponent'].isin(NBA_TEAMS)]

@st.cache_data(ttl=3600)
def load_standings():
    bq = get_bq_client()
    return bq.query("""
        SELECT * FROM `nba-dashboard-495409.nba_stats.league_standings`
        ORDER BY conference, playoffrank
    """).to_dataframe()

@st.cache_data(ttl=3600)
def load_player_gamelogs(player_id_val):
    bq = get_bq_client()
    return bq.query(f"""
        SELECT
            r.GAME_DATE,
            r.game_id,
            r.team,
            t.opponent,
            r.min,
            r.fgm, r.fga, r.fg_pct,
            r.fg3m, r.fg3a, r.fg3_pct,
            r.ftm, r.fta, r.ft_pct,
            r.pts, r.reb, r.ast,
            r.stl, r.blk, r.tov
        FROM `nba-dashboard-495409.nba_stats.raw_box_scores` r
        LEFT JOIN `nba-dashboard-495409.nba_stats.team_game_results` t
            ON r.game_id = t.game_id
            AND r.team = t.team
        WHERE r.player_id = {int(player_id_val)}
        ORDER BY r.GAME_DATE DESC
    """).to_dataframe()

# ── helpers ───────────────────────────────────────────────
def dark_layout(fig, height=400, title=None):
    fig.update_layout(
        plot_bgcolor='#111827',
        paper_bgcolor='#111827',
        font_color='#9ca3af',
        font_size=11,
        height=height,
        title=title,
        title_font_color='#f9fafb',
        margin=dict(l=16, r=16, t=40 if title else 16, b=16),
        xaxis=dict(gridcolor='#1f2937', color='#6b7280'),
        yaxis=dict(gridcolor='#1f2937', color='#6b7280'),
        legend=dict(bgcolor='#111827', bordercolor='#1f2937', font_color='#9ca3af')
    )
    return fig

def draw_court(ax, color='#374151', lw=1.5):
    for element in [
        plt.Circle((0, 0), radius=7.5, linewidth=lw, color=color, fill=False),
        plt.Rectangle((-30, -7.5), 60, -1, linewidth=lw, color=color),
        plt.Rectangle((-80, -47.5), 160, 190, linewidth=lw, color=color, fill=False),
        plt.Rectangle((-60, -47.5), 120, 190, linewidth=lw, color=color, fill=False),
        Arc((0, 142.5), 120, 120, theta1=0, theta2=180, linewidth=lw, color=color, fill=False),
        Arc((0, 142.5), 120, 120, theta1=180, theta2=0, linewidth=lw, color=color, linestyle='dashed'),
        Arc((0, 0), 80, 80, theta1=0, theta2=180, linewidth=lw, color=color),
        plt.Rectangle((-220, -47.5), 0, 140, linewidth=lw, color=color),
        plt.Rectangle((220, -47.5), 0, 140, linewidth=lw, color=color),
        Arc((0, 0), 475, 475, theta1=22, theta2=158, linewidth=lw, color=color),
        Arc((0, 422.5), 120, 120, theta1=180, theta2=0, linewidth=lw, color=color),
    ]:
        ax.add_patch(element)
    return ax

def plot_shot_chart(shots_df, title):
    fig, ax = plt.subplots(figsize=(5, 4.5))
    fig.patch.set_facecolor('#111827')
    ax.set_facecolor('#111827')
    made = shots_df[shots_df['shot_made'] == 1]
    missed = shots_df[shots_df['shot_made'] == 0]
    ax.scatter(missed['loc_x'], missed['loc_y'], c='#f87171', alpha=0.4, s=8,
               label=f'Missed ({len(missed)})')
    ax.scatter(made['loc_x'], made['loc_y'], c='#6b8cff', alpha=0.6, s=8,
               label=f'Made ({len(made)})')
    draw_court(ax)
    ax.set_xlim(-250, 250)
    ax.set_ylim(-47.5, 422.5)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.legend(loc='upper right', facecolor='#111827', labelcolor='#9ca3af', fontsize=8)
    ax.set_title(title, color='#f9fafb', fontsize=11, pad=8)
    plt.tight_layout()
    return fig

# ── navigation ────────────────────────────────────────────
PAGES = ["League Overview", "Team Analysis", "Player Profile",
         "Team vs Team", "Player Comparison"]
ICONS = {
    "League Overview":   "◈",
    "Team Analysis":     "▦",
    "Player Profile":    "◉",
    "Team vs Team":      "⚔",
    "Player Comparison": "≋"
}

if 'page' not in st.session_state:
    st.session_state.page = "League Overview"

with st.sidebar:
    for p in PAGES:
        is_active = st.session_state.page == p
        if st.button(ICONS[p], key=f"nav_{p}", help=p,
                     type="primary" if is_active else "secondary"):
            st.session_state.page = p
            st.rerun()

page = st.session_state.page

# ── shared data ───────────────────────────────────────────
player_avg = load_player_averages()
team_records = load_team_records()

# ── league overview ───────────────────────────────────────
if page == "League Overview":
    st.title("League Overview")
    st.caption("2025–26 NBA Season")

    qualified = player_avg[
        (player_avg['player_name'].notna()) &
        (player_avg['games_played'] >= 58)
    ]

    # stat leader cards
    leaders = [
        ('pts_exact', 'Points',   'PPG'),
        ('reb_exact', 'Rebounds', 'RPG'),
        ('ast_exact', 'Assists',  'APG'),
        ('stl_exact', 'Steals',   'SPG'),
        ('blk_exact', 'Blocks',   'BPG'),
    ]

    cols = st.columns(5)
    for col, (stat, label, unit) in zip(cols, leaders):
        player = qualified.nlargest(1, stat).iloc[0]
        display_stat = stat.replace('_exact', '')
        with col:
            st.markdown(
                f"""
                <div style="
                    background: #111827;
                    border: 1px solid #1f2937;
                    border-top: 2px solid #6b8cff;
                    border-radius: 10px;
                    padding: 20px 12px;
                    text-align: center;
                ">
                    <img src="{player.get('headshot_url', '')}"
                         style="width:80px; height:80px; object-fit:cover;
                                border-radius:50%; border:2px solid #1f2937;
                                margin-bottom:12px;"
                         onerror="this.style.display='none'"/>
                    <div style="font-size:11px; color:#6b7280; text-transform:uppercase;
                                letter-spacing:0.1em; margin-bottom:6px;">{label} Leader</div>
                    <div style="font-size:36px; font-weight:500; color:#f9fafb;
                                line-height:1.0; margin-bottom:4px;">
                        {player[display_stat]}
                    </div>
                    <div style="font-size:12px; color:#6b7280; margin-bottom:8px;">{unit}</div>
                    <div style="font-size:15px; color:#6b8cff; font-weight:500;">
                        {player['player_name']}
                    </div>
                    <div style="font-size:11px; color:#4b5563; margin-top:4px;">
                        {player.get('team', '')} · {int(player['games_played'])} GP
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.divider()

    # standings
    standings = load_standings()
    if 'wins' not in standings.columns and 'record' in standings.columns:
        standings['wins'] = standings['record'].apply(
            lambda x: int(x.split('-')[0]) if isinstance(x, str) and '-' in x else None)
        standings['losses'] = standings['record'].apply(
            lambda x: int(x.split('-')[1]) if isinstance(x, str) and '-' in x else None)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Western Conference")
        west = standings[standings['conference'] == 'West']\
            .sort_values('playoffrank')[['playoffrank', 'teamname', 'record',
                                         'winpct', 'conferencegamesback',
                                         'l10', 'currentstreak']]\
            .rename(columns={'playoffrank': 'Seed', 'teamname': 'Team',
                             'record': 'W-L', 'winpct': 'WIN%',
                             'conferencegamesback': 'GB',
                             'l10': 'L10', 'currentstreak': 'Streak'})
        render_table(west)

    with col2:
        st.subheader("Eastern Conference")
        east = standings[standings['conference'] == 'East']\
            .sort_values('playoffrank')[['playoffrank', 'teamname', 'record',
                                         'winpct', 'conferencegamesback',
                                         'l10', 'currentstreak']]\
            .rename(columns={'playoffrank': 'Seed', 'teamname': 'Team',
                             'record': 'W-L', 'winpct': 'WIN%',
                             'conferencegamesback': 'GB',
                             'l10': 'L10', 'currentstreak': 'Streak'})
        render_table(east)

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top 5 Scorers")
        render_table(
            qualified.nlargest(5, 'pts_exact')[['player_name', 'team', 'pts']]
            .rename(columns={'player_name': 'Player', 'team': 'Team', 'pts': 'PPG'})
            .reset_index(drop=True),
            index=True
        )
    with col2:
        st.subheader("Top 5 Rebounders")
        render_table(
            qualified.nlargest(5, 'reb_exact')[['player_name', 'team', 'reb']]
            .rename(columns={'player_name': 'Player', 'team': 'Team', 'reb': 'RPG'})
            .reset_index(drop=True),
            index=True
        )

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top 5 Assist Leaders")
        render_table(
            qualified.nlargest(5, 'ast_exact')[['player_name', 'team', 'ast']]
            .rename(columns={'player_name': 'Player', 'team': 'Team', 'ast': 'APG'})
            .reset_index(drop=True),
            index=True
        )
    with col2:
        st.subheader("Top 5 Three Point Leaders")
        render_table(
            qualified.nlargest(5, 'fg3m')[['player_name', 'team', 'fg3m']]
            .rename(columns={'player_name': 'Player', 'team': 'Team', 'fg3m': '3PM'})
            .reset_index(drop=True),
            index=True
        )

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top 5 Steals Leaders")
        render_table(
            qualified.nlargest(5, 'stl_exact')[['player_name', 'team', 'stl']]
            .rename(columns={'player_name': 'Player', 'team': 'Team', 'stl': 'SPG'})
            .reset_index(drop=True),
            index=True
        )
    with col2:
        st.subheader("Top 5 Blocks Leaders")
        render_table(
            qualified.nlargest(5, 'blk_exact')[['player_name', 'team', 'blk']]
            .rename(columns={'player_name': 'Player', 'team': 'Team', 'blk': 'BPG'})
            .reset_index(drop=True),
            index=True
        )

elif page == "Team Analysis":
    st.title("Team Analysis")

    team_advanced = load_team_advanced()
    team_monthly = load_team_monthly()
    team_adv_season = load_team_advanced_season()

    team_options = sorted(
        team_records[team_records['team'].isin(NBA_TEAMS)]['team_name'].dropna().unique()
    )
    selected_team_name = st.selectbox("Select Team", team_options)
    team_row = team_records[team_records['team_name'] == selected_team_name]
    if team_row.empty:
        st.warning("Team not found.")
        st.stop()
    selected_team = team_row.iloc[0]['team']
    team_data = team_row.iloc[0]

    st.divider()

    # team header
    if pd.notna(team_data.get('logo_url')):
        st.markdown(
            f"""<div style="display:flex; align-items:center; gap:20px; margin-bottom:16px;">
                <img src="{team_data['logo_url']}" style="height:120px; width:auto;"/>
                <div>
                    <div style="font-size:28px; font-weight:500; color:#f9fafb;">
                        {team_data.get('team_name', selected_team)}</div>
                    <div style="font-size:14px; color:#6b7280; margin-top:4px;">
                        {team_data.get('conference', '')} Conference · {team_data.get('division', '')} Division
                    </div>
                </div>
            </div>""",
            unsafe_allow_html=True
        )

    # team metrics — 8 columns including FG%, 3P%, FT%
    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
    col1.metric("Record", f"{int(team_data['wins'])}-{int(team_data['losses'])}")
    col2.metric("Win %", f"{team_data['win_pct']:.1%}")
    col3.metric("PPG", team_data['avg_pts'])
    col4.metric("Opp PPG", team_data['avg_pts_allowed'])
    col5.metric("Point Diff", team_data['avg_point_diff'])
    col6.metric("FG%", f"{team_data['fg_pct']:.1%}")
    col7.metric("3P%", f"{team_data['fg3_pct']:.1%}")
    col8.metric("FT%", f"{team_data['ft_pct']:.1%}")

    st.divider()

    # monthly performance — full width
    st.subheader("Monthly Performance")
    monthly = team_monthly[team_monthly['team'] == selected_team]\
        .sort_values('month')
    if not monthly.empty:
        render_table(
            monthly[['month', 'games_played', 'wins', 'losses',
                      'avg_pts', 'avg_pts_allowed', 'avg_point_diff',
                      'fg_pct', 'fg3_pct']]
            .rename(columns={
                'month': 'Month', 'games_played': 'GP',
                'wins': 'W', 'losses': 'L',
                'avg_pts': 'PPG', 'avg_pts_allowed': 'Opp PPG',
                'avg_point_diff': 'Diff',
                'fg_pct': 'FG%', 'fg3_pct': '3P%'
            })
        )
    else:
        st.info("No monthly data available.")

    st.divider()

    # Advanced Stats
    st.subheader("Advanced Stats")

    adv = team_advanced[team_advanced['team'] == selected_team]
    if not adv.empty:
        a = adv.iloc[0]
        a1, a2, a3, a4, a5, a6 = st.columns(6)
        a1.metric("Pts in Paint", a['avg_pts_paint'])
        a2.metric("Fast Break Pts", a['avg_pts_fast_break'])
        a3.metric("Bench Points", a['avg_bench_points'])
        a4.metric("2nd Chance Pts", a['avg_pts_second_chance'])
        a5.metric("Pts off TOs", a['avg_pts_off_turnovers'])
        a6.metric("Lead Changes", a['avg_lead_changes'])

    adv_season = team_adv_season[team_adv_season['team_name'] == team_data['team_name']]
    if not adv_season.empty:
        s = adv_season.iloc[0]
        s1, s2, s3, s4, s5, s6 = st.columns(6)
        s1.metric("ORtg", s['off_rating'])
        s2.metric("DRtg", s['def_rating'])
        s3.metric("Net Rtg", s['net_rating'])
        s4.metric("Pace", s['pace'])
        s5.metric("PIE", f"{s['pie']:.1%}")
        s6.metric("eFG%", f"{s['efg_pct']:.1%}")

    st.markdown("</div>", unsafe_allow_html=True)

# ── player profile ────────────────────────────────────────
elif page == "Player Profile":
    st.title("Player Profile")

    player_advanced = load_player_advanced()
    player_consistency = load_player_consistency()
    player_highs = load_player_season_highs()
    player_vs_opp = load_player_vs_opponent()
    player_rolling = load_player_rolling()

    selected_player = st.selectbox(
        "Search Player",
        sorted(player_avg['player_name'].unique())
    )

    p = player_avg[player_avg['player_name'] == selected_player].iloc[0]
    player_id = p.get('player_id')  # define early so all sections can use it
    adv = player_advanced[player_advanced['player_name'] == selected_player]
    highs = player_highs[player_highs['player_name'] == selected_player]
    consistency = player_consistency[player_consistency['player_name'] == selected_player]

    if pd.notna(p.get('headshot_url')):
        st.markdown(
            f"""<div style="display:flex; align-items:center; gap:20px; margin-bottom:16px;">
                <img src="{p['headshot_url']}" style="height:100px; width:auto;"/>
                <div>
                    <div style="font-size:28px; font-weight:500; color:#f9fafb;">{p['player_name']}</div>
                    <div style="font-size:14px; color:#6b7280; margin-top:4px;">
                        {p.get('team_name', p['team'])} · {p.get('position', '')} · #{p.get('jersey', '')}
                    </div>
                    <div style="font-size:14px; color:#6b7280; margin-top:2px;">
                        {int(p['games_played'])} games played
                    </div>
                </div>
            </div>""",
            unsafe_allow_html=True
        )

    st.divider()

    st.subheader("Season Averages")
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("PTS", p['pts'])
    c2.metric("REB", p['reb'])
    c3.metric("AST", p['ast'])
    c4.metric("STL", p['stl'])
    c5.metric("BLK", p['blk'])
    c6.metric("TOV", p['tov'])
    c7.metric("MIN", p['min'])

    c1, c2, c3 = st.columns(3)
    c1.metric("FG%", f"{p['fg_pct']:.1%}")
    c2.metric("3P%", f"{p['fg3_pct']:.1%}")
    c3.metric("FT%", f"{p['ft_pct']:.1%}")

    st.divider()

    if not adv.empty:
        st.subheader("Advanced Stats")
        a = adv.iloc[0]
        c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
        c1.metric("TS%", f"{a['ts_pct']:.1%}")
        c2.metric("eFG%", f"{a['efg_pct']:.1%}")
        c3.metric("USG%", f"{a['usg_pct']:.1%}")
        c4.metric("BPM", a['bpm_approx'])
        c5.metric("VORP", a['vorp_approx'])
        c6.metric("WS", a['ws_approx'])
        c7.metric("ORtg", a['ortg'])

    st.divider()

    if not highs.empty:
        st.subheader("Season Highs")
        h = highs.iloc[0]
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("PTS", int(h['season_high_pts']))
        c2.metric("REB", int(h['season_high_reb']))
        c3.metric("AST", int(h['season_high_ast']))
        c4.metric("STL", int(h['season_high_stl']))
        c5.metric("BLK", int(h['season_high_blk']))

    st.divider()

    st.subheader("Game Log")

    gamelogs = load_player_gamelogs(int(player_id))

    if not gamelogs.empty:
        gamelogs['GAME_DATE'] = pd.to_datetime(gamelogs['GAME_DATE']).dt.strftime('%Y-%m-%d')

        # pagination
        rows_per_page = 10
        total_rows = len(gamelogs)
        total_pages = (total_rows - 1) // rows_per_page + 1

        if 'gamelog_page' not in st.session_state:
            st.session_state.gamelog_page = 0

        # reset page when player changes
        if st.session_state.get('gamelog_player') != selected_player:
            st.session_state.gamelog_page = 0
            st.session_state.gamelog_player = selected_player

        start = st.session_state.gamelog_page * rows_per_page
        end = start + rows_per_page
        page_df = gamelogs.iloc[start:end]

        render_table(
            page_df.rename(columns={
                'GAME_DATE': 'Date',
                'team': 'Team',
                'opponent': 'Opp',
                'min': 'MIN',
                'fgm': 'FGM', 'fga': 'FGA', 'fg_pct': 'FG%',
                'fg3m': '3PM', 'fg3a': '3PA', 'fg3_pct': '3P%',
                'ftm': 'FTM', 'fta': 'FTA', 'ft_pct': 'FT%',
                'pts': 'PTS', 'reb': 'REB', 'ast': 'AST',
                'stl': 'STL', 'blk': 'BLK', 'tov': 'TOV'
            }).drop(columns=['game_id'])
        )

        # pagination controls
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        col_prev, col_info, col_next = st.columns([1, 6, 1])
        with col_prev:
            if st.button("← Prev", key="gamelog_prev",
                         disabled=st.session_state.gamelog_page == 0,
                         use_container_width=True):
                st.session_state.gamelog_page -= 1
                st.rerun()
        with col_info:
            st.markdown(
                f"<div style='text-align:center; color:#6b7280; font-size:13px; padding-top:8px;'>"
                f"Page {st.session_state.gamelog_page + 1} of {total_pages} · {total_rows} games"
                f"</div>",
                unsafe_allow_html=True
            )
        with col_next:
            if st.button("Next →", key="gamelog_next",
                         disabled=st.session_state.gamelog_page >= total_pages - 1,
                         use_container_width=True):
                st.session_state.gamelog_page += 1
                st.rerun()
    else:
        st.info("No game log data available.")

    st.divider()

    if not consistency.empty:
        st.subheader("Consistency Metrics")
        con = consistency.iloc[0]
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("PTS Std Dev", con['std_pts'])
            st.metric("PTS Variance", con['var_pts'])
            st.metric("PTS CV", con['cv_pts'])
        with c2:
            st.metric("REB Std Dev", con['std_reb'])
            st.metric("REB Variance", con['var_reb'])
            st.metric("REB CV", con['cv_reb'])
        with c3:
            st.metric("AST Std Dev", con['std_ast'])
            st.metric("AST Variance", con['var_ast'])
            st.metric("AST CV", con['cv_ast'])

    st.divider()

    st.subheader("Performance Trend")
    rolling = player_rolling[player_rolling['player_name'] == selected_player]\
        .sort_values('GAME_DATE')
    if not rolling.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=rolling['GAME_DATE'], y=rolling['rolling_5_pts'],
                                  name='5-game avg', mode='lines',
                                  line=dict(color='#6b8cff')))
        fig.add_trace(go.Scatter(x=rolling['GAME_DATE'], y=rolling['rolling_10_pts'],
                                  name='10-game avg', mode='lines',
                                  line=dict(color='#a78bfa')))
        fig.add_trace(go.Scatter(x=rolling['GAME_DATE'], y=rolling['rolling_15_pts'],
                                  name='15-game avg', mode='lines',
                                  line=dict(color='#34d399')))
        fig.add_trace(go.Scatter(x=rolling['GAME_DATE'], y=rolling['pts'],
                                  name='Game pts', mode='markers',
                                  marker=dict(color='#6b7280', size=4), opacity=0.5))
        dark_layout(fig, height=350, title=f"{selected_player} Scoring Trend")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("Performance vs Each Opponent")
    player_id = p.get('player_id')
    if player_id is not None:
        vs_opp = player_vs_opp[player_vs_opp['player_id'] == player_id]
    else:
        vs_opp = player_vs_opp[player_vs_opp['player_name'] == selected_player]

    if not vs_opp.empty:
        render_table(
            vs_opp[['opponent', 'games_played', 'avg_pts', 'avg_reb',
                    'avg_ast', 'avg_fg_pct']]
            .sort_values('avg_pts', ascending=False)
            .rename(columns={
                'opponent': 'Opponent', 'games_played': 'GP',
                'avg_pts': 'PPG', 'avg_reb': 'RPG',
                'avg_ast': 'APG', 'avg_fg_pct': 'FG%'
            })
        )
    else:
        st.info("No opponent data available.")

    st.divider()
    st.subheader("Shot Chart")

    @st.cache_data(ttl=3600)
    def load_player_shots(player_id_val):
        bq = get_bq_client()
        return bq.query(f"""
            SELECT loc_x, loc_y, shot_made, shot_zone_basic, shot_type, game_date
            FROM `nba-dashboard-495409.nba_stats.shot_charts`
            WHERE player_id = {int(player_id_val)}
            ORDER BY game_date
        """).to_dataframe()

    player_shots = load_player_shots(int(player_id))

    if not player_shots.empty:
        player_shots['game_date'] = pd.to_datetime(player_shots['game_date'])

        all_months = ['Oct 2025', 'Nov 2025', 'Dec 2025', 'Jan 2026',
                      'Feb 2026', 'Mar 2026', 'Apr 2026']
        played_months = set(player_shots['game_date'].dt.strftime('%b %Y').unique().tolist())
        zones = sorted(player_shots['shot_zone_basic'].dropna().unique().tolist())

        zone_short = {
            'Above the Break 3': 'ATB3',
            'In The Paint (Non-RA)': 'Paint',
            'Restricted Area': 'RA',
            'Left Corner 3': 'LC3',
            'Right Corner 3': 'RC3',
            'Mid-Range': 'Mid',
            'Backcourt': 'Back'
        }

        for key, default in [('selected_months', []), ('full_season', True),
                              ('selected_zones', []), ('all_zones', True),
                              ('shot_view', 'All')]:
            if key not in st.session_state:
                st.session_state[key] = default

        # ── filter row ────────────────────────────────────
        col_f1, col_f2, col_f3 = st.columns([2, 2, 2])

        with col_f1:
            st.markdown(
                "<div style='font-size:12px; color:#6b7280; text-transform:uppercase; "
                "letter-spacing:0.08em; margin-bottom:6px;'>Month</div>",
                unsafe_allow_html=True
            )
            # available months only — gray out unplayed ones in label
            month_options_display = []
            for m in all_months:
                if m in played_months:
                    month_options_display.append(m)
                else:
                    month_options_display.append(f"{m} (no data)")

            selected_months_input = st.multiselect(
                "",
                options=all_months,
                default=st.session_state.selected_months if not st.session_state.full_season else [],
                placeholder="Full Season",
                key="month_multiselect",
                label_visibility="collapsed",
                format_func=lambda x: x if x in played_months else f"{x} — no data"
            )
            if not selected_months_input:
                st.session_state.full_season = True
                st.session_state.selected_months = []
            else:
                st.session_state.full_season = False
                st.session_state.selected_months = selected_months_input

        with col_f2:
            st.markdown(
                "<div style='font-size:12px; color:#6b7280; text-transform:uppercase; "
                "letter-spacing:0.08em; margin-bottom:6px;'>Zone</div>",
                unsafe_allow_html=True
            )
            selected_zones_input = st.multiselect(
                "",
                options=zones,
                default=st.session_state.selected_zones if not st.session_state.all_zones else [],
                placeholder="All Zones",
                key="zone_multiselect",
                label_visibility="collapsed"
            )
            if not selected_zones_input:
                st.session_state.all_zones = True
                st.session_state.selected_zones = []
            else:
                st.session_state.all_zones = False
                st.session_state.selected_zones = selected_zones_input

        with col_f3:
            st.markdown(
                "<div style='font-size:10px; color:#6b7280; text-transform:uppercase; "
                "letter-spacing:0.08em; margin-bottom:6px;'>Shot type</div>",
                unsafe_allow_html=True
            )
            # compact inline toggle for All / Made / Missed
            v1, v2, v3 = st.columns(3)
            with v1:
                if st.button("All",
                             key="view_all",
                             type="primary" if st.session_state.shot_view == 'All' else "secondary",
                             use_container_width=True):
                    st.session_state.shot_view = 'All'
                    st.rerun()
            with v2:
                if st.button("Made",
                             key="view_made",
                             type="primary" if st.session_state.shot_view == 'Made' else "secondary",
                             use_container_width=True):
                    st.session_state.shot_view = 'Made'
                    st.rerun()
            with v3:
                if st.button("Missed",
                             key="view_missed",
                             type="primary" if st.session_state.shot_view == 'Missed' else "secondary",
                             use_container_width=True):
                    st.session_state.shot_view = 'Missed'
                    st.rerun()

        # ── apply filters ─────────────────────────────────
        filtered_shots = player_shots.copy()
        if not st.session_state.full_season and st.session_state.selected_months:
            filtered_shots = filtered_shots[
                filtered_shots['game_date'].dt.strftime('%b %Y').isin(
                    st.session_state.selected_months)
            ]
        if not st.session_state.all_zones and st.session_state.selected_zones:
            filtered_shots = filtered_shots[
                filtered_shots['shot_zone_basic'].isin(st.session_state.selected_zones)
            ]
        if st.session_state.shot_view == 'Made':
            chart_df = filtered_shots[filtered_shots['shot_made'] == 1]
        elif st.session_state.shot_view == 'Missed':
            chart_df = filtered_shots[filtered_shots['shot_made'] == 0]
        else:
            chart_df = filtered_shots

        total = len(filtered_shots)
        made_count = int(filtered_shots['shot_made'].sum())
        pct = made_count / total * 100 if total > 0 else 0

        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

        # ── court + breakdown layout ──────────────────────
        col_court, col_right = st.columns([1, 1])

        with col_court:
            if not chart_df.empty:
                st.pyplot(
                    plot_shot_chart(
                        chart_df,
                        f"{selected_player} — {st.session_state.shot_view} ({len(chart_df):,})"
                    ),
                    use_container_width=True
                )
            else:
                st.info("No shots found for selected filters.")

        with col_right:
            # summary metrics
            st.markdown(
                f"""<div style="display:flex; gap:10px; margin-bottom:16px;">
                    <div style="flex:1; background:#111827; border:1px solid #1f2937;
                                border-radius:8px; padding:14px; text-align:center;">
                        <div style="font-size:11px; color:#6b7280; text-transform:uppercase;
                                    letter-spacing:0.07em; margin-bottom:6px;">Attempts</div>
                        <div style="font-size:26px; font-weight:500; color:#f9fafb;">{total}</div>
                    </div>
                    <div style="flex:1; background:#111827; border:1px solid #1f2937;
                                border-radius:8px; padding:14px; text-align:center;">
                        <div style="font-size:11px; color:#6b7280; text-transform:uppercase;
                                    letter-spacing:0.07em; margin-bottom:6px;">Makes</div>
                        <div style="font-size:26px; font-weight:500; color:#f9fafb;">{made_count}</div>
                    </div>
                    <div style="flex:1; background:#111827; border:1px solid #1f2937;
                                border-radius:8px; padding:14px; text-align:center;">
                        <div style="font-size:11px; color:#6b7280; text-transform:uppercase;
                                    letter-spacing:0.07em; margin-bottom:6px;">FG%</div>
                        <div style="font-size:26px; font-weight:500; color:#6b8cff;">{pct:.1f}%</div>
                    </div>
                </div>""",
                unsafe_allow_html=True
            )

            # zone breakdown bar chart — short labels, bigger fonts
            st.markdown(
                "<div style='font-size:12px; color:#6b7280; text-transform:uppercase; "
                "letter-spacing:0.08em; margin-bottom:12px;'>Zone breakdown</div>",
                unsafe_allow_html=True
            )

            if not filtered_shots.empty:
                zone_df = filtered_shots.groupby('shot_zone_basic').agg(
                    attempts=('shot_made', 'count'),
                    makes=('shot_made', 'sum')
                ).reset_index()
                zone_df['fg_pct'] = (
                    zone_df['makes'] / zone_df['attempts'] * 100
                ).round(1)
                zone_df = zone_df.sort_values('attempts', ascending=False)
                max_attempts = zone_df['attempts'].max()

                bar_html = ""
                for _, row in zone_df.iterrows():
                    short = zone_short.get(row['shot_zone_basic'], row['shot_zone_basic'])
                    bar_width = int((row['attempts'] / max_attempts) * 100)
                    bar_html += f"""
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:9px;">
                        <div style="font-size:12px; color:#9ca3af; width:44px;
                                    text-align:right; flex-shrink:0;">{short}</div>
                        <div style="flex:1; height:7px; background:#1f2937; border-radius:3px;">
                            <div style="width:{bar_width}%; height:7px;
                                        background:#3b6dc4; border-radius:3px;"></div>
                        </div>
                        <div style="font-size:12px; color:#9ca3af; width:40px;">{row['fg_pct']}%</div>
                    </div>"""

                st.markdown(bar_html, unsafe_allow_html=True)

                st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

                # zone table — full names
                render_table(
                    zone_df[['shot_zone_basic', 'attempts', 'makes', 'fg_pct']]
                    .rename(columns={
                        'shot_zone_basic': 'Zone',
                        'attempts': 'Att',
                        'makes': 'Made',
                        'fg_pct': 'FG%'
                    })
                )
    else:
        st.info("No shot chart data available.")

# ── team vs team ──────────────────────────────────────────
elif page == "Team vs Team":
    st.title("Team vs Team")

    team_vs_team = load_team_vs_team()
    team_adv_season = load_team_advanced_season()
    team_game_results = load_team_game_results()

    team_options = sorted(
        team_records[team_records['team'].isin(NBA_TEAMS)]['team_name'].dropna().unique()
    )

    col1, col2, col3 = st.columns([5, 1, 5])
    with col1:
        team_a_name = st.selectbox("Team A", team_options, key="team_a")
    with col2:
        st.markdown("<div style='text-align:center; font-size:20px; padding-top:28px; color:#6b7280;'></div>",
                    unsafe_allow_html=True)
    with col3:
        team_b_name = st.selectbox("Team B", team_options, index=1, key="team_b")

    team_a = team_records[team_records['team_name'] == team_a_name].iloc[0]['team']
    team_b = team_records[team_records['team_name'] == team_b_name].iloc[0]['team']

    if team_a != team_b:
        a_data = team_records[team_records['team'] == team_a].iloc[0]
        b_data = team_records[team_records['team'] == team_b].iloc[0]

        col1, col2, col3 = st.columns([5, 1, 5])
        with col1:
            if pd.notna(a_data.get('logo_url')):
                st.markdown(
                    f"""<div style="display:flex; align-items:center; gap:16px;">
                        <img src="{a_data['logo_url']}" style="height:80px; width:auto;"/>
                        <div>
                            <div style="font-size:22px; font-weight:500; color:#f9fafb;">
                                {a_data.get('team_name', team_a)}</div>
                            <div style="font-size:13px; color:#6b7280;">
                                {a_data.get('conference', '')} · {a_data.get('division', '')}</div>
                            <div style="font-size:13px; color:#6b7280;">
                                {int(a_data['wins'])}-{int(a_data['losses'])} · {a_data['win_pct']:.1%}</div>
                        </div>
                    </div>""", unsafe_allow_html=True)
        with col2:
            st.markdown("<div style='text-align:center; padding-top:24px; color:#6b7280;'>VS</div>",
                        unsafe_allow_html=True)
        with col3:
            if pd.notna(b_data.get('logo_url')):
                st.markdown(
                    f"""<div style="display:flex; align-items:center; gap:16px;">
                        <img src="{b_data['logo_url']}" style="height:80px; width:auto;"/>
                        <div>
                            <div style="font-size:22px; font-weight:500; color:#f9fafb;">
                                {b_data.get('team_name', team_b)}</div>
                            <div style="font-size:13px; color:#6b7280;">
                                {b_data.get('conference', '')} · {b_data.get('division', '')}</div>
                            <div style="font-size:13px; color:#6b7280;">
                                {int(b_data['wins'])}-{int(b_data['losses'])} · {b_data['win_pct']:.1%}</div>
                        </div>
                    </div>""", unsafe_allow_html=True)

        st.divider()

        h2h = team_vs_team[
            (team_vs_team['team'] == team_a) &
            (team_vs_team['opponent'] == team_b)
        ]
        if not h2h.empty:
            h = h2h.iloc[0]
            st.subheader("Head to Head Record")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Games Played", int(h['games_played']))
            c2.metric(f"{team_a} Wins", int(h['wins']))
            c3.metric(f"{team_b} Wins", int(h['losses']))
            c4.metric("Avg Point Diff", h['avg_point_diff'])

        st.divider()

        def get_comparison(val_a, val_b, higher_is_better=True):
            try:
                a = float(str(val_a).replace('%', ''))
                b = float(str(val_b).replace('%', ''))
                if a == b:
                    return None, None
                winner = 'a' if (a > b) == higher_is_better else 'b'
                pct = abs((a - b) / abs(b)) * 100 if b != 0 else 0
                pct_str = f"{pct:.1f}%"
                return (f"+{pct_str}" if winner == 'a' else f"-{pct_str}",
                        f"+{pct_str}" if winner == 'b' else f"-{pct_str}")
            except:
                return None, None

        st.subheader("Season Stats Comparison")
        stats = [
            ("Wins",       int(a_data['wins']),         int(b_data['wins']),         True),
            ("Losses",     int(a_data['losses']),       int(b_data['losses']),       False),
            ("Win %",      a_data['win_pct'],           b_data['win_pct'],           True),
            ("PPG",        a_data['avg_pts'],           b_data['avg_pts'],           True),
            ("Opp PPG",    a_data['avg_pts_allowed'],   b_data['avg_pts_allowed'],   False),
            ("Point Diff", a_data['avg_point_diff'],    b_data['avg_point_diff'],    True),
            ("RPG",        a_data['avg_reb'],           b_data['avg_reb'],           True),
            ("APG",        a_data['avg_ast'],           b_data['avg_ast'],           True),
            ("SPG",        a_data['avg_stl'],           b_data['avg_stl'],           True),
            ("BPG",        a_data['avg_blk'],           b_data['avg_blk'],           True),
            ("TOV",        a_data['avg_tov'],           b_data['avg_tov'],           False),
            ("FG%",        a_data['fg_pct'],            b_data['fg_pct'],            True),
            ("3P%",        a_data['fg3_pct'],           b_data['fg3_pct'],           True),
            ("FT%",        a_data['ft_pct'],            b_data['ft_pct'],            True),
        ]

        col_stat, col_a, col_b = st.columns([2, 3, 3])
        col_stat.markdown("**Stat**")
        col_a.markdown(f"**{team_a}**")
        col_b.markdown(f"**{team_b}**")

        for stat, val_a, val_b, hib in stats:
            d_a, d_b = get_comparison(val_a, val_b, hib)
            display_a = f"{val_a:.1%}" if isinstance(val_a, float) and val_a < 1 and stat != "Point Diff" else val_a
            display_b = f"{val_b:.1%}" if isinstance(val_b, float) and val_b < 1 and stat != "Point Diff" else val_b
            col_stat, col_a, col_b = st.columns([2, 3, 3])
            col_stat.markdown(stat)
            col_a.metric("", display_a, delta=d_a, label_visibility="collapsed")
            col_b.metric("", display_b, delta=d_b, label_visibility="collapsed")

        st.divider()

        st.subheader("Advanced Stats Comparison")
        a_adv = team_adv_season[team_adv_season['team_name'] == a_data['team_name']]
        b_adv = team_adv_season[team_adv_season['team_name'] == b_data['team_name']]

        if not a_adv.empty and not b_adv.empty:
            a_s = a_adv.iloc[0]
            b_s = b_adv.iloc[0]
            adv_stats = [
                ("ORtg",    a_s['off_rating'],  b_s['off_rating'],  True),
                ("DRtg",    a_s['def_rating'],  b_s['def_rating'],  False),
                ("Net Rtg", a_s['net_rating'],  b_s['net_rating'],  True),
                ("Pace",    a_s['pace'],        b_s['pace'],        True),
                ("eFG%",    a_s['efg_pct'],     b_s['efg_pct'],     True),
                ("TS%",     a_s['ts_pct'],      b_s['ts_pct'],      True),
                ("TOV%",    a_s['tov_pct'],     b_s['tov_pct'],     False),
                ("PIE",     a_s['pie'],         b_s['pie'],         True),
            ]
            col_stat, col_a, col_b = st.columns([2, 3, 3])
            col_stat.markdown("**Stat**")
            col_a.markdown(f"**{team_a}**")
            col_b.markdown(f"**{team_b}**")

            for stat, val_a, val_b, hib in adv_stats:
                d_a, d_b = get_comparison(val_a, val_b, hib)
                display_a = f"{val_a:.1%}" if isinstance(val_a, float) and val_a < 1 else round(float(val_a), 1)
                display_b = f"{val_b:.1%}" if isinstance(val_b, float) and val_b < 1 else round(float(val_b), 1)
                col_stat, col_a, col_b = st.columns([2, 3, 3])
                col_stat.markdown(stat)
                col_a.metric("", display_a, delta=d_a, label_visibility="collapsed")
                col_b.metric("", display_b, delta=d_b, label_visibility="collapsed")

        st.divider()

        st.subheader("Game Results")
        games = team_game_results[
            (team_game_results['team'] == team_a) &
            (team_game_results['opponent'] == team_b)
        ].sort_values('GAME_DATE', ascending=False)

        if not games.empty:
            render_table(
                games[['GAME_DATE', 'team', 'team_pts', 'opponent_pts', 'result']]
                .rename(columns={'GAME_DATE': 'Date', 'team': 'Team',
                                 'team_pts': f'{team_a} PTS',
                                 'opponent_pts': f'{team_b} PTS',
                                 'result': 'Result'})
            )
    else:
        st.warning("Please select two different teams.")

# ── player comparison ─────────────────────────────────────
elif page == "Player Comparison":
    st.title("Player Comparison")

    player_advanced = load_player_advanced()
    player_consistency = load_player_consistency()

    selected_players = st.multiselect(
        "Select Players to Compare (2–4)",
        sorted(player_avg['player_name'].unique()),
        max_selections=4
    )

    if len(selected_players) >= 2:
        st.divider()

        st.subheader("Basic Stats")
        render_table(
            player_avg[player_avg['player_name'].isin(selected_players)][[
                'player_name', 'team', 'games_played', 'min',
                'pts', 'reb', 'ast', 'stl', 'blk', 'tov',
                'fg_pct', 'fg3_pct', 'ft_pct'
            ]].rename(columns={'player_name': 'Player', 'team': 'Team',
                               'games_played': 'GP', 'min': 'MIN',
                               'pts': 'PTS', 'reb': 'REB', 'ast': 'AST',
                               'stl': 'STL', 'blk': 'BLK', 'tov': 'TOV',
                               'fg_pct': 'FG%', 'fg3_pct': '3P%', 'ft_pct': 'FT%'})
        )

        st.divider()

        st.subheader("Advanced Stats")
        render_table(
            player_advanced[player_advanced['player_name'].isin(selected_players)][[
                'player_name', 'ts_pct', 'efg_pct', 'usg_pct',
                'bpm_approx', 'vorp_approx', 'ws_approx', 'ortg', 'drtg'
            ]].rename(columns={'player_name': 'Player', 'ts_pct': 'TS%',
                               'efg_pct': 'eFG%', 'usg_pct': 'USG%',
                               'bpm_approx': 'BPM', 'vorp_approx': 'VORP',
                               'ws_approx': 'WS', 'ortg': 'ORtg', 'drtg': 'DRtg'})
        )

        st.divider()

        st.subheader("Consistency")
        render_table(
            player_consistency[player_consistency['player_name'].isin(selected_players)][[
                'player_name', 'avg_pts', 'std_pts', 'cv_pts',
                'avg_reb', 'std_reb', 'cv_reb',
                'avg_ast', 'std_ast', 'cv_ast'
            ]].rename(columns={'player_name': 'Player',
                               'avg_pts': 'PPG', 'std_pts': 'PTS SD', 'cv_pts': 'PTS CV',
                               'avg_reb': 'RPG', 'std_reb': 'REB SD', 'cv_reb': 'REB CV',
                               'avg_ast': 'APG', 'std_ast': 'AST SD', 'cv_ast': 'AST CV'})
        )

        st.divider()

        st.subheader("Stat Radar")
        categories = ['pts', 'reb', 'ast', 'stl', 'blk']
        colors = ['#6b8cff', '#a78bfa', '#34d399', '#f87171']
        fig = go.Figure()
        for i, player in enumerate(selected_players):
            p_data = player_avg[player_avg['player_name'] == player].iloc[0]
            values = [p_data[cat] for cat in categories]
            values.append(values[0])
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=categories + [categories[0]],
                fill='toself',
                name=player,
                line_color=colors[i % len(colors)],
                fillcolor=colors[i % len(colors)],
                opacity=0.3
            ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, color='#6b7280', gridcolor='#1f2937'),
                angularaxis=dict(color='#6b7280'),
                bgcolor='#111827'
            ),
            plot_bgcolor='#111827',
            paper_bgcolor='#111827',
            font_color='#9ca3af',
            showlegend=True,
            height=400,
            legend=dict(bgcolor='#111827', bordercolor='#1f2937')
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Select at least 2 players to compare.")