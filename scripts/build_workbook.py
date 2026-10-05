"""Build a packaged Tableau workbook (.twbx) from the Tableau-ready CSVs.

Usage:
    python scripts/build_workbook.py                       # reads data/tableau
    python scripts/build_workbook.py --csv path/to/csvs --out workbook.twbx

The workbook connects all six CSVs, sets field roles, and contains Dashboard 1
(Course Outcomes Overview) built as described in docs/dashboard-1-course-outcomes.md.
Open it in Tableau Public with File > Open.
"""

from __future__ import annotations

import argparse
import hashlib
import uuid
import zipfile
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
WORKBOOK_NAME = "Online Learning Outcomes"
DATA_DIR = "Data/tableau"  # folder inside the .twbx

TABLES = [
    "fact_enrollment",
    "agg_weekly_engagement",
    "agg_withdrawal_timing",
    "agg_assessment_performance",
    "agg_equity_gaps",
    "data_quality_checks",
]

# Numbers that are labels, not quantities to add up.
NUMERIC_DIMENSIONS = {
    "fact_enrollment": ["id_student", "start_year", "early_engagement_quartile"],
    "agg_weekly_engagement": ["week"],
    "agg_withdrawal_timing": ["week"],
    "agg_assessment_performance": ["id_assessment", "assessment_order"],
}

# (remote type code, Tableau datatype, default aggregation)
TYPES = {
    "VARCHAR": (129, "string", "Count"),
    "BIGINT": (20, "integer", "Sum"),
    "DOUBLE": (5, "real", "Sum"),
    "BOOLEAN": (11, "boolean", "Count"),
}

# Dashboard 1 calculated fields: id -> (caption, datatype, format, formula)
PARAM = "[Parameters].[Parameter 1]"
CALCS = {
    "Calculation_enrollments": ("Enrollments", "integer", "n#,##0", "COUNT([id_student])"),
    "Calculation_pass_rate": ("Pass Rate", "real", "p0.0%", "AVG([is_pass])"),
    "Calculation_withdrawal_rate": ("Withdrawal Rate", "real", "p0.0%", "AVG([is_withdrawn])"),
    "Calculation_distinction_rate": ("Distinction Rate", "real", "p0.0%", "AVG([is_distinction])"),
    "Calculation_first_attempt_pass": (
        "First-Attempt Pass Rate", "real", "p0.0%",
        "AVG(IF [is_first_attempt] THEN [is_pass] END)",
    ),
    "Calculation_selected_metric": (
        "Selected Metric", "real", "p0.0%",
        f"CASE {PARAM}\n"
        "  WHEN 'Pass Rate' THEN [Calculation_pass_rate]\n"
        "  WHEN 'Withdrawal Rate' THEN [Calculation_withdrawal_rate]\n"
        "  WHEN 'Distinction Rate' THEN [Calculation_distinction_rate]\n"
        "END",
    ),
}
CALC_DEPENDS = {
    "Calculation_enrollments": ["id_student"],
    "Calculation_pass_rate": ["is_pass"],
    "Calculation_withdrawal_rate": ["is_withdrawn"],
    "Calculation_distinction_rate": ["is_distinction"],
    "Calculation_first_attempt_pass": ["is_first_attempt", "is_pass"],
    "Calculation_selected_metric": [
        "Calculation_pass_rate", "Calculation_withdrawal_rate", "Calculation_distinction_rate",
    ],
}
METRICS = ["Pass Rate", "Withdrawal Rate", "Distinction Rate"]

KPIS = [
    ("KPI Enrollments", "Calculation_enrollments", "Enrollments"),
    ("KPI Pass Rate", "Calculation_pass_rate", "Pass rate"),
    ("KPI Withdrawal Rate", "Calculation_withdrawal_rate", "Withdrawal rate"),
    ("KPI Distinction Rate", "Calculation_distinction_rate", "Distinction rate"),
    ("KPI First-Attempt Pass", "Calculation_first_attempt_pass", "First-attempt pass rate"),
]
DASHBOARD = "Course Outcomes"


def esc(value: str) -> str:
    return (
        value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;").replace("\n", "&#10;")
    )


def attrs(**kwargs: object) -> str:
    return " ".join(f'{k.rstrip("_").replace("__", ":").replace("_", "-")}="{esc(str(v))}"'
                    for k, v in kwargs.items())


def ds_name(table: str) -> str:
    digest = hashlib.sha1(table.encode()).hexdigest()[:28]
    return f"federated.{digest}"


def new_uuid(seed: str) -> str:
    return "{" + str(uuid.uuid5(uuid.NAMESPACE_URL, seed)).upper() + "}"


def read_schema(csv: Path) -> list[tuple[str, str]]:
    rows = duckdb.sql(f"DESCRIBE SELECT * FROM read_csv_auto('{csv.as_posix()}')").fetchall()
    return [(r[0], r[1]) for r in rows]


def base_column_xml(name: str, duck_type: str, table: str) -> str:
    _, datatype, _ = TYPES[duck_type]
    if name in NUMERIC_DIMENSIONS.get(table, []):
        return f'<column {attrs(datatype=datatype, name=f"[{name}]", role="dimension", type="ordinal")} />'
    if datatype in ("string", "boolean"):
        return f'<column {attrs(datatype=datatype, name=f"[{name}]", role="dimension", type="nominal")} />'
    return f'<column {attrs(datatype=datatype, name=f"[{name}]", role="measure", type="quantitative")} />'


def calc_column_xml(calc_id: str) -> str:
    caption, datatype, fmt, formula = CALCS[calc_id]
    return (
        f'<column {attrs(caption=caption, datatype=datatype, default_format=fmt, name=f"[{calc_id}]", role="measure", type="quantitative")}>'
        f'<calculation {attrs(class_="tableau", formula=formula)} /></column>'
    )


def parameter_column_xml() -> str:
    members = "".join(f'<member {attrs(value=f"{chr(34)}{m}{chr(34)}")} />' for m in METRICS)
    default = '"Withdrawal Rate"'
    return (
        f'<column {attrs(caption="Choose Metric", datatype="string", name="[Parameter 1]", param_domain_type="list", role="measure", type="nominal", value=default)}>'
        f'<calculation {attrs(class_="tableau", formula=default)} />'
        f"<members>{members}</members></column>"
    )


def datasource_xml(table: str, schema: list[tuple[str, str]]) -> str:
    name = ds_name(table)
    conn = f"textscan.{name.split('.')[1]}"
    csv = f"{table}.csv"
    rel_cols = "".join(
        f'<column {attrs(datatype=TYPES[t][1], name=c, ordinal=i)} />' for i, (c, t) in enumerate(schema)
    )
    records = "".join(
        "<metadata-record class=\"column\">"
        f"<remote-name>{esc(c)}</remote-name><remote-type>{TYPES[t][0]}</remote-type>"
        f"<local-name>[{esc(c)}]</local-name><parent-name>[{csv}]</parent-name>"
        f"<remote-alias>{esc(c)}</remote-alias><ordinal>{i}</ordinal>"
        f"<local-type>{TYPES[t][1]}</local-type><aggregation>{TYPES[t][2]}</aggregation>"
        "<contains-null>true</contains-null></metadata-record>"
        for i, (c, t) in enumerate(schema)
    )
    columns = "".join(base_column_xml(c, t, table) for c, t in schema)
    if table == "fact_enrollment":
        columns += "".join(calc_column_xml(c) for c in CALCS)
    return (
        f'<datasource {attrs(caption=table, inline="true", name=name, version="18.1")}>'
        '<connection class="federated"><named-connections>'
        f'<named-connection {attrs(caption=table, name=conn)}>'
        f'<connection {attrs(class_="textscan", directory=DATA_DIR, filename=csv, password="", server="")} />'
        "</named-connection></named-connections>"
        f'<relation {attrs(connection=conn, name=csv, table=f"[{table}#csv]", type="table")}>'
        f'<columns {attrs(character_set="UTF-8", header="yes", locale="en_US", separator=",")}>{rel_cols}</columns>'
        f"</relation><metadata-records>{records}</metadata-records></connection>"
        '<aliases enabled="yes" />'
        f"{columns}</datasource>"
    )


class Sheet:
    """Collects what one worksheet uses from fact_enrollment."""

    def __init__(self, schema: dict[str, str]):
        self.schema = schema
        self.ds = ds_name("fact_enrollment")
        self.columns: list[str] = []
        self.instances: list[str] = []
        self.uses_param = False

    def _need(self, col: str) -> None:
        if col in self.columns:
            return
        for dep in CALC_DEPENDS.get(col, []):
            self._need(dep)
        if col == "Calculation_selected_metric":
            self.uses_param = True
        self.columns.append(col)

    def dim(self, col: str) -> str:
        self._need(col)
        inst = f"[none:{col}:nk]"
        xml = f'<column-instance {attrs(column=f"[{col}]", derivation="None", name=inst, pivot="key", type="nominal")} />'
        if xml not in self.instances:
            self.instances.append(xml)
        return f"[{self.ds}].{inst}"

    def measure(self, calc_id: str) -> str:
        self._need(calc_id)
        inst = f"[usr:{calc_id}:qk]"
        xml = f'<column-instance {attrs(column=f"[{calc_id}]", derivation="User", name=inst, pivot="key", type="quantitative")} />'
        if xml not in self.instances:
            self.instances.append(xml)
        return f"[{self.ds}].{inst}"

    def view_xml(self) -> str:
        """The <view> block: data sources, dependencies, and the pre-start filter."""
        flt = self.dim("withdrew_before_start")
        cols = "".join(
            calc_column_xml(c) if c in CALCS else base_column_xml(c, self.schema[c], "fact_enrollment")
            for c in self.columns
        )
        param_ds = '<datasource name="Parameters" />' if self.uses_param else ""
        param_deps = (
            f'<datasource-dependencies datasource="Parameters">{parameter_column_xml()}</datasource-dependencies>'
            if self.uses_param else ""
        )
        level = "[none:withdrew_before_start:nk]"
        return (
            "<view><datasources>"
            f'<datasource {attrs(caption="fact_enrollment", name=self.ds)} />{param_ds}'
            f"</datasources>{param_deps}"
            f'<datasource-dependencies {attrs(datasource=self.ds)}>{cols}{"".join(self.instances)}</datasource-dependencies>'
            f'<filter {attrs(class_="categorical", column=flt)}>'
            f'<groupfilter {attrs(function="except", user__ui_domain="database", user__ui_enumeration="exclusive", user__ui_marker="enumerate")}>'
            f'<groupfilter {attrs(function="level-members", level=level)} />'
            f'<groupfilter {attrs(function="member", level=level, member="true")} />'
            "</groupfilter></filter>"
            f"<slices><column>{esc(flt)}</column></slices>"
            '<aggregation value="true" /></view>'
        )


def worksheet_xml(name: str, sheet: Sheet, pane: str, rows: str, cols: str) -> str:
    view = sheet.view_xml()
    return (
        f'<worksheet {attrs(name=name)}><table>{view}<style />'
        f'<panes><pane selection-relaxation-option="selection-relaxation-allow">'
        f'<view><breakdown value="auto" /></view>{pane}</pane></panes>'
        f"<rows>{esc(rows)}</rows><cols>{esc(cols)}</cols></table>"
        f'<simple-id uuid="{new_uuid(name)}" /></worksheet>'
    )


def kpi_sheet(name: str, calc_id: str, label: str, schema: dict[str, str]) -> str:
    s = Sheet(schema)
    m = s.measure(calc_id)
    pane = (
        '<mark class="Text" />'
        f'<encodings><text {attrs(column=m)} /></encodings>'
        "<customized-label><formatted-text>"
        f'<run {attrs(fontcolor="#666666", fontsize="11")}>{esc(label)}</run>'
        "<run>Æ&#10;</run>"
        f'<run {attrs(bold="true", fontsize="28")}>{esc("<" + m + ">")}</run>'
        "</formatted-text></customized-label>"
    )
    return worksheet_xml(name, s, pane, "", "")


def matrix_sheet(schema: dict[str, str]) -> str:
    s = Sheet(schema)
    rows, cols = s.dim("code_module"), s.dim("code_presentation")
    metric = s.measure("Calculation_selected_metric")
    size = s.measure("Calculation_enrollments")
    pane = (
        '<mark class="Square" />'
        f'<encodings><color {attrs(column=metric)} /><text {attrs(column=metric)} />'
        f'<tooltip {attrs(column=size)} /></encodings>'
    )
    return worksheet_xml("Course Matrix", s, pane, rows, cols)


def trend_sheet(schema: dict[str, str]) -> str:
    s = Sheet(schema)
    cols = s.dim("code_presentation")
    rows = s.measure("Calculation_selected_metric")
    color = s.dim("code_module")
    pane = f'<mark class="Line" /><encodings><color {attrs(column=color)} /></encodings>'
    return worksheet_xml("Trend", s, pane, rows, cols)


def zone(zid: int, x: int, y: int, w: int, h: int, **extra: object) -> str:
    return f'<zone {attrs(h=h, id=zid, w=w, x=x, y=y, **extra)} />'


def dashboard_xml() -> str:
    # Coordinates are in 1/100000ths of the dashboard (1200 x 800 px).
    kpi_w = 20000
    kpis = "".join(
        zone(10 + i, i * kpi_w, 8000, kpi_w, 16000, name=sheet) for i, (sheet, _, _) in enumerate(KPIS)
    )
    title = (
        '<zone h="8000" id="3" type="text" w="100000" x="0" y="0"><formatted-text>'
        '<run bold="true" fontsize="18">Course Outcomes Overview</run><run>Æ&#10;</run>'
        '<run fontcolor="#666666" fontsize="10">Open University, 2013 to 2014. Pick a metric to see '
        "which courses need attention. Excludes students who withdrew before the course started.</run>"
        "</formatted-text></zone>"
    )
    legend_field = f"[{ds_name('fact_enrollment')}].[none:code_module:nk]"
    return (
        f'<dashboards><dashboard {attrs(name=DASHBOARD)}><style />'
        '<size maxheight="800" maxwidth="1200" minheight="800" minwidth="1200" />'
        '<zones><zone h="100000" id="1" type="layout-basic" w="100000" x="0" y="0">'
        '<zone h="100000" id="2" param="vert" type="layout-flow" w="100000" x="0" y="0">'
        f"{title}"
        f'<zone h="16000" id="4" param="horz" type="layout-flow" w="100000" x="0" y="8000">{kpis}</zone>'
        '<zone h="76000" id="5" param="horz" type="layout-flow" w="100000" x="0" y="24000">'
        + zone(20, 0, 24000, 50000, 76000, name="Course Matrix")
        + zone(21, 50000, 24000, 32000, 76000, name="Trend")
        + '<zone h="76000" id="6" param="vert" type="layout-flow" w="18000" x="82000" y="24000">'
        + zone(22, 82000, 24000, 18000, 10000, mode="compact", param=PARAM, type="paramctrl")
        + zone(23, 82000, 34000, 18000, 66000, name="Trend", param=legend_field, type="color")
        + "</zone></zone></zone></zone></zones>"
        f'<simple-id uuid="{new_uuid(DASHBOARD)}" /></dashboard></dashboards>'
    )


def windows_xml(sheets: list[str]) -> str:
    cards = (
        '<cards><edge name="left"><strip size="160"><card type="pages" /><card type="filters" />'
        '<card type="marks" /></strip></edge><edge name="top"><strip size="2147483647">'
        '<card type="columns" /></strip><strip size="2147483647"><card type="rows" /></strip>'
        '<strip size="31"><card type="title" /></strip></edge></cards>'
    )
    out = "".join(
        f'<window {attrs(class_="worksheet", name=s)}>{cards}<simple-id uuid="{new_uuid("w" + s)}" /></window>'
        for s in sheets
    )
    viewpoints = "".join(f'<viewpoint {attrs(name=s)} />' for s in sheets)
    out += (
        f'<window {attrs(class_="dashboard", maximized="true", name=DASHBOARD)}>'
        f'<viewpoints>{viewpoints}</viewpoints><active id="-1" />'
        f'<simple-id uuid="{new_uuid("w" + DASHBOARD)}" /></window>'
    )
    return f'<windows source-height="30">{out}</windows>'


def build_twb(csv_dir: Path) -> str:
    schemas = {t: read_schema(csv_dir / f"{t}.csv") for t in TABLES}
    fact = dict(schemas["fact_enrollment"])
    datasources = (
        '<datasource hasconnection="false" inline="true" name="Parameters" version="18.1">'
        f'<aliases enabled="yes" />{parameter_column_xml()}</datasource>'
        + "".join(datasource_xml(t, schemas[t]) for t in TABLES)
    )
    worksheets = [kpi_sheet(n, c, label, fact) for n, c, label in KPIS]
    worksheets += [matrix_sheet(fact), trend_sheet(fact)]
    sheet_names = [n for n, _, _ in KPIS] + ["Course Matrix", "Trend"]
    return (
        "<?xml version='1.0' encoding='utf-8' ?>\n"
        '<workbook original-version="18.1" source-build="2020.2.0 (20202.20.0525.1210)" '
        'source-platform="win" version="18.1" xmlns:user="http://www.tableausoftware.com/xml/user">'
        f"<datasources>{datasources}</datasources>"
        f'<worksheets>{"".join(worksheets)}</worksheets>'
        f"{dashboard_xml()}{windows_xml(sheet_names)}</workbook>\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--csv", type=Path, default=ROOT / "data" / "tableau")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / f"{WORKBOOK_NAME}.twbx")
    args = parser.parse_args()

    twb = build_twb(args.csv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as twbx:
        twbx.writestr(f"{WORKBOOK_NAME}.twb", twb)
        for table in TABLES:
            twbx.write(args.csv / f"{table}.csv", f"{DATA_DIR}/{table}.csv")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
