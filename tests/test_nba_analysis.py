import pandas as pd

from src.nba_analysis import build_leaderboards, prepare_bench_rotation, select_player_season_rows


def _row(player, team, games, starts, three_pct, *, player_id=None):
    return {
        "Player": player,
        "Player-additional": player_id or player.lower(),
        "Team": team,
        "G": games,
        "GS": starts,
        "3PA": 5.0,
        "3P%": three_pct,
        "2PA": 6.0,
        "2P%": 0.55,
        "FTA": 2.5,
        "FT%": 0.80,
        "ORB": 1.0,
        "DRB": 3.0,
        "TRB": 4.0,
        "PTS": 12.0,
    }


def test_multi_team_player_uses_aggregate_row():
    frame = pd.DataFrame(
        [
            _row("Traded Player", "AAA", 20, 3, 0.30, player_id="trade01"),
            _row("Traded Player", "BBB", 30, 4, 0.40, player_id="trade01"),
            _row("Traded Player", "2TM", 50, 7, 0.36, player_id="trade01"),
            _row("Single Team", "CCC", 60, 5, 0.42, player_id="single01"),
        ]
    )

    result = select_player_season_rows(frame)

    assert len(result) == 2
    assert result.loc[result["Player-additional"].eq("trade01"), "Team"].item() == "2TM"


def test_bench_cohort_requires_40_games_and_more_bench_games_than_starts():
    frame = pd.DataFrame(
        [
            _row("Qualified", "AAA", 60, 20, 0.40),
            _row("Too Few Games", "BBB", 39, 2, 0.45),
            _row("Mostly Started", "CCC", 60, 35, 0.50),
        ]
    )

    cohort, metrics = prepare_bench_rotation(frame, min_games=40)

    assert cohort["Player"].tolist() == ["Qualified"]
    assert metrics["qualified_bench_players"] == 1


def test_three_point_board_sorts_by_percentage_then_attempts():
    frame = pd.DataFrame(
        [
            _row("A", "AAA", 60, 1, 0.40),
            _row("B", "BBB", 60, 1, 0.44),
            _row("C", "CCC", 60, 1, 0.42),
        ]
    )
    cohort, _ = prepare_bench_rotation(frame)

    board = build_leaderboards(cohort, top_n=3)["three_point"]

    assert board["Player"].tolist() == ["B", "C", "A"]
