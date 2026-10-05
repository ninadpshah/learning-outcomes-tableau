# Online Learning Outcomes: SQL + Tableau

Which online courses are working, which students are at risk of dropping out, and who is being left behind?

This project answers those questions with real, anonymized data from an online distance-learning university. Raw activity logs (10M+ rows) are cleaned and modeled in SQL with DuckDB, checked for data quality, and exported as small, Tableau-ready tables. The dashboards are published on Tableau Public.

**Dashboards:** _link coming soon_

## The questions

| Dashboard | Question it answers | Main table |
| --- | --- | --- |
| Course Outcomes Overview | Which courses have high withdrawal or low pass rates, and is it getting better or worse? | `fact_enrollment` |
| Early Warning | Can we spot students who will withdraw in their first four weeks? When do they leave? | `agg_weekly_engagement`, `agg_withdrawal_timing`, `fact_enrollment` |
| Assessment Drop-off | Which assessments are hardest, and where do students stop submitting work? | `agg_assessment_performance` |
| Equity Gaps | Which student groups pass less often than their classmates in the same course? | `agg_equity_gaps` |

## Data

[Open University Learning Analytics Dataset (OULAD)](https://archive.ics.uci.edu/dataset/349/open+university+learning+analytics+dataset), Kuzilek, Hlosta and Zdrahal, *Scientific Data* (2017). Licensed CC BY 4.0.

- About 32,600 enrollments across 7 courses and 22 course runs (2013 and 2014)
- Demographics, registration and withdrawal dates, assessment results, and daily clicks on the course website
- Each course run is identified by a module code (for example `AAA`) and a presentation code (`2013J` = October 2013 start, `2014B` = February 2014 start)
- Days are counted from the course start date, so negative days are before the course began

The raw data is not stored in this repo. See setup below.

## Setup

```bash
pip install -r requirements.txt
# Download the dataset zip from the link above and put it in data/raw/
python pipeline.py
```

The pipeline unzips the download, runs the SQL in `sql/` in order, writes CSVs to `data/tableau/`, and prints a data quality report. It also saves `data/oulad.duckdb` so you can query the tables directly.

To try it without the download, generate a small fake dataset with the same files and quirks:

```bash
python scripts/make_sample_data.py data/sample
python pipeline.py --raw data/sample --out data/sample_tableau --db data/sample.duckdb
```

## Building the dashboards

Step-by-step Tableau Public guides, written to learn each feature as you use it:

- [Dashboard 1: Course Outcomes Overview](docs/dashboard-1-course-outcomes.md)

## How the SQL is built

| File | What it does | Techniques |
| --- | --- | --- |
| `01_staging.sql` | Loads and types the 7 raw files, standardizes a mislabeled band, handles `?` as missing | Type casting, `TRY_CAST`, data cleaning |
| `02_fact_enrollment.sql` | One row per student per course run, with outcomes, early engagement and coursework measures | CTEs, `FILTER` aggregates, `ROW_NUMBER`, `NTILE`, left joins |
| `03_weekly_engagement.sql` | Weekly activity by final result, with every week present even when nobody was active | Date spine with `range()`, cross join, `COALESCE` |
| `04_withdrawal_timing.sql` | Weekly and running withdrawal rate per course run | Running totals with window frames, named `WINDOW` |
| `05_assessment_performance.sql` | Per-assessment scores, late rate, difficulty rank and submission drop-off | `MEDIAN`, `RANK`, `LAG` |
| `06_equity_gaps.sql` | Pass and withdrawal rate gaps by student group, with small groups suppressed | `UNION ALL` to long format, gap vs. baseline |
| `07_data_quality.sql` | Integrity and consistency checks run on every build | `ANTI JOIN`, duplicate detection |

## Metric definitions

| Metric | Definition |
| --- | --- |
| Pass rate | Share of enrollments with a final result of Pass or Distinction |
| Withdrawal rate | Share of enrollments with a final result of Withdrawn |
| First-attempt pass rate | Pass rate for students taking the course for the first time |
| Early engagement | Clicks on the course site in the first four weeks (days 0 to 27) |
| Early engagement quartile | Student's rank on early engagement against classmates in the same course run (1 = lowest) |
| Submitted first assessment | Whether the student turned in the first scheduled piece of coursework |
| Late submission | Submitted after the due date. Results carried over from an earlier attempt are excluded |
| Pass gap (pp) | Group pass rate minus the course run's overall pass rate, in percentage points |

## Data quality decisions

- **Final result is the source of truth.** A few students have a withdrawal date but a different final result, and some withdrawn students have no date. Rates use the final result. Timing charts use only students with a date.
- **Withdrawals before the course started** are counted, but flagged (`withdrew_before_start`) so they can be excluded when judging course design.
- **Small-cell suppression.** In the equity table, rates for groups with fewer than 10 students are blanked out so individuals cannot be identified.
- **Missing scores** are left out of averages but kept in submission counts.

## Project structure

```
pipeline.py            Runs the SQL and exports CSVs
sql/                   SQL scripts, run in numeric order
scripts/               Sample data generator for testing
docs/                  Tableau build guides
data/raw/              Downloaded dataset (not committed)
data/tableau/          Tableau-ready CSVs
```

## Tools

SQL (DuckDB), Python, Tableau Public
