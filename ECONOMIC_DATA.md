# Economic Data SQLite Database

## Overview

This SQLite database contains official US economic data focused on housing and job markets, sourced from the Federal Reserve Economic Data (FRED) system. The data spans from 1939 to 2026 with over 15,000 observations across 18 economic series.

## Database Statistics

- **Total Series**: 18 (8 housing, 10 jobs)
- **Total Observations**: 15,224
- **Date Range**: 1939-01-01 to 2026-01-08
- **Database Size**: ~1.5 MB
- **Data Source**: Federal Reserve Economic Data (FRED)

## Schema

### `series_metadata` Table

Stores metadata about each economic series.

| Column | Type | Description |
|--------|------|-------------|
| series_id | TEXT (PK) | Unique FRED series identifier |
| title | TEXT | Full name of the economic series |
| category | TEXT | Either "housing" or "jobs" |
| units | TEXT | Units of measurement |
| frequency | TEXT | Data frequency (monthly, quarterly, etc.) |
| seasonal_adjustment | TEXT | Seasonal adjustment method |
| last_updated | TIMESTAMP | Last database update timestamp |
| notes | TEXT | Additional notes about the series |

### `observations` Table

Stores individual data points for each series.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER (PK) | Auto-incrementing primary key |
| series_id | TEXT (FK) | References series_metadata.series_id |
| date | TEXT | Observation date (YYYY-MM-DD) |
| value | REAL | Numeric value (NULL if unavailable) |

**Indexes**:
- `idx_observations_series` on series_id
- `idx_observations_date` on date
- Unique constraint on (series_id, date)

## Economic Series Included

### Housing Market (8 series)

| Series ID | Description |
|-----------|-------------|
| MSPUS | Median Sales Price of Houses Sold for the United States |
| HOUST | New Privately-Owned Housing Units Started |
| EXHOSLUSM495S | Existing Home Sales |
| MSACSR | Monthly Supply of Houses in the United States |
| MORTGAGE30US | 30-Year Fixed Rate Mortgage Average |
| CSUSHPISA | S&P/Case-Shiller U.S. National Home Price Index |
| PERMIT | New Private Housing Units Authorized by Building Permits |
| USSTHPI | All-Transactions House Price Index for the United States |

### Job Market (10 series)

| Series ID | Description |
|-----------|-------------|
| UNRATE | Unemployment Rate |
| PAYEMS | All Employees, Total Nonfarm |
| CIVPART | Labor Force Participation Rate |
| ICSA | Initial Claims (Unemployment Insurance) |
| JTSJOL | Job Openings: Total Nonfarm |
| CES0500000003 | Average Hourly Earnings of All Employees, Total Private |
| UNEMPLOY | Unemployed |
| EMRATIO | Employment-Population Ratio |
| U6RATE | Total Unemployed, Plus All Marginally Attached Workers |
| JTS1000JOL | Job Openings: Total Private |

## Usage

### Python

```python
import sqlite3

conn = sqlite3.connect('economic_data.db')
cursor = conn.cursor()

# Get unemployment rate for 2025
cursor.execute("""
    SELECT date, value
    FROM observations
    WHERE series_id = 'UNRATE'
    AND date >= '2025-01-01'
    ORDER BY date
""")

for row in cursor.fetchall():
    print(f"Date: {row[0]}, Unemployment Rate: {row[1]}%")

conn.close()
```

### Web Interface

Open `economic-data.html` in a web browser to interactively explore the data with charts and tables.

### Command Line (if sqlite3 is installed)

```bash
# List all series
sqlite3 economic_data.db "SELECT series_id, title FROM series_metadata"

# Get latest values
sqlite3 economic_data.db "
  SELECT sm.title, o.date, o.value
  FROM observations o
  JOIN series_metadata sm ON o.series_id = sm.series_id
  WHERE o.date = (
    SELECT MAX(date) FROM observations o2
    WHERE o2.series_id = o.series_id AND o2.value IS NOT NULL
  )
  ORDER BY sm.category, sm.series_id
"
```

## Updating the Database

To refresh the database with the latest data from FRED:

```bash
python3 build_economic_db.py
```

This will:
1. Download the latest data for all 18 series
2. Update the existing database (or create if missing)
3. Show a summary of the downloaded data

The script downloads data as CSV files directly from FRED, which doesn't require an API key.

## Sample Queries

### Latest unemployment rate
```sql
SELECT date, value
FROM observations
WHERE series_id = 'UNRATE'
ORDER BY date DESC
LIMIT 1;
```

### Average housing prices by year
```sql
SELECT strftime('%Y', date) as year, AVG(value) as avg_price
FROM observations
WHERE series_id = 'MSPUS'
AND value IS NOT NULL
GROUP BY year
ORDER BY year;
```

### Job openings vs unemployment correlation
```sql
SELECT
  j.date,
  j.value as job_openings,
  u.value as unemployment_rate
FROM observations j
JOIN observations u ON j.date = u.date
WHERE j.series_id = 'JTSJOL'
AND u.series_id = 'UNRATE'
AND j.date >= '2020-01-01'
ORDER BY j.date;
```

### Housing starts trend
```sql
SELECT date, value
FROM observations
WHERE series_id = 'HOUST'
AND date >= '2020-01-01'
ORDER BY date;
```

## Data Source Attribution

All data is sourced from the Federal Reserve Bank of St. Louis's FRED database:
https://fred.stlouisfed.org/

## License

The data is in the public domain. The FRED Terms of Use apply to the source data.
