## Cannibalisation Classifier with Jev
### What it does

1. **Reads your Excel file** — every tab you might have (e.g; branded, non-brand), and remembers which tab each row came from.
2. **Groups rows by search query.**
3. **Compares every pair of URLs within each query group** — asking Jev three things about each pair:
   1. Do these two pages compete for the same search?
   2. Which one should win if we had to pick one?
   3. How bad is the overlap?
4. **Runs those comparisons in parallel** (8 at a time by default).
5. **Saves everything to a CSV** — one row per URL pair, with the risk score, which page should be primary, and severity.

### What You Get — a spreadsheet flagging exactly which pages are stepping on each other's toes for the same queries.

### Input — expected columns on each sheet

| Column | Description |
|---|---|
| `query` | The search query |
| `url` | Page URL |
| `Title 1` | Page title tag |
| `Meta Description 1` | Meta description |
| `H1-1` | Page H1 |

### Output CSV columns

| Column | Type | Values |
|---|---|---|
| `query` | — | The shared search query |
| `url_a` / `url_b` | — | The two compared URLs |
| `segment_a` / `segment_b` | — | Source tab each URL came from |
| `cannibalization_probability` | `noul` | 0–1 probability |
| `primary_page` | `choice` | `page_a` / `page_b` / `unclear` |
| `severity` | `score` | `low` / `medium` / `high` |

### ⚠️ Before running

Make sure `TYPESAFE_API_KEY` is set as an environment variable in your Colab environment.
