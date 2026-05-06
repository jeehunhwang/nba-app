import pickle
import pandas as pd
from google.cloud import bigquery
from nba_api.stats.endpoints import leaguestandingsv3

PROJECT_ID = "nba-dashboard-495409"
DATASET = "nba_stats"

def get_bq_client():
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
    return bigquery.Client(project=PROJECT_ID, credentials=creds)

def fetch_standings(season="2025-26"):
    standings = leaguestandingsv3.LeagueStandingsV3(season=season)
    df = standings.standings.get_data_frame()
    print(df.columns.tolist())
    print(df.head(2))
    return df

def clean_standings(df):
    cols = [
        "TeamID", "TeamCity", "TeamName", "TeamSlug",
        "Conference", "ConferenceRecord", "PlayoffRank",
        "ClinchIndicator", "Division", "DivisionRecord",
        "DivisionRank", "WinPCT", "LeagueRank", "Record",
        "Home", "Road", "L10", "Last10Home", "Last10Road",
        "OT", "ThreePTSOrLess", "TenPTSOrMore", "LongHomeStreak",
        "LongRoadStreak", "LongWinStreak", "LongLossStreak",
        "CurrentHomeStreak", "CurrentRoadStreak", "CurrentStreak",
        "ConferenceGamesBack", "DivisionGamesBack", "ClinchedConferenceTitle",
        "ClinchedDivisionTitle", "ClinchedPlayoffBirth", "EliminatedConference",
        "Points", "OppPoints", "DiffPoints"
    ]
    # only keep columns that exist
    available = [c for c in cols if c in df.columns]
    df = df[available].copy()
    df.columns = [c.lower() for c in df.columns]
    df["season"] = "2025-26"
    return df

def push_standings(bq, df):
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        autodetect=True
    )
    bq.load_table_from_dataframe(
        df,
        f"{PROJECT_ID}.{DATASET}.league_standings",
        job_config=job_config
    ).result()
    print(f"✅ league_standings table created with {len(df)} rows")

if __name__ == "__main__":
    bq = get_bq_client()
    df = fetch_standings("2025-26")
    cleaned = clean_standings(df)
    push_standings(bq, cleaned)