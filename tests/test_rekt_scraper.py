"""Tests for Rekt.news scraper."""

import json
from datetime import datetime

import httpx
import pytest
import respx

from src.models.schemas import IncidentSeverity
from src.tools.rekt_scraper import RektScraper


@pytest.fixture
def scraper():
    """Create a fresh scraper instance."""
    return RektScraper()


@pytest.fixture
def mock_leaderboard_html():
    """Mock HTML with embedded JSON data."""
    leaderboard_data = [
        {
            "protocol": "Cream Finance",
            "slug": "cream-finance",
            "amount": 130000000,
            "date": "2021-10-27T00:00:00Z",
            "title": "Cream Finance - $130M",
            "description": "Flash loan attack on lending protocol",
            "tags": ["cream", "lending"],
            "audit_status": "Audited",
            "fixed": True,
            "url": "https://rekt.news/cream-finance-rekt-2",
        },
        {
            "protocol": "Poly Network",
            "slug": "poly-network",
            "amount": 611000000,
            "date": "2021-08-10T00:00:00Z",
            "title": "Poly Network - $611M",
            "description": "Cross-chain bridge exploit",
            "tags": ["poly", "bridge"],
            "audit_status": "Unknown",
            "fixed": True,
            "url": "https://rekt.news/polynetwork-rekt",
        },
        {
            "protocol": "BadgerDAO",
            "slug": "badger-dao",
            "amount": 120000000,
            "date": "2021-12-02T00:00:00Z",
            "title": "BadgerDAO - $120M",
            "description": "Frontend injection attack",
            "tags": ["badger", "dao"],
            "audit_status": "Audited",
            "fixed": True,
            "url": "https://rekt.news/badger-rekt",
        },
    ]

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><title>Rekt Leaderboard</title></head>
    <body>
        <script>
            var leaderboard = {json.dumps(leaderboard_data)};
        </script>
    </body>
    </html>
    """
    return html


@pytest.fixture
def mock_leaderboard_table():
    """Mock HTML with table structure."""
    html = """
    <!DOCTYPE html>
    <html>
    <body>
        <table>
            <tr><th>Protocol</th><th>Amount</th><th>Date</th></tr>
            <tr>
                <td><a href="/cream-finance-rekt-2">Cream Finance</a></td>
                <td>$130M</td>
                <td>2021-10-27</td>
            </tr>
            <tr>
                <td><a href="/poly-network-rekt">Poly Network</a></td>
                <td>$611M</td>
                <td>2021-08-10</td>
            </tr>
        </table>
    </body>
    </html>
    """
    return html


@respx.mock
async def test_fetch_leaderboard_data_json(scraper, mock_leaderboard_html):
    """Test fetching leaderboard data from embedded JSON."""
    respx.get(RektScraper.LEADERBOARD_URL).mock(
        return_value=httpx.Response(200, text=mock_leaderboard_html)
    )

    data = await scraper.fetch_leaderboard_data()

    assert len(data) == 3
    assert data[0]["protocol"] == "Cream Finance"
    assert data[0]["amount"] == 130000000
    assert data[1]["protocol"] == "Poly Network"
    assert data[1]["amount"] == 611000000


@respx.mock
async def test_fetch_leaderboard_data_table(scraper, mock_leaderboard_table):
    """Test parsing leaderboard data from HTML table."""
    respx.get(RektScraper.LEADERBOARD_URL).mock(
        return_value=httpx.Response(200, text=mock_leaderboard_table)
    )

    data = await scraper.fetch_leaderboard_data()

    assert len(data) == 2
    assert data[0]["protocol"] == "Cream Finance"
    assert data[0]["amount"] == 130000000
    assert data[1]["protocol"] == "Poly Network"
    assert data[1]["amount"] == 611000000


@respx.mock
async def test_fetch_leaderboard_data_error(scraper):
    """Test handling of HTTP errors."""
    respx.get(RektScraper.LEADERBOARD_URL).mock(return_value=httpx.Response(500))

    data = await scraper.fetch_leaderboard_data()

    # Should return empty list on error
    assert data == []


@respx.mock
async def test_fetch_protocol_incidents(scraper, mock_leaderboard_html):
    """Test fetching incidents for a specific protocol."""
    respx.get(RektScraper.LEADERBOARD_URL).mock(
        return_value=httpx.Response(200, text=mock_leaderboard_html)
    )

    incidents = await scraper.fetch_protocol_incidents("cream-finance", "Cream Finance")

    assert len(incidents) == 1
    assert incidents[0].protocol_name == "Cream Finance"
    assert incidents[0].amount_lost_usd == 130000000
    assert incidents[0].severity == IncidentSeverity.CRITICAL
    assert incidents[0].title == "Cream Finance - $130M"


@respx.mock
async def test_fetch_protocol_incidents_by_name(scraper, mock_leaderboard_html):
    """Test matching by protocol name when slug doesn't match."""
    respx.get(RektScraper.LEADERBOARD_URL).mock(
        return_value=httpx.Response(200, text=mock_leaderboard_html)
    )

    incidents = await scraper.fetch_protocol_incidents("badger", "BadgerDAO")

    assert len(incidents) == 1
    assert incidents[0].protocol_name == "BadgerDAO"
    assert incidents[0].amount_lost_usd == 120000000


@respx.mock
async def test_fetch_protocol_incidents_no_match(scraper, mock_leaderboard_html):
    """Test fetching incidents when protocol has none."""
    respx.get(RektScraper.LEADERBOARD_URL).mock(
        return_value=httpx.Response(200, text=mock_leaderboard_html)
    )

    incidents = await scraper.fetch_protocol_incidents("uniswap", "Uniswap")

    assert len(incidents) == 0


def test_classify_severity_critical(scraper):
    """Test severity classification for critical incidents."""
    assert scraper._classify_severity(100_000_000) == IncidentSeverity.CRITICAL


def test_classify_severity_high(scraper):
    """Test severity classification for high severity incidents."""
    assert scraper._classify_severity(30_000_000) == IncidentSeverity.HIGH


def test_classify_severity_medium(scraper):
    """Test severity classification for medium severity incidents."""
    assert scraper._classify_severity(5_000_000) == IncidentSeverity.MEDIUM


def test_classify_severity_low(scraper):
    """Test severity classification for low severity incidents."""
    assert scraper._classify_severity(500_000) == IncidentSeverity.LOW


def test_normalize_protocol_name(scraper):
    """Test protocol name normalization."""
    assert scraper._normalize_protocol_name("Cream Finance") == "cream"
    assert scraper._normalize_protocol_name("BadgerDAO") == "badgerdao"
    assert scraper._normalize_protocol_name("Poly Network") == "poly"
    assert scraper._normalize_protocol_name("Compound V3") == "compound"
    assert scraper._normalize_protocol_name("Aave Protocol") == "aave"


def test_normalize_protocol_name_empty(scraper):
    """Test normalizing empty or None names."""
    assert scraper._normalize_protocol_name(None) == ""
    assert scraper._normalize_protocol_name("") == ""


@respx.mock
async def test_caching(scraper, mock_leaderboard_html):
    """Test that data is cached properly."""
    route = respx.get(RektScraper.LEADERBOARD_URL).mock(
        return_value=httpx.Response(200, text=mock_leaderboard_html)
    )

    # First call - should hit API
    data1 = await scraper.fetch_leaderboard_data()
    assert route.call_count == 1

    # Second call - should use cache
    data2 = await scraper.fetch_leaderboard_data()
    assert route.call_count == 1  # No additional call

    # Data should be identical
    assert data1 == data2


def test_parse_amount(scraper):
    """Test amount parsing from various formats."""
    assert scraper._parse_amount("$100M") == 100_000_000
    assert scraper._parse_amount("$1.5B") == 1_500_000_000
    assert scraper._parse_amount("$50K") == 50_000
    assert scraper._parse_amount("$10") == 10
    assert scraper._parse_amount("$120.5M") == 120_500_000
    assert scraper._parse_amount("invalid") == 0.0


def test_parse_date(scraper):
    """Test date parsing from various formats."""
    result = scraper._parse_date("2021-10-27")
    assert result is not None
    assert result.year == 2021
    assert result.month == 10
    assert result.day == 27

    result = scraper._parse_date("10/27/2021")
    assert result is not None

    result = scraper._parse_date("invalid")
    assert result is None
