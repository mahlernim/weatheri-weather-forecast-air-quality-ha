from datetime import UTC, date, datetime

import pytest
from weatheri_forecast.parser import WeatheriParseError, parse_forecast_html


def _summary_html(
    *,
    today="07월 19일 (일)",
    tomorrow="07월 20일 (월)",
    today_temps="31˚C 26˚C",
    tomorrow_temps="32˚C 27˚C",
    noise="",
):
    return f"""
    <html><head><meta charset="utf-8"></head><body>
      {noise}
      <table class="daily-summary">
        <tr><td>{today}</td><td>{tomorrow}</td></tr>
        <tr>
          <td onclick='showthree("1")'><table><tr><td>{today_temps}</td></tr></table></td>
          <td onclick='showthree("2")'><table><tr><td>{tomorrow_temps}</td></tr></table></td>
        </tr>
      </table>
      <p>부산 지역별 날씨</p>
    </body></html>
    """


NOW = datetime(2026, 7, 19, 15, 0, tzinfo=UTC)


def test_parse_valid_forecast():
    snapshot = parse_forecast_html(
        _summary_html(), location="부산", current_date=date(2026, 7, 19), fetched_at=NOW
    )
    assert snapshot.location == "부산"
    assert snapshot.source_date == date(2026, 7, 19)
    assert snapshot.today.high == 31
    assert snapshot.today.low == 26
    assert snapshot.tomorrow.high == 32
    assert snapshot.tomorrow.low == 27


def test_ignores_unrelated_tables_before_summary():
    noise = "<table><tr><td>01월 01일</td></tr></table>"
    snapshot = parse_forecast_html(
        _summary_html(noise=noise),
        location="부산",
        current_date=date(2026, 7, 19),
        fetched_at=NOW,
    )
    assert snapshot.tomorrow.date == date(2026, 7, 20)


@pytest.mark.parametrize(
    "html",
    [
        "<html><body>no forecast</body></html>",
        _summary_html(tomorrow_temps="32˚C"),
        _summary_html(today_temps="100˚C 26˚C"),
        _summary_html(today_temps="20˚C 26˚C"),
        _summary_html(tomorrow="07월 21일 (화)"),
    ],
)
def test_rejects_invalid_or_incomplete_forecast(html):
    with pytest.raises(WeatheriParseError):
        parse_forecast_html(
            html,
            location="부산",
            current_date=date(2026, 7, 19),
            fetched_at=NOW,
        )


def test_handles_year_boundary():
    snapshot = parse_forecast_html(
        _summary_html(today="12월 31일 (수)", tomorrow="01월 01일 (목)"),
        location="부산",
        current_date=date(2025, 12, 31),
        fetched_at=NOW,
    )
    assert snapshot.today.date == date(2025, 12, 31)
    assert snapshot.tomorrow.date == date(2026, 1, 1)


def test_snapshot_round_trip():
    snapshot = parse_forecast_html(
        _summary_html(), location="부산", current_date=date(2026, 7, 19), fetched_at=NOW
    )
    restored = type(snapshot).from_dict(snapshot.as_dict())
    assert restored == snapshot
