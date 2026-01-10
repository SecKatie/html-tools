#!/usr/bin/env python3
"""
Download official economic data from FRED API and build SQLite database.
Focuses on housing and job market data.
"""

import sqlite3
import urllib.request
import csv
import io
import time
from datetime import datetime
from pathlib import Path

# FRED graph data URL (downloads CSV without API key)
FRED_GRAPH_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"

# Economic series to download
# Format: (series_id, category, description)
SERIES_TO_DOWNLOAD = [
    # Housing Market Indicators
    ("MSPUS", "housing", "Median Sales Price of Houses Sold for the United States"),
    ("HOUST", "housing", "New Privately-Owned Housing Units Started"),
    ("EXHOSLUSM495S", "housing", "Existing Home Sales"),
    ("MSACSR", "housing", "Monthly Supply of Houses in the United States"),
    ("MORTGAGE30US", "housing", "30-Year Fixed Rate Mortgage Average"),
    ("CSUSHPISA", "housing", "S&P/Case-Shiller U.S. National Home Price Index"),
    ("PERMIT", "housing", "New Private Housing Units Authorized by Building Permits"),
    ("USSTHPI", "housing", "All-Transactions House Price Index for the United States"),

    # Job Market Indicators
    ("UNRATE", "jobs", "Unemployment Rate"),
    ("PAYEMS", "jobs", "All Employees, Total Nonfarm"),
    ("CIVPART", "jobs", "Labor Force Participation Rate"),
    ("ICSA", "jobs", "Initial Claims (Unemployment Insurance)"),
    ("JTSJOL", "jobs", "Job Openings: Total Nonfarm"),
    ("CES0500000003", "jobs", "Average Hourly Earnings of All Employees, Total Private"),
    ("UNEMPLOY", "jobs", "Unemployed"),
    ("EMRATIO", "jobs", "Employment-Population Ratio"),
    ("U6RATE", "jobs", "Total Unemployed, Plus All Marginally Attached Workers Plus Total Employed Part Time"),
    ("JTS1000JOL", "jobs", "Job Openings: Total Private"),
]

def create_database(db_path):
    """Create SQLite database with schema for economic data."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create series_metadata table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS series_metadata (
            series_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            units TEXT,
            frequency TEXT,
            seasonal_adjustment TEXT,
            last_updated TIMESTAMP,
            notes TEXT
        )
    """)

    # Create observations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series_id TEXT NOT NULL,
            date TEXT NOT NULL,
            value REAL,
            FOREIGN KEY (series_id) REFERENCES series_metadata(series_id),
            UNIQUE(series_id, date)
        )
    """)

    # Create indexes for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_observations_series
        ON observations(series_id)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_observations_date
        ON observations(date)
    """)

    conn.commit()
    return conn

def download_series_csv(series_id):
    """Download CSV data for a FRED series."""
    url = f"{FRED_GRAPH_BASE}?id={series_id}"

    try:
        with urllib.request.urlopen(url) as response:
            content = response.read().decode('utf-8')
            reader = csv.reader(io.StringIO(content))

            # First row is header
            header = next(reader)

            # Parse observations
            observations = []
            for row in reader:
                if len(row) >= 2:
                    date = row[0]
                    value = row[1]
                    observations.append({'date': date, 'value': value})

            return observations
    except Exception as e:
        print(f"  Error fetching CSV from {url}: {e}")
        return None

def save_series_to_db(conn, series_id, category, description):
    """Download and save a FRED series to the database."""
    cursor = conn.cursor()

    print(f"Downloading {series_id}: {description}...")

    # Download CSV data
    observations = download_series_csv(series_id)
    if not observations:
        print(f"  Failed to download data for {series_id}")
        return False

    # Save metadata
    cursor.execute("""
        INSERT OR REPLACE INTO series_metadata
        (series_id, title, category, units, frequency, seasonal_adjustment, last_updated, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        series_id,
        description,
        category,
        '',  # units not available from CSV
        '',  # frequency not available from CSV
        '',  # seasonal_adjustment not available from CSV
        datetime.now().isoformat(),
        ''   # notes not available from CSV
    ))

    # Save observations
    count = 0
    for obs in observations:
        try:
            value_str = obs['value']
            value = float(value_str) if value_str and value_str != '.' else None
            cursor.execute("""
                INSERT OR REPLACE INTO observations (series_id, date, value)
                VALUES (?, ?, ?)
            """, (series_id, obs['date'], value))
            count += 1
        except (ValueError, KeyError):
            continue

    conn.commit()
    print(f"  Saved {count} observations")

    # Be nice to the server
    time.sleep(0.3)
    return True

def generate_summary(conn):
    """Generate summary statistics about the database."""
    cursor = conn.cursor()

    print("\n" + "="*60)
    print("DATABASE SUMMARY")
    print("="*60)

    # Total series count
    cursor.execute("SELECT COUNT(*) FROM series_metadata")
    total_series = cursor.fetchone()[0]
    print(f"\nTotal series: {total_series}")

    # Series by category
    cursor.execute("""
        SELECT category, COUNT(*)
        FROM series_metadata
        GROUP BY category
    """)
    print("\nSeries by category:")
    for category, count in cursor.fetchall():
        print(f"  {category}: {count}")

    # Total observations
    cursor.execute("SELECT COUNT(*) FROM observations")
    total_obs = cursor.fetchone()[0]
    print(f"\nTotal observations: {total_obs:,}")

    # Date range
    cursor.execute("""
        SELECT MIN(date), MAX(date)
        FROM observations
        WHERE value IS NOT NULL
    """)
    min_date, max_date = cursor.fetchone()
    print(f"\nDate range: {min_date} to {max_date}")

    # Sample of latest values
    print("\nLatest values (sample):")
    cursor.execute("""
        SELECT sm.title, o.date, o.value, sm.units
        FROM observations o
        JOIN series_metadata sm ON o.series_id = sm.series_id
        WHERE o.date = (
            SELECT MAX(date)
            FROM observations o2
            WHERE o2.series_id = o.series_id AND o2.value IS NOT NULL
        )
        ORDER BY sm.category, sm.series_id
        LIMIT 10
    """)
    for title, date, value, units in cursor.fetchall():
        print(f"  {title[:50]}: {value} {units} ({date})")

    print("\n" + "="*60)

def main():
    """Main function to build the economic database."""
    db_path = Path(__file__).parent / "economic_data.db"

    print("Building Economic Data SQLite Database")
    print("="*60)
    print(f"Database: {db_path}")
    print(f"Data source: FRED (Federal Reserve Economic Data)")
    print(f"Series to download: {len(SERIES_TO_DOWNLOAD)}")
    print("="*60 + "\n")

    # Create database
    conn = create_database(db_path)

    # Download all series
    success_count = 0
    for series_id, category, description in SERIES_TO_DOWNLOAD:
        if save_series_to_db(conn, series_id, category, description):
            success_count += 1

    print(f"\n{'='*60}")
    print(f"Successfully downloaded {success_count}/{len(SERIES_TO_DOWNLOAD)} series")
    print(f"{'='*60}")

    # Generate summary
    generate_summary(conn)

    conn.close()
    print(f"\nDatabase saved to: {db_path}")

if __name__ == "__main__":
    main()
