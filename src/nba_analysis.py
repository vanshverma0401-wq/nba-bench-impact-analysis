"""Reusable cleaning, ranking, and visualization functions for the NBA analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

import matplotlib.pyplot as plt
import pandas as pd


REQUIRED_COLUMNS = {
    "Player",
    "Team",
    "G",
    "GS",
    "3PA",
    "3P%",
    "2PA",
    "2P%",
    "FTA",
    "FT%",
    "ORB",
    "DRB",
    "TRB",
    "PTS",
}

NUMERIC_COLUMNS = [
    "G",
    "GS",
    "MP",
    "3P",
    "3PA",
    "3P%",
    "2P",
    "2PA",
    "2P%",
    "FT",
    "FTA",
    "FT%",
    "ORB",
    "DRB",
    "TRB",
    "PTS",
]


def load_player_stats(path: str | Path) -> pd.DataFrame:
    """Load a Sports Reference CSV or the original private Excel workbook."""
    source = Path(path).expanduser()
    if not source.exists():
        raise FileNotFoundError(
            f"Data file not found: {source.name}. Follow data/README.md to obtain "
            "the source table, or set NBA_DATA_PATH to a private local copy."
        )

    if source.suffix.lower() == ".csv":
        frame = pd.read_csv(source)
    elif source.suffix.lower() in {".xlsx", ".xls"}:
        frame = pd.read_excel(source, sheet_name="PLayerstats")
    else:
        raise ValueError("Supported input formats are .csv, .xlsx, and .xls.")

    frame.columns = [str(column).strip() for column in frame.columns]
    frame = frame.loc[frame["Player"].astype(str).ne("Player")].copy()
    if "StatsType" in frame.columns:
        frame = frame.loc[frame["StatsType"].eq("Regular")].copy()

    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    for column in set(NUMERIC_COLUMNS).intersection(frame.columns):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    return frame.reset_index(drop=True)


def select_player_season_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """Return one regular-season row per player.

    Sports Reference includes both team stints and an aggregate ``2TM``/``3TM``
    row for traded players. The aggregate row is the correct season-level record.
    """
    key = "Player-additional" if "Player-additional" in frame.columns else "Player"
    selected: list[pd.Series] = []

    for player_key, group in frame.groupby(key, sort=False, dropna=False):
        if len(group) == 1:
            selected.append(group.iloc[0])
            continue

        aggregate = group.loc[
            group["Team"].astype(str).str.fullmatch(r"\d+TM", na=False)
        ]
        if len(aggregate) != 1:
            raise ValueError(
                f"Expected exactly one multi-team aggregate for {player_key!r}; "
                f"found {len(aggregate)}."
            )
        selected.append(aggregate.iloc[0])

    result = pd.DataFrame(selected).reset_index(drop=True)
    if result[key].duplicated().any():
        raise AssertionError("Player-season deduplication did not produce unique rows.")
    return result


def prepare_bench_rotation(
    frame: pd.DataFrame, *, min_games: int = 40
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Create the analysis cohort and return auditable row-count metrics."""
    season = select_player_season_rows(frame)
    season["Bench Games"] = season["G"] - season["GS"]

    invalid = season.loc[(season["G"] < season["GS"]) | (season["Bench Games"] < 0)]
    if not invalid.empty:
        raise ValueError("Found records where games started exceed games played.")

    cohort = season.loc[
        (season["G"] >= min_games) & (season["Bench Games"] > season["GS"])
    ].copy()

    metrics = {
        "source_rows": int(len(frame)),
        "unique_player_rows": int(len(season)),
        "multi_team_rows_removed": int(len(frame) - len(season)),
        "qualified_bench_players": int(len(cohort)),
        "minimum_games": int(min_games),
    }
    return cohort.reset_index(drop=True), metrics


def build_leaderboards(cohort: pd.DataFrame, *, top_n: int = 10) -> dict[str, pd.DataFrame]:
    """Build four qualified leaderboards using explicit attempt thresholds."""
    definitions = {
        "three_point": ("3PA", 4.0, "3P%"),
        "two_point": ("2PA", 5.0, "2P%"),
        "free_throw": ("FTA", 2.0, "FT%"),
    }

    boards: dict[str, pd.DataFrame] = {}
    for name, (attempts, threshold, percentage) in definitions.items():
        boards[name] = (
            cohort.loc[cohort[attempts] >= threshold]
            .sort_values([percentage, attempts], ascending=[False, False])
            .head(top_n)
            .copy()
        )

    boards["rebounding"] = (
        cohort.sort_values(["TRB", "G"], ascending=[False, False])
        .head(top_n)
        .copy()
    )
    return boards


def leaderboard_exports(boards: Mapping[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Return compact, recruiter-readable result tables."""
    columns = {
        "three_point": ["Player", "Team", "G", "GS", "3PA", "3P%", "PTS"],
        "two_point": ["Player", "Team", "G", "GS", "2PA", "2P%", "PTS"],
        "free_throw": ["Player", "Team", "G", "GS", "FTA", "FT%", "PTS"],
        "rebounding": ["Player", "Team", "G", "GS", "ORB", "DRB", "TRB", "PTS"],
    }
    return {name: board[columns[name]].reset_index(drop=True) for name, board in boards.items()}


def plot_leaderboard(
    frame: pd.DataFrame,
    *,
    value_column: str,
    title: str,
    subtitle: str,
    output_path: str | Path,
    percentage: bool = False,
) -> plt.Figure:
    """Create a consistent horizontal ranking chart and save it as a PNG."""
    chart = frame.sort_values(value_column, ascending=True)
    values = chart[value_column] * 100 if percentage else chart[value_column]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(chart["Player"], values, color="#256D85")
    ax.set_title(title, loc="left", fontsize=15, fontweight="bold", pad=22)
    ax.text(0, 1.015, subtitle, transform=ax.transAxes, fontsize=9, color="#52606D")
    ax.set_xlabel("Percentage" if percentage else "Per-game value")
    ax.grid(axis="x", alpha=0.2)
    ax.spines[["top", "right", "left"]].set_visible(False)

    labels = [f"{value:.1f}%" if percentage else f"{value:.1f}" for value in values]
    ax.bar_label(bars, labels=labels, padding=4, fontsize=9)
    ax.margins(x=0.12)
    fig.text(
        0.01,
        0.008,
        "Source: Basketball-Reference / Sports Reference LLC, 2023–24 per-game player table",
        fontsize=8,
        color="#52606D",
    )
    fig.tight_layout(rect=(0, 0.035, 1, 1))

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, dpi=180, bbox_inches="tight", facecolor="white")
    return fig
