"""Build Tableau-ready CSVs from the Open University Learning Analytics Dataset.

Usage:
    python pipeline.py                 # reads data/raw, writes data/tableau
    python pipeline.py --raw path/to/folder_or.zip

Put the OULAD download (zip or extracted CSVs) in data/raw first.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
import zipfile
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent
SQL_DIR = ROOT / "sql"

REQUIRED_FILES = [
    "courses.csv",
    "assessments.csv",
    "vle.csv",
    "studentInfo.csv",
    "studentRegistration.csv",
    "studentAssessment.csv",
    "studentVle.csv",
]

# Tables exported for Tableau, in the order the dashboards use them.
EXPORTS = [
    "fact_enrollment",
    "agg_weekly_engagement",
    "agg_withdrawal_timing",
    "agg_assessment_performance",
    "agg_equity_gaps",
    "data_quality_checks",
]


def extract_zips(folder: Path) -> None:
    """Unzip every archive in the folder, including zips nested inside zips."""
    seen: set[Path] = set()
    while True:
        zips = [z for z in folder.rglob("*.zip") if z not in seen]
        if not zips:
            return
        for z in zips:
            seen.add(z)
            with zipfile.ZipFile(z) as archive:
                archive.extractall(z.parent / z.stem)


def find_csv_folder(raw: Path) -> Path:
    """Return the folder that holds all seven OULAD CSV files."""
    if raw.is_file() and raw.suffix == ".zip":
        target = ROOT / "data" / "raw"
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy(raw, target / raw.name)
        raw = target
    extract_zips(raw)
    for candidate in [raw, *sorted(p for p in raw.rglob("*") if p.is_dir())]:
        if all((candidate / name).exists() for name in REQUIRED_FILES):
            return candidate
    missing = [n for n in REQUIRED_FILES if not any(raw.rglob(n))]
    sys.exit(f"Could not find the OULAD files in {raw}. Missing: {', '.join(missing)}")


def run_sql_file(con: duckdb.DuckDBPyConnection, path: Path, raw_dir: Path) -> None:
    sql = path.read_text().replace("{raw}", raw_dir.as_posix())
    start = time.time()
    con.execute(sql)
    print(f"  {path.name:<34} {time.time() - start:6.1f}s")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, default=ROOT / "data" / "raw")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "tableau")
    parser.add_argument("--db", type=Path, default=ROOT / "data" / "oulad.duckdb")
    args = parser.parse_args()

    raw_dir = find_csv_folder(args.raw)
    args.out.mkdir(parents=True, exist_ok=True)
    print(f"Raw files: {raw_dir}")

    con = duckdb.connect(str(args.db))
    print("Running SQL:")
    for sql_file in sorted(SQL_DIR.glob("*.sql")):
        run_sql_file(con, sql_file, raw_dir)

    print("\nExported for Tableau:")
    for table in EXPORTS:
        out_file = args.out / f"{table}.csv"
        con.execute(f"COPY {table} TO '{out_file.as_posix()}' (HEADER, DELIMITER ',')")
        rows = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {out_file.name:<34} {rows:>10,} rows")

    print("\nHeadline numbers:")
    summary = con.execute(
        """
        SELECT COUNT(*), COUNT(DISTINCT id_student),
               COUNT(DISTINCT code_module || code_presentation),
               AVG(is_pass), AVG(is_withdrawn)
        FROM fact_enrollment
        """
    ).fetchone()
    print(f"  Enrollments: {summary[0]:,}   Students: {summary[1]:,}   Course runs: {summary[2]}")
    print(f"  Pass rate: {summary[3]:.1%}   Withdrawal rate: {summary[4]:.1%}")

    print("\nData quality:")
    errors = 0
    for name, severity, failing, _ in con.execute(
        "SELECT * FROM data_quality_checks"
    ).fetchall():
        flag = "OK  " if failing == 0 else ("FAIL" if severity == "error" else "NOTE")
        errors += severity == "error" and failing > 0
        print(f"  [{flag}] {name:<46} {failing:>8,}")
    con.close()

    if errors:
        sys.exit(f"\n{errors} data quality error(s). Fix before publishing.")
    print("\nDone. Open the CSVs in data/tableau with Tableau Public.")


if __name__ == "__main__":
    main()
