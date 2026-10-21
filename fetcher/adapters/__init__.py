"""Adapter registry. Each adapter: fn(source_cfg) -> list of normalized race dicts. Add a new module and register it to swap formats."""
from . import mo_sos, stlco_csv, lvt_html, national_csv
ADAPTERS = {
    "mo_sos_enr": mo_sos.parse_enr,
    "mo_sos_pdf": mo_sos.parse_pdf,
    "stlco_csv": stlco_csv.parse,
    "lvt_html": lvt_html.parse,
    "national_csv": national_csv.parse,
}
