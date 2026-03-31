# CLAUDE.md — Instructions for Claude Code

## Before ANY Work

1. **READ `CONTEXT.md` FIRST.** Always. Every session. No exceptions.
2. Check the `## Execution Status` section to understand what's been completed.
3. Identify which phase you're working on.
4. Read the phase-specific tasks carefully.

## After Completing Work

1. **REWRITE `CONTEXT.md`** — update the Execution Status, Discovered Facts, Key Decisions, and Deviations sections with everything you learned or changed.
2. This is critical: if the context window resets, the next session MUST be able to pick up exactly where you left off by reading CONTEXT.md alone.

## Code Standards

- **Python 3.11+**, type hints on all function signatures
- **Polars** for DataFrames, never pandas
- **DuckDB** for complex SQL aggregations over parquet
- **Logging** via `logging` module, never `print()` in library code
- **Ruff** for linting (line length 100)
- **Google-style docstrings** on all public functions
- **Constants** in `src/config.py`, never hardcoded paths or magic numbers
- **No notebooks** — all logic in `.py` files

## Testing

- Write tests as you build, not after
- Use `pytest` with descriptive test names: `test_bronze_events_row_count_matches_expected`
- At minimum: test row counts, null rates, schema compliance, business logic correctness
- Tests must be runnable independently with `pytest tests/`

## Data Handling

- Never commit data files to git (add to `.gitignore`)
- All parquet files go in `data/{bronze,silver,gold}/`
- Use Polars `scan_parquet` (lazy) when possible for memory efficiency
- Log row counts and schema at every layer transition

## Git Practices

- Meaningful commit messages: `feat(ingestion): parse XES to bronze parquet`
- One commit per logical unit of work
- Never commit broken code

## Common Pitfalls to Avoid

- Don't invent dataset attributes — inspect the actual XES file
- Don't build the frontend before the gold layer is solid
- Don't skip quality validation to move faster
- Don't use pm4py for everything — use it for XES parsing, but do analytics with Polars/DuckDB
- Don't make the predictive layer the star — it's a supporting module
- Don't create notebooks — create scripts and modules

## Dataset Location

The BPI Challenge 2019 XES file should be placed at:
```
data/raw/BPI_Challenge_2019.xes
```

If the file is not present, inform the user and stop.

## Key Dependencies

```
polars >= 1.0
duckdb >= 0.10
pandera[polars] >= 0.20
pm4py >= 2.7
scikit-learn >= 1.4
lightgbm >= 4.0
pytest >= 8.0
ruff >= 0.4
```

## Frontend Stack

```
react >= 18
typescript >= 5
tailwindcss >= 3
echarts >= 5
echarts-for-react >= 3
vite >= 5
react-router-dom >= 6
```
