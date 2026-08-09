# Data setup

The raw player table is intentionally excluded from this repository.

1. Visit the [2023–24 NBA Player Stats: Per Game](https://www.basketball-reference.com/leagues/NBA_2024_per_game.html) page.
2. Use the table's official sharing/export controls to obtain a CSV for personal use.
3. Save it locally as `data/raw/nba_2023_24_per_game.csv`.
4. Do not commit the file; `data/raw/` is ignored.

Alternatively, point the notebook to a private local `.xlsx` or `.csv` file:

```bash
export NBA_DATA_PATH="/absolute/private/path/to/file.xlsx"
```

The analysis expects the regular-season per-game columns documented in `src/nba_analysis.py`. Source data remains governed by the current Sports Reference terms. No automated scraping is part of this project.
