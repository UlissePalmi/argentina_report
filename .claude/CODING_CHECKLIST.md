# Coding Checklist

## When adding a new data series
1. Add fetch function to the appropriate module in `ingestion/`
2. Add series ID and endpoint to `DATA_SOURCES.md`
3. Add cleaning/deflation logic inside that same ingestion module
4. Add the derived metric to the relevant `signals/*.py`
5. Update the relevant `SKILLS/*.md` if interpretation changes
6. Test that `main.py` still runs end to end

## When adding a new analytical section
1. Decide which layer it belongs to
2. If it needs new data → ingestion module first
3. If it needs new derived metrics → signals layer
4. If it needs new interpretation rules → SKILLS/
5. Add renderer to `sections/<domain>/section.py`
6. Wire into `report/build.py`

## Error handling
```python
def fetch_with_fallback(primary_fn, fallback_fn, series_name):
    try:
        data = primary_fn()
        return data
    except Exception as e:
        log(f"WARNING: {series_name} primary failed: {e}")
        try:
            return fallback_fn()
        except Exception as e2:
            log(f"CRITICAL: {series_name} both sources failed")
            return None  # never crash — continue with partial data
```

## Never
- Let the LLM compute percentages or do arithmetic
- Use constant-price shares as the primary composition view
- Use simple subtraction instead of Fisher equation for deflation
- Hardcode dates — always use `datetime.now()` or latest available
- Crash on missing data — always degrade gracefully
- Use `api.bcra.gob.ar/estadisticas` — fully deprecated

## Always
- Cache raw data in `cache/`
- Validate that GDP components sum correctly (within 2%)
- Label whether a series is real or nominal in output files
- Include the data source and series code in every output CSV
- Run a sum check on GDP composition before reporting shares
