"""Adapter registry. Each adapter: fn(source_cfg) -> list of normalized race dicts. Add a new module and register it to swap formats."""
from . import mo_sos, stlco_csv, lvt_html, national_csv, state_feeds
ADAPTERS = {
    "mo_sos_enr": mo_sos.parse_enr,
    "mo_sos_pdf": mo_sos.parse_pdf,
    "stlco_csv": stlco_csv.parse,
    "lvt_html": lvt_html.parse,
    "national_csv": national_csv.parse,
    "nc_enr": state_feeds.nc_enr, "ga_ev": state_feeds.ga_ev, "mn_txt": state_feeds.mn_txt,
    "pa_api": state_feeds.pa_api, "clarity": state_feeds.clarity, "fl_dos": state_feeds.fl_dos, "wa_sos": state_feeds.wa_sos,
}
