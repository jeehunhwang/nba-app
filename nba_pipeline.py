import os
import pickle
import time
import pandas as pd
from datetime import datetime, timedelta
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.cloud import bigquery
from nba_api.stats.endpoints import (
    scoreboardv3,
    boxscoretraditionalv3,
    commonplayerinfo,
    boxscoresummaryv3,
    shotchartdetail,
    leaguedashteamstats
)
from nba_api.stats.static import teams as nba_teams

# ── config ────────────────────────────────────────────────
SCOPES = ['https://www.googleapis.com/auth/bigquery']
PROJECT_ID = "nba-dashboard-495409"
DATASET = "nba_stats"

TEAM_INFO = [
    {"team": "ATL", "team_id": 1610612737, "team_name": "Atlanta Hawks",           "conference": "East", "division": "Southeast"},
    {"team": "BOS", "team_id": 1610612738, "team_name": "Boston Celtics",           "conference": "East", "division": "Atlantic"},
    {"team": "BKN", "team_id": 1610612751, "team_name": "Brooklyn Nets",            "conference": "East", "division": "Atlantic"},
    {"team": "CHA", "team_id": 1610612766, "team_name": "Charlotte Hornets",        "conference": "East", "division": "Southeast"},
    {"team": "CHI", "team_id": 1610612741, "team_name": "Chicago Bulls",            "conference": "East", "division": "Central"},
    {"team": "CLE", "team_id": 1610612739, "team_name": "Cleveland Cavaliers",      "conference": "East", "division": "Central"},
    {"team": "DAL", "team_id": 1610612742, "team_name": "Dallas Mavericks",         "conference": "West", "division": "Southwest"},
    {"team": "DEN", "team_id": 1610612743, "team_name": "Denver Nuggets",           "conference": "West", "division": "Northwest"},
    {"team": "DET", "team_id": 1610612765, "team_name": "Detroit Pistons",          "conference": "East", "division": "Central"},
    {"team": "GSW", "team_id": 1610612744, "team_name": "Golden State Warriors",    "conference": "West", "division": "Pacific"},
    {"team": "HOU", "team_id": 1610612745, "team_name": "Houston Rockets",          "conference": "West", "division": "Southwest"},
    {"team": "IND", "team_id": 1610612754, "team_name": "Indiana Pacers",           "conference": "East", "division": "Central"},
    {"team": "LAC", "team_id": 1610612746, "team_name": "LA Clippers",              "conference": "West", "division": "Pacific"},
    {"team": "LAL", "team_id": 1610612747, "team_name": "Los Angeles Lakers",       "conference": "West", "division": "Pacific"},
    {"team": "MEM", "team_id": 1610612763, "team_name": "Memphis Grizzlies",        "conference": "West", "division": "Southwest"},
    {"team": "MIA", "team_id": 1610612748, "team_name": "Miami Heat",               "conference": "East", "division": "Southeast"},
    {"team": "MIL", "team_id": 1610612749, "team_name": "Milwaukee Bucks",          "conference": "East", "division": "Central"},
    {"team": "MIN", "team_id": 1610612750, "team_name": "Minnesota Timberwolves",   "conference": "West", "division": "Northwest"},
    {"team": "NOP", "team_id": 1610612740, "team_name": "New Orleans Pelicans",     "conference": "West", "division": "Southwest"},
    {"team": "NYK", "team_id": 1610612752, "team_name": "New York Knicks",          "conference": "East", "division": "Atlantic"},
    {"team": "OKC", "team_id": 1610612760, "team_name": "Oklahoma City Thunder",    "conference": "West", "division": "Northwest"},
    {"team": "ORL", "team_id": 1610612753, "team_name": "Orlando Magic",            "conference": "East", "division": "Southeast"},
    {"team": "PHI", "team_id": 1610612755, "team_name": "Philadelphia 76ers",       "conference": "East", "division": "Atlantic"},
    {"team": "PHX", "team_id": 1610612756, "team_name": "Phoenix Suns",             "conference": "West", "division": "Pacific"},
    {"team": "POR", "team_id": 1610612757, "team_name": "Portland Trail Blazers",   "conference": "West", "division": "Northwest"},
    {"team": "SAC", "team_id": 1610612758, "team_name": "Sacramento Kings",         "conference": "West", "division": "Pacific"},
    {"team": "SAS", "team_id": 1610612759, "team_name": "San Antonio Spurs",        "conference": "West", "division": "Southwest"},
    {"team": "TOR", "team_id": 1610612761, "team_name": "Toronto Raptors",          "conference": "East", "division": "Atlantic"},
    {"team": "UTA", "team_id": 1610612762, "team_name": "Utah Jazz",                "conference": "West", "division": "Northwest"},
    {"team": "WAS", "team_id": 1610612764, "team_name": "Washington Wizards",       "conference": "East", "division": "Southeast"},
]

# ── auth ──────────────────────────────────────────────────
def get_bq_client():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return bigquery.Client(project=PROJECT_ID, credentials=creds)

# ── fetch functions ───────────────────────────────────────
def get_completed_games(game_date):
    board = scoreboardv3.ScoreboardV3(game_date=game_date)
    games = board.game_header.get_data_frame()
    completed = games[games["gameStatus"] == 3][["gameId", "gameEt"]]
    completed = completed.rename(columns={"gameId": "GAME_ID", "gameEt": "GAME_DATE_EST"})
    print(f"Found {len(completed)} completed games on {game_date}")
    return completed

def get_box_scores(completed, game_date):
    all_boxes = []
    for game_id in completed["GAME_ID"]:
        print(f"Fetching box score: {game_id}")
        box = boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=game_id, timeout=60)
        df = box.player_stats.get_data_frame()
        df["GAME_DATE"] = game_date
        all_boxes.append(df)
        time.sleep(1)
    if not all_boxes:
        return pd.DataFrame()
    return pd.concat(all_boxes).reset_index(drop=True)

def clean_box_scores(raw):
    cols = [
        "GAME_DATE", "gameId", "teamTricode",
        "personId", "firstName", "familyName", "minutes",
        "points", "reboundsTotal", "assists",
        "steals", "blocks", "turnovers",
        "fieldGoalsMade", "fieldGoalsAttempted", "fieldGoalsPercentage",
        "threePointersMade", "threePointersAttempted", "threePointersPercentage",
        "freeThrowsMade", "freeThrowsAttempted", "freeThrowsPercentage"
    ]
    df = raw[cols].copy()
    df["player_name"] = df["firstName"] + " " + df["familyName"]
    df = df.drop(columns=["firstName", "familyName"])
    df["minutes"] = df["minutes"].apply(
        lambda x: round(int(str(x).split(":")[0]) + int(str(x).split(":")[1])/60, 1)
        if pd.notna(x) and ":" in str(x) else None
    )
    df = df[df["minutes"] > 0].reset_index(drop=True)
    df = df.rename(columns={
        "gameId": "game_id",
        "teamTricode": "team",
        "personId": "player_id",
        "minutes": "min",
        "points": "pts",
        "reboundsTotal": "reb",
        "assists": "ast",
        "steals": "stl",
        "blocks": "blk",
        "turnovers": "tov",         # renamed from "to"
        "fieldGoalsMade": "fgm",
        "fieldGoalsAttempted": "fga",
        "fieldGoalsPercentage": "fg_pct",
        "threePointersMade": "fg3m",
        "threePointersAttempted": "fg3a",
        "threePointersPercentage": "fg3_pct",
        "freeThrowsMade": "ftm",
        "freeThrowsAttempted": "fta",
        "freeThrowsPercentage": "ft_pct"
    })
    return df

def get_game_summary(game_id, game_date):
    summary = boxscoresummaryv3.BoxScoreSummaryV3(game_id=game_id)
    other_stats = summary.other_stats.get_data_frame()
    if other_stats.empty:
        return pd.DataFrame()
    rows = []
    for _, row in other_stats.iterrows():
        rows.append({
            "game_id": game_id,
            "game_date": game_date,
            "team": row["teamTricode"],
            "pts_paint": row["pointsInThePaint"],
            "pts_second_chance": row["pointsSecondChance"],
            "pts_off_turnovers": row["pointsFromTurnovers"],
            "pts_fast_break": row["pointsFastBreak"],
            "largest_lead": row["biggestLead"],
            "biggest_scoring_run": row["biggestScoringRun"],
            "lead_changes": row["leadChanges"],
            "times_tied": row["timesTied"],
            "bench_points": row["benchPoints"],
            "turnovers_team": row["turnoversTeam"],
            "turnovers_total": row["turnoversTotal"],
            "rebounds_team": row["reboundsTeam"],
        })
    return pd.DataFrame(rows)

def get_game_shot_chart(game_id, team_id, game_date):
    shot_chart = shotchartdetail.ShotChartDetail(
        team_id=team_id,
        player_id=0,
        game_id_nullable=game_id,
        season_nullable="2025-26",
        season_type_all_star="Regular Season",
        context_measure_simple="FGA",
        timeout=60
    )
    df = shot_chart.get_data_frames()[0]
    if not df.empty:
        df["GAME_DATE"] = game_date
    return df

def clean_shot_chart(df, team):
    cols = [
        "GAME_ID", "GAME_DATE", "PLAYER_ID", "PLAYER_NAME",
        "TEAM_ID", "TEAM_NAME", "PERIOD", "MINUTES_REMAINING",
        "SECONDS_REMAINING", "EVENT_TYPE", "ACTION_TYPE",
        "SHOT_TYPE", "SHOT_ZONE_BASIC", "SHOT_ZONE_AREA",
        "SHOT_ZONE_RANGE", "SHOT_DISTANCE", "LOC_X", "LOC_Y",
        "SHOT_MADE_FLAG"
    ]
    df = df[cols].copy()
    df["team"] = team
    df = df.rename(columns={
        "GAME_ID": "game_id", "GAME_DATE": "game_date",
        "PLAYER_ID": "player_id", "PLAYER_NAME": "player_name",
        "TEAM_ID": "team_id", "TEAM_NAME": "team_name",
        "PERIOD": "period", "MINUTES_REMAINING": "minutes_remaining",
        "SECONDS_REMAINING": "seconds_remaining", "EVENT_TYPE": "event_type",
        "ACTION_TYPE": "action_type", "SHOT_TYPE": "shot_type",
        "SHOT_ZONE_BASIC": "shot_zone_basic", "SHOT_ZONE_AREA": "shot_zone_area",
        "SHOT_ZONE_RANGE": "shot_zone_range", "SHOT_DISTANCE": "shot_distance",
        "LOC_X": "loc_x", "LOC_Y": "loc_y", "SHOT_MADE_FLAG": "shot_made"
    })
    return df

# ── push functions ────────────────────────────────────────
def push_to_bq(bq, df, table, mode="WRITE_APPEND"):
    if df.empty:
        print(f"Skipping {table} — empty DataFrame")
        return
    if table == "raw_box_scores":
        df = df.drop_duplicates(subset=["game_id", "player_id"])
    elif table == "game_summary":
        df = df.drop_duplicates(subset=["game_id", "team"])
    elif table == "shot_charts":
        df = df.drop_duplicates(subset=["game_id", "player_id", "loc_x", "loc_y", "period", "minutes_remaining", "seconds_remaining"])
    try:
        game_ids = df["game_id"].unique().tolist()
        game_ids_str = ", ".join([f"'{g}'" for g in game_ids])
        existing = bq.query(f"""
            SELECT DISTINCT game_id
            FROM `{PROJECT_ID}.{DATASET}.{table}`
            WHERE game_id IN ({game_ids_str})
        """).to_dataframe()
        existing_ids = existing["game_id"].tolist()
        df = df[~df["game_id"].isin(existing_ids)]
        if df.empty:
            print(f"⏭  {table} — all game_ids already exist, skipping")
            return
        print(f"Pushing {len(df)} new rows to {table}")
    except Exception:
        print(f"Table {table} doesn't exist yet — pushing all rows")
    job_config = bigquery.LoadJobConfig(
        write_disposition=mode,
        autodetect=True
    )
    bq.load_table_from_dataframe(
        df, f"{PROJECT_ID}.{DATASET}.{table}", job_config=job_config
    ).result()
    print(f"✅ Pushed {len(df)} rows to {table}")

# ── team advanced stats ───────────────────────────────────
def fetch_team_advanced_stats(season="2025-26"):
    stats = leaguedashteamstats.LeagueDashTeamStats(
        season=season,
        season_type_all_star="Regular Season",
        measure_type_detailed_defense="Advanced"
    )
    df = stats.league_dash_team_stats.get_data_frame()
    df = df[[
        "TEAM_ID", "TEAM_NAME", "GP", "W", "L", "W_PCT",
        "OFF_RATING", "DEF_RATING", "NET_RATING",
        "AST_PCT", "AST_TO", "AST_RATIO",
        "OREB_PCT", "DREB_PCT", "REB_PCT",
        "TM_TOV_PCT", "EFG_PCT", "TS_PCT",
        "PACE", "PACE_PER40", "POSS", "PIE"
    ]].copy()
    df = df.rename(columns={
        "TEAM_ID": "team_id", "TEAM_NAME": "team_name",
        "GP": "games_played", "W": "wins", "L": "losses", "W_PCT": "win_pct",
        "OFF_RATING": "off_rating", "DEF_RATING": "def_rating",
        "NET_RATING": "net_rating", "AST_PCT": "ast_pct",
        "AST_TO": "ast_to", "AST_RATIO": "ast_ratio",
        "OREB_PCT": "oreb_pct", "DREB_PCT": "dreb_pct", "REB_PCT": "reb_pct",
        "TM_TOV_PCT": "tov_pct", "EFG_PCT": "efg_pct", "TS_PCT": "ts_pct",
        "PACE": "pace", "PACE_PER40": "pace_per40", "POSS": "possessions", "PIE": "pie"
    })
    df["season"] = season
    return df

def build_team_advanced_table(bq, season="2025-26"):
    df = fetch_team_advanced_stats(season)
    push_to_bq(bq, df, "team_advanced_season", mode="WRITE_TRUNCATE")
    print(f"✅ team_advanced_season table created with {len(df)} teams")

# ── player info ───────────────────────────────────────────
def build_player_info_table(bq):
    existing_ids = bq.query(f"""
        SELECT DISTINCT player_id
        FROM `{PROJECT_ID}.{DATASET}.raw_box_scores`
    """).to_dataframe()
    player_ids = existing_ids["player_id"].dropna().unique().tolist()
    print(f"Found {len(player_ids)} unique players")
    rows = []
    for i, pid in enumerate(player_ids):
        try:
            info = commonplayerinfo.CommonPlayerInfo(player_id=int(pid))
            df = info.common_player_info.get_data_frame()
            rows.append({
                "player_id": int(pid),
                "player_name": df["DISPLAY_FIRST_LAST"].values[0],
                "jersey": df["JERSEY"].values[0],
                "position": df["POSITION"].values[0],
                "height": df["HEIGHT"].values[0],
                "weight": df["WEIGHT"].values[0],
                "country": df["COUNTRY"].values[0],
                "team": df["TEAM_ABBREVIATION"].values[0],
                "team_name": df["TEAM_NAME"].values[0],
                "headshot_url": f"https://cdn.nba.com/headshots/nba/latest/1040x760/{int(pid)}.png"
            })
            if i % 50 == 0:
                print(f"Progress: {i}/{len(player_ids)}")
            time.sleep(0.6)
        except Exception as e:
            print(f"❌ Error for player_id {pid}: {e}")
    player_info_df = pd.DataFrame(rows)
    push_to_bq(bq, player_info_df, "player_info", mode="WRITE_TRUNCATE")
    print(f"✅ player_info table created with {len(player_info_df)} players")

# ── team info ─────────────────────────────────────────────
def build_team_info_table(bq):
    team_info_df = pd.DataFrame(TEAM_INFO)
    team_info_df["logo_url"] = team_info_df["team_id"].apply(
        lambda x: f"https://cdn.nba.com/logos/nba/{x}/global/L/logo.svg"
    )
    push_to_bq(bq, team_info_df, "team_info", mode="WRITE_TRUNCATE")
    print(f"✅ team_info table created with {len(team_info_df)} teams")

# ── bigquery views ────────────────────────────────────────
def create_views(bq):
    views = {
        "player_averages": f"""
            CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.player_averages` AS
            SELECT
              r.player_name, r.player_id, r.team,
              pi.headshot_url, pi.position, pi.jersey, pi.team_name,
              ti.logo_url as team_logo_url, ti.conference, ti.division,
              COUNT(DISTINCT r.game_id) as games_played,
              ROUND(AVG(r.min), 1) as min,
              ROUND(AVG(r.pts), 1) as pts,
              ROUND(AVG(r.reb), 1) as reb,
              ROUND(AVG(r.ast), 1) as ast,
              ROUND(AVG(r.stl), 1) as stl,
              ROUND(AVG(r.blk), 1) as blk,
              ROUND(AVG(r.tov), 1) as tov,
              ROUND(AVG(r.fgm), 1) as fgm,
              ROUND(AVG(r.fga), 1) as fga,
              ROUND(AVG(r.fg_pct), 3) as fg_pct,
              ROUND(AVG(r.fg3m), 1) as fg3m,
              ROUND(AVG(r.fg3a), 1) as fg3a,
              ROUND(AVG(r.fg3_pct), 3) as fg3_pct,
              ROUND(AVG(r.ftm), 1) as ftm,
              ROUND(AVG(r.fta), 1) as fta,
              ROUND(AVG(r.ft_pct), 3) as ft_pct
            FROM `{PROJECT_ID}.{DATASET}.raw_box_scores` r
            LEFT JOIN `{PROJECT_ID}.{DATASET}.player_info` pi ON r.player_id = pi.player_id
            LEFT JOIN `{PROJECT_ID}.{DATASET}.team_info` ti ON r.team = ti.team
            GROUP BY
              r.player_name, r.player_id, r.team,
              pi.headshot_url, pi.position, pi.jersey, pi.team_name,
              ti.logo_url, ti.conference, ti.division
        """,

        "player_advanced_stats": f"""
            CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.player_advanced_stats` AS
            WITH team_stats AS (
                SELECT team_id, pace, possessions, off_rating, def_rating
                FROM `{PROJECT_ID}.{DATASET}.team_advanced_season`
            ),
            player_base AS (
                SELECT
                    r.player_name, r.player_id, r.team,
                    pi.headshot_url, pi.position,
                    ti.team_id, ti.team_name, ti.logo_url as team_logo_url,
                    COUNT(DISTINCT r.game_id) as games_played,
                    ROUND(AVG(r.min), 1) as min,
                    ROUND(AVG(r.pts), 1) as pts,
                    ROUND(AVG(r.reb), 1) as reb,
                    ROUND(AVG(r.ast), 1) as ast,
                    ROUND(AVG(r.stl), 1) as stl,
                    ROUND(AVG(r.blk), 1) as blk,
                    ROUND(AVG(r.tov), 1) as tov,
                    ROUND(AVG(r.fgm), 1) as fgm,
                    ROUND(AVG(r.fga), 1) as fga,
                    ROUND(AVG(r.fg3m), 1) as fg3m,
                    ROUND(AVG(r.fg3a), 1) as fg3a,
                    ROUND(AVG(r.ftm), 1) as ftm,
                    ROUND(AVG(r.fta), 1) as fta,
                    ROUND(AVG(r.fg_pct), 3) as fg_pct,
                    ROUND(AVG(r.fg3_pct), 3) as fg3_pct,
                    ROUND(AVG(r.ft_pct), 3) as ft_pct,
                    SUM(r.min) as total_min,
                    SUM(r.fga) as total_fga,
                    SUM(r.fta) as total_fta,
                    SUM(r.tov) as total_tov
                FROM `{PROJECT_ID}.{DATASET}.raw_box_scores` r
                LEFT JOIN `{PROJECT_ID}.{DATASET}.player_info` pi ON r.player_id = pi.player_id
                LEFT JOIN `{PROJECT_ID}.{DATASET}.team_info` ti ON r.team = ti.team
                GROUP BY
                    r.player_name, r.player_id, r.team,
                    pi.headshot_url, pi.position,
                    ti.team_id, ti.team_name, ti.logo_url
            )
            SELECT
                p.player_name, p.player_id, p.team, p.team_name,
                p.headshot_url, p.position, p.team_logo_url,
                p.games_played, p.min, p.pts, p.reb, p.ast,
                p.stl, p.blk, p.tov, p.fgm, p.fga, p.fg3m,
                p.fg3a, p.ftm, p.fta, p.fg_pct, p.fg3_pct, p.ft_pct,
                -- TS%
                ROUND(p.pts / NULLIF(2 * (p.fga + 0.44 * p.fta), 0), 3) as ts_pct,
                -- eFG%
                ROUND((p.fgm + 0.5 * p.fg3m) / NULLIF(p.fga, 0), 3) as efg_pct,
                -- AST ratio
                ROUND(p.ast / NULLIF(p.fga + 0.44 * p.fta + p.ast + p.tov, 0), 3) as ast_ratio,
                -- TOV ratio
                ROUND(p.tov / NULLIF(p.fga + 0.44 * p.fta + p.ast + p.tov, 0), 3) as tov_ratio,
                -- 3PT rate
                ROUND(p.fg3a / NULLIF(p.fga, 0), 3) as three_pt_rate,
                -- FT rate
                ROUND(p.fta / NULLIF(p.fga, 0), 3) as ft_rate,
                -- pts per shot
                ROUND(p.pts / NULLIF(p.fga + 0.44 * p.fta, 0), 3) as pts_per_shot,
                -- USG%
                ROUND(
                    (p.total_fga + 0.44 * p.total_fta + p.total_tov) /
                    NULLIF(t.possessions * (p.total_min / (p.games_played * 48 * 5)), 0)
                , 3) as usg_pct,
                -- ORtg
                ROUND(
                    p.pts / NULLIF(
                        (p.total_fga + 0.44 * p.total_fta + p.total_tov) / p.games_played
                    , 0) * 100
                , 1) as ortg,
                -- DRtg (team proxy)
                ROUND(t.def_rating, 1) as drtg,
                -- BPM approximation
                ROUND(
                    (p.pts + 0.7*p.ast + 0.7*p.reb + p.stl + p.blk - p.tov
                     - 0.7*(p.fga - p.fgm) - 0.4*(p.fta - p.ftm))
                    / NULLIF(p.min, 0) * 36
                , 2) as bpm_approx,
                -- VORP approximation
                ROUND(
                    ((p.pts + 0.7*p.ast + 0.7*p.reb + p.stl + p.blk - p.tov
                      - 0.7*(p.fga - p.fgm) - 0.4*(p.fta - p.ftm))
                     / NULLIF(p.min, 0) * 36 + 2)
                    * (p.total_min / 48)
                    * (p.games_played / 82)
                , 2) as vorp_approx,
                -- Win Shares approximation
                ROUND(
                    (p.pts + p.reb + p.ast + p.stl + p.blk - p.tov
                     - (p.fga - p.fgm) - (p.fta - p.ftm))
                    / NULLIF(p.games_played, 0) / 30 * p.games_played
                , 2) as ws_approx
            FROM player_base p
            LEFT JOIN team_stats t ON p.team_id = t.team_id
        """,

        "player_consistency": f"""
            CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.player_consistency` AS
            SELECT
              player_name, player_id, team,
              COUNT(game_id) as games_played,
              ROUND(AVG(pts), 1) as avg_pts,
              ROUND(AVG(reb), 1) as avg_reb,
              ROUND(AVG(ast), 1) as avg_ast,
              ROUND(STDDEV(pts), 2) as std_pts,
              ROUND(STDDEV(reb), 2) as std_reb,
              ROUND(STDDEV(ast), 2) as std_ast,
              ROUND(VARIANCE(pts), 2) as var_pts,
              ROUND(VARIANCE(reb), 2) as var_reb,
              ROUND(VARIANCE(ast), 2) as var_ast,
              ROUND(STDDEV(pts) / NULLIF(AVG(pts), 0), 3) as cv_pts,
              ROUND(STDDEV(reb) / NULLIF(AVG(reb), 0), 3) as cv_reb,
              ROUND(STDDEV(ast) / NULLIF(AVG(ast), 0), 3) as cv_ast
            FROM `{PROJECT_ID}.{DATASET}.raw_box_scores`
            GROUP BY player_name, player_id, team
            HAVING COUNT(game_id) >= 10
        """,

        "player_season_highs": f"""
            CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.player_season_highs` AS
            SELECT
              player_name, player_id, team,
              MAX(pts) as season_high_pts,
              MAX(reb) as season_high_reb,
              MAX(ast) as season_high_ast,
              MAX(stl) as season_high_stl,
              MAX(blk) as season_high_blk,
              MAX(fgm) as season_high_fgm,
              MAX(fg3m) as season_high_fg3m,
              MAX(ftm) as season_high_ftm,
              MAX(min) as season_high_min
            FROM `{PROJECT_ID}.{DATASET}.raw_box_scores`
            GROUP BY player_name, player_id, team
        """,

        "team_game_results": f"""
            CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.team_game_results` AS
            WITH team_scores AS (
              SELECT
                game_id, GAME_DATE, team,
                SUM(pts) as team_pts, SUM(reb) as team_reb,
                SUM(ast) as team_ast, SUM(stl) as team_stl,
                SUM(blk) as team_blk, SUM(tov) as team_tov,
                SUM(fgm) as team_fgm, SUM(fga) as team_fga,
                SUM(fg3m) as team_fg3m, SUM(fg3a) as team_fg3a,
                SUM(ftm) as team_ftm, SUM(fta) as team_fta
              FROM `{PROJECT_ID}.{DATASET}.raw_box_scores`
              GROUP BY game_id, GAME_DATE, team
            )
            SELECT
              a.game_id, a.GAME_DATE, a.team,
              a.team_pts, a.team_reb, a.team_ast,
              a.team_stl, a.team_blk, a.team_tov,
              a.team_fgm, a.team_fga, a.team_fg3m,
              a.team_fg3a, a.team_ftm, a.team_fta,
              b.team as opponent, b.team_pts as opponent_pts,
              CASE WHEN a.team_pts > b.team_pts THEN 'W' ELSE 'L' END as result
            FROM team_scores a
            JOIN team_scores b ON a.game_id = b.game_id AND a.team != b.team
        """,

        "team_records": f"""
            CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.team_records` AS
            SELECT
              t.team, ti.team_name, ti.conference, ti.division, ti.logo_url,
              COUNT(*) as games_played,
              SUM(CASE WHEN t.result = 'W' THEN 1 ELSE 0 END) as wins,
              SUM(CASE WHEN t.result = 'L' THEN 1 ELSE 0 END) as losses,
              ROUND(SUM(CASE WHEN t.result = 'W' THEN 1 ELSE 0 END) / COUNT(*), 3) as win_pct,
              ROUND(AVG(t.team_pts), 1) as avg_pts,
              ROUND(AVG(t.opponent_pts), 1) as avg_pts_allowed,
              ROUND(AVG(t.team_pts) - AVG(t.opponent_pts), 1) as avg_point_diff,
              ROUND(AVG(t.team_reb), 1) as avg_reb,
              ROUND(AVG(t.team_ast), 1) as avg_ast,
              ROUND(AVG(t.team_stl), 1) as avg_stl,
              ROUND(AVG(t.team_blk), 1) as avg_blk,
              ROUND(AVG(t.team_tov), 1) as avg_tov,
              ROUND(AVG(t.team_fgm) / NULLIF(AVG(t.team_fga), 0), 3) as fg_pct,
              ROUND(AVG(t.team_fg3m) / NULLIF(AVG(t.team_fg3a), 0), 3) as fg3_pct,
              ROUND(AVG(t.team_ftm) / NULLIF(AVG(t.team_fta), 0), 3) as ft_pct
            FROM `{PROJECT_ID}.{DATASET}.team_game_results` t
            LEFT JOIN `{PROJECT_ID}.{DATASET}.team_info` ti ON t.team = ti.team
            GROUP BY t.team, ti.team_name, ti.conference, ti.division, ti.logo_url
            ORDER BY win_pct DESC
        """,

        "team_monthly_stats": f"""
            CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.team_monthly_stats` AS
            SELECT
              t.team, ti.team_name, ti.conference, ti.logo_url,
              FORMAT_DATE('%Y-%m', DATE(t.GAME_DATE)) as month,
              COUNT(*) as games_played,
              SUM(CASE WHEN t.result = 'W' THEN 1 ELSE 0 END) as wins,
              SUM(CASE WHEN t.result = 'L' THEN 1 ELSE 0 END) as losses,
              ROUND(AVG(t.team_pts), 1) as avg_pts,
              ROUND(AVG(t.opponent_pts), 1) as avg_pts_allowed,
              ROUND(AVG(t.team_pts) - AVG(t.opponent_pts), 1) as avg_point_diff,
              ROUND(AVG(t.team_reb), 1) as avg_reb,
              ROUND(AVG(t.team_ast), 1) as avg_ast,
              ROUND(AVG(t.team_tov), 1) as avg_tov,
              ROUND(AVG(t.team_fgm) / NULLIF(AVG(t.team_fga), 0), 3) as fg_pct,
              ROUND(AVG(t.team_fg3m) / NULLIF(AVG(t.team_fg3a), 0), 3) as fg3_pct
            FROM `{PROJECT_ID}.{DATASET}.team_game_results` t
            LEFT JOIN `{PROJECT_ID}.{DATASET}.team_info` ti ON t.team = ti.team
            GROUP BY t.team, ti.team_name, ti.conference, ti.logo_url, month
            ORDER BY t.team, month
        """,

        "team_vs_team": f"""
            CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.team_vs_team` AS
            SELECT
              t.team, ti.team_name, ti.logo_url,
              t.opponent, ti2.team_name as opponent_name, ti2.logo_url as opponent_logo_url,
              COUNT(*) as games_played,
              SUM(CASE WHEN t.result = 'W' THEN 1 ELSE 0 END) as wins,
              SUM(CASE WHEN t.result = 'L' THEN 1 ELSE 0 END) as losses,
              ROUND(AVG(t.team_pts), 1) as avg_pts,
              ROUND(AVG(t.opponent_pts), 1) as avg_pts_allowed,
              ROUND(AVG(t.team_pts) - AVG(t.opponent_pts), 1) as avg_point_diff
            FROM `{PROJECT_ID}.{DATASET}.team_game_results` t
            LEFT JOIN `{PROJECT_ID}.{DATASET}.team_info` ti ON t.team = ti.team
            LEFT JOIN `{PROJECT_ID}.{DATASET}.team_info` ti2 ON t.opponent = ti2.team
            GROUP BY t.team, ti.team_name, ti.logo_url, t.opponent, ti2.team_name, ti2.logo_url
            ORDER BY t.team, t.opponent
        """,

        "team_advanced_stats": f"""
            CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.team_advanced_stats` AS
            SELECT
              g.team, ti.team_name, ti.logo_url,
              COUNT(DISTINCT g.game_id) as games_played,
              ROUND(AVG(g.pts_paint), 1) as avg_pts_paint,
              ROUND(AVG(g.pts_second_chance), 1) as avg_pts_second_chance,
              ROUND(AVG(g.pts_off_turnovers), 1) as avg_pts_off_turnovers,
              ROUND(AVG(g.pts_fast_break), 1) as avg_pts_fast_break,
              ROUND(AVG(g.largest_lead), 1) as avg_largest_lead,
              ROUND(AVG(g.biggest_scoring_run), 1) as avg_biggest_scoring_run,
              ROUND(AVG(g.lead_changes), 1) as avg_lead_changes,
              ROUND(AVG(g.times_tied), 1) as avg_times_tied,
              ROUND(AVG(g.bench_points), 1) as avg_bench_points,
              ROUND(AVG(g.turnovers_team), 1) as avg_turnovers_team,
              ROUND(AVG(g.turnovers_total), 1) as avg_turnovers_total,
              ROUND(AVG(g.rebounds_team), 1) as avg_rebounds_team
            FROM `{PROJECT_ID}.{DATASET}.game_summary` g
            LEFT JOIN `{PROJECT_ID}.{DATASET}.team_info` ti ON g.team = ti.team
            GROUP BY g.team, ti.team_name, ti.logo_url
            ORDER BY avg_pts_paint DESC
        """,

        "player_vs_opponent": f"""
            CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.player_vs_opponent` AS
            SELECT
              r.player_name, r.player_id, r.team,
              t.opponent,
              COUNT(r.game_id) as games_played,
              ROUND(AVG(r.pts), 1) as avg_pts,
              ROUND(AVG(r.reb), 1) as avg_reb,
              ROUND(AVG(r.ast), 1) as avg_ast,
              ROUND(AVG(r.stl), 1) as avg_stl,
              ROUND(AVG(r.blk), 1) as avg_blk,
              ROUND(AVG(r.min), 1) as avg_min,
              ROUND(AVG(r.fg_pct), 3) as avg_fg_pct
            FROM `{PROJECT_ID}.{DATASET}.raw_box_scores` r
            JOIN `{PROJECT_ID}.{DATASET}.team_game_results` t
              ON r.game_id = t.game_id AND r.team = t.team
            GROUP BY r.player_name, r.player_id, r.team, t.opponent
            ORDER BY r.player_name, avg_pts DESC
        """,

        "player_rolling_averages": f"""
            CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.player_rolling_averages` AS
            SELECT
              player_name, player_id, team, GAME_DATE, game_id, pts, reb, ast,
              ROUND(AVG(pts) OVER (PARTITION BY player_name ORDER BY GAME_DATE ROWS BETWEEN 4 PRECEDING AND CURRENT ROW), 1) as rolling_5_pts,
              ROUND(AVG(reb) OVER (PARTITION BY player_name ORDER BY GAME_DATE ROWS BETWEEN 4 PRECEDING AND CURRENT ROW), 1) as rolling_5_reb,
              ROUND(AVG(ast) OVER (PARTITION BY player_name ORDER BY GAME_DATE ROWS BETWEEN 4 PRECEDING AND CURRENT ROW), 1) as rolling_5_ast,
              ROUND(AVG(pts) OVER (PARTITION BY player_name ORDER BY GAME_DATE ROWS BETWEEN 9 PRECEDING AND CURRENT ROW), 1) as rolling_10_pts,
              ROUND(AVG(reb) OVER (PARTITION BY player_name ORDER BY GAME_DATE ROWS BETWEEN 9 PRECEDING AND CURRENT ROW), 1) as rolling_10_reb,
              ROUND(AVG(ast) OVER (PARTITION BY player_name ORDER BY GAME_DATE ROWS BETWEEN 9 PRECEDING AND CURRENT ROW), 1) as rolling_10_ast,
              ROUND(AVG(pts) OVER (PARTITION BY player_name ORDER BY GAME_DATE ROWS BETWEEN 14 PRECEDING AND CURRENT ROW), 1) as rolling_15_pts,
              ROUND(AVG(reb) OVER (PARTITION BY player_name ORDER BY GAME_DATE ROWS BETWEEN 14 PRECEDING AND CURRENT ROW), 1) as rolling_15_reb,
              ROUND(AVG(ast) OVER (PARTITION BY player_name ORDER BY GAME_DATE ROWS BETWEEN 14 PRECEDING AND CURRENT ROW), 1) as rolling_15_ast
            FROM `{PROJECT_ID}.{DATASET}.raw_box_scores`
            ORDER BY player_name, GAME_DATE
        """,

        "team_shot_zones": f"""
            CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.team_shot_zones` AS
            SELECT
              team, shot_zone_basic, shot_zone_area,
              shot_zone_range, shot_type,
              COUNT(*) as attempts,
              SUM(shot_made) as makes,
              ROUND(SUM(shot_made) / NULLIF(COUNT(*), 0), 3) as fg_pct,
              ROUND(AVG(shot_distance), 1) as avg_distance
            FROM `{PROJECT_ID}.{DATASET}.shot_charts`
            GROUP BY team, shot_zone_basic, shot_zone_area, shot_zone_range, shot_type
            ORDER BY team, attempts DESC
        """,

        "team_shot_distribution": f"""
            CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.team_shot_distribution` AS
            SELECT
              team,
              ROUND(SUM(CASE WHEN shot_zone_basic = 'Restricted Area' THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) as pct_restricted_area,
              ROUND(SUM(CASE WHEN shot_zone_basic = 'In The Paint (Non-RA)' THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) as pct_paint_non_ra,
              ROUND(SUM(CASE WHEN shot_zone_basic = 'Mid-Range' THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) as pct_midrange,
              ROUND(SUM(CASE WHEN shot_zone_basic = 'Left Corner 3' THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) as pct_corner_3_left,
              ROUND(SUM(CASE WHEN shot_zone_basic = 'Right Corner 3' THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) as pct_corner_3_right,
              ROUND(SUM(CASE WHEN shot_zone_basic = 'Above the Break 3' THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) as pct_above_break_3,
              COUNT(*) as total_attempts,
              SUM(shot_made) as total_makes,
              ROUND(SUM(shot_made) / NULLIF(COUNT(*), 0), 3) as overall_fg_pct
            FROM `{PROJECT_ID}.{DATASET}.shot_charts`
            GROUP BY team
            ORDER BY team
        """,

        "game_shot_zones": f"""
            CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.game_shot_zones` AS
            SELECT
              game_id, game_date, team,
              shot_zone_basic, shot_zone_area, shot_zone_range, shot_type,
              COUNT(*) as attempts,
              SUM(shot_made) as makes,
              ROUND(SUM(shot_made) / NULLIF(COUNT(*), 0), 3) as fg_pct
            FROM `{PROJECT_ID}.{DATASET}.shot_charts`
            GROUP BY game_id, game_date, team, shot_zone_basic, shot_zone_area, shot_zone_range, shot_type
            ORDER BY game_date DESC, team
        """
    }

    for view_name, query in views.items():
        try:
            bq.query(query).result()
            print(f"✅ Created view: {view_name}")
        except Exception as e:
            print(f"❌ Error creating {view_name}: {e}")
    print("\nAll views created!")

# ── daily update ──────────────────────────────────────────
def daily_update(bq, game_date=None):
    if game_date is None:
        game_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"Fetching games for: {game_date}")
    completed = get_completed_games(game_date)
    if completed.empty:
        print("No games found, exiting.")
        return
    raw = get_box_scores(completed, game_date)
    if not raw.empty:
        nightly = clean_box_scores(raw)
        push_to_bq(bq, nightly, "raw_box_scores")
    all_summaries = []
    all_shots = []
    for game_id in completed["GAME_ID"]:
        try:
            summary_df = get_game_summary(game_id, game_date)
            if not summary_df.empty:
                all_summaries.append(summary_df)
            time.sleep(0.6)
        except Exception as e:
            print(f"❌ Summary error {game_id}: {e}")
        if not raw.empty:
            game_teams = nightly[nightly["game_id"] == game_id]["team"].unique()
            for team_abbr in game_teams:
                team_row = next((t for t in TEAM_INFO if t["team"] == team_abbr), None)
                if team_row:
                    try:
                        shots = get_game_shot_chart(game_id, team_row["team_id"], game_date)
                        if not shots.empty:
                            cleaned = clean_shot_chart(shots, team_abbr)
                            all_shots.append(cleaned)
                        time.sleep(0.6)
                    except Exception as e:
                        print(f"❌ Shot chart error {game_id} {team_abbr}: {e}")
    if all_summaries:
        combined_summaries = pd.concat(all_summaries)
        if not combined_summaries.empty:
            push_to_bq(bq, combined_summaries, "game_summary")
    if all_shots:
        combined_shots = pd.concat(all_shots)
        if not combined_shots.empty:
            push_to_bq(bq, combined_shots, "shot_charts")
    print(f"✅ Daily update done!")

# ── backfill ──────────────────────────────────────────────
def backfill_season(bq, start, end):
    current = datetime.strptime(start, "%Y-%m-%d")
    end_date = datetime.strptime(end, "%Y-%m-%d")
    while current <= end_date:
        game_date = current.strftime("%Y-%m-%d")
        try:
            completed = get_completed_games(game_date)
            if not completed.empty:
                raw = get_box_scores(completed, game_date)
                if not raw.empty:
                    nightly = clean_box_scores(raw)
                    push_to_bq(bq, nightly, "raw_box_scores")
                all_summaries = []
                all_shots = []
                for game_id in completed["GAME_ID"]:
                    try:
                        summary_df = get_game_summary(game_id, game_date)
                        if not summary_df.empty:
                            all_summaries.append(summary_df)
                        time.sleep(0.6)
                    except Exception as e:
                        print(f"❌ Summary error {game_id}: {e}")
                    if not raw.empty:
                        game_teams = nightly[nightly["game_id"] == game_id]["team"].unique()
                        for team_abbr in game_teams:
                            team_row = next((t for t in TEAM_INFO if t["team"] == team_abbr), None)
                            if team_row:
                                try:
                                    shots = get_game_shot_chart(game_id, team_row["team_id"], game_date)
                                    if not shots.empty:
                                        cleaned = clean_shot_chart(shots, team_abbr)
                                        all_shots.append(cleaned)
                                    time.sleep(0.6)
                                except Exception as e:
                                    print(f"❌ Shot chart error {game_id} {team_abbr}: {e}")
                if all_summaries:
                    combined_summaries = pd.concat(all_summaries)
                    if not combined_summaries.empty:
                        push_to_bq(bq, combined_summaries, "game_summary")
                if all_shots:
                    combined_shots = pd.concat(all_shots)
                    if not combined_shots.empty:
                        push_to_bq(bq, combined_shots, "shot_charts")
                print(f"✅ {game_date} done")
            else:
                print(f"⏭  {game_date} — no games, skipping")
        except Exception as e:
            print(f"❌ {game_date} — error: {e}")
        time.sleep(2)
        current += timedelta(days=1)

# ── main ──────────────────────────────────────────────────
if __name__ == "__main__":
    bq = get_bq_client()

    # step 1 — backfill 2025-26 season
    backfill_season(bq, "2025-10-22", "2026-04-13")

    # step 2 — build player info table
    build_player_info_table(bq)

    # step 3 — build team info table
    build_team_info_table(bq)

    # step 4 — build team advanced season stats
    build_team_advanced_table(bq)

    # step 5 — create all views
    create_views(bq)

    # daily update — uncomment when running daily
    # daily_update(bq)
    # daily_update(bq, "2026-04-02")