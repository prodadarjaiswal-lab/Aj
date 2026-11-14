import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import markets as M  # noqa: E402

CSV = """SEM_EXM_EXCH_ID,SEM_SEGMENT,SEM_SMST_SECURITY_ID,SEM_INSTRUMENT_NAME,SEM_TRADING_SYMBOL,SEM_EXPIRY_DATE
MCX,M,111,FUTCOM,GOLD-05Dec2026-FUT,2026-12-05 23:30:00
MCX,M,110,FUTCOM,GOLD-05Oct2026-FUT,2026-10-05 23:30:00
MCX,M,112,FUTCOM,GOLD-05Feb2027-FUT,2027-02-05 23:30:00
MCX,M,120,FUTCOM,GOLDM-05Dec2026-FUT,2026-12-05 23:30:00
MCX,M,130,FUTCOM,CRUDEOIL-17Nov2026-FUT,2026-11-17 23:30:00
NSE,C,140,FUTCUR,USDINR-26Nov2026-FUT,2026-11-26 12:00:00
NSE,E,1,EQUITY,TCS,
"""


def test_pick_nearest_live_future():
    f = M.pick_futures(CSV, dt.date(2026, 11, 14))
    assert f["GOLD"][1] == "111" and f["CRUDEOIL"][0] == "MCX_COMM" and f["USDINR"][:2] == ("NSE_CURRENCY", "140")
    assert "GOLDM" not in f and "SILVER" not in f


def test_headlines_found_in_any_shape():
    reply = {"status": "success", "data": {"news": [{"title": "Gold jumps", "publishedAt": "2026-11-13T10:00:00", "source": "X"},
                                                     {"headline": "Rupee slips", "time": "2026-11-13"}, {"title": "Gold jumps"}]}}
    hs = M._headlines(reply)
    assert [h["title"] for h in hs] == ["Gold jumps", "Rupee slips"] and hs[0]["source"] == "X"
