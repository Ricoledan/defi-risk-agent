"""Rekt.news incident data scraper."""

import json
import re
from datetime import datetime, timedelta
from typing import Any

import httpx
from bs4 import BeautifulSoup

from src.models.schemas import ExploitIncident, IncidentSeverity


class RektScraper:
    """Scraper for Rekt.news leaderboard data."""

    LEADERBOARD_URL = "https://rekt.news/leaderboard/"
    CACHE_TTL = timedelta(hours=24)

    def __init__(self) -> None:
        """Initialize scraper with cache."""
        self._cache: dict[str, Any] = {}
        self._cache_time: datetime | None = None

    async def fetch_leaderboard_data(self) -> list[dict[str, Any]]:
        """
        Fetch and parse Rekt.news leaderboard data.

        Returns:
            List of incident dictionaries with title, date, amount, tags, etc.
        """
        # Check cache
        if self._cache_time and datetime.utcnow() - self._cache_time < self.CACHE_TTL:
            return self._cache.get("leaderboard_data", [])

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(self.LEADERBOARD_URL)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")

                # Look for embedded JSON data in script tags
                incidents = []
                for script in soup.find_all("script"):
                    if script.string and "leaderboard" in script.string.lower():
                        # Try to extract JSON data
                        try:
                            # Look for patterns like: var leaderboard = [...];
                            json_match = re.search(
                                r'(?:var|let|const)?\s*(?:leaderboard|data)\s*=\s*(\[.*?\]);',
                                script.string,
                                re.DOTALL | re.IGNORECASE,
                            )
                            if json_match:
                                data = json.loads(json_match.group(1))
                                if isinstance(data, list):
                                    incidents = data
                                    break
                        except (json.JSONDecodeError, AttributeError):
                            continue

                # If no JSON found, try parsing HTML table
                if not incidents:
                    incidents = self._parse_leaderboard_table(soup)

                # Cache results
                self._cache["leaderboard_data"] = incidents
                self._cache_time = datetime.utcnow()

                return incidents

        except Exception as e:
            # Log error but don't fail - return empty list
            print(f"Error fetching Rekt.news data: {e}")
            return []

    def _parse_leaderboard_table(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """
        Parse leaderboard data from HTML structure.

        Args:
            soup: BeautifulSoup object of the page

        Returns:
            List of incident dictionaries
        """
        incidents = []

        # Look for leaderboard div with rows
        leaderboard = soup.find("div", class_="leaderboard")
        if not leaderboard:
            # Fallback to generic table structure
            return self._parse_generic_table(soup)

        # Find all leaderboard rows
        rows = leaderboard.find_all("div", class_="leaderboard-row")

        for row in rows:
            try:
                # Get title and link
                title_div = row.find("div", class_="leaderboard-row-title")
                if not title_div:
                    continue

                link = title_div.find("a")
                if not link:
                    continue

                # Extract protocol name
                protocol = link.get_text(strip=True)
                # Remove audit status from name
                audit_span = link.find("span", class_="leaderboard-audit")
                if audit_span:
                    audit_status = audit_span.get_text(strip=True)
                    protocol = protocol.replace(audit_status, "").strip()
                else:
                    audit_status = None

                # Get URL and slug
                url = link.get("href", "")
                if url and not url.startswith("http"):
                    url = f"https://rekt.news{url}"

                slug = None
                if url:
                    slug_match = re.search(r'/([^/]+)/?$', url)
                    if slug_match:
                        slug = slug_match.group(1)

                # Get details (amount and date)
                details_div = row.find("div", class_="leaderboard-row-details")
                if details_div:
                    details_text = details_div.get_text(strip=True)
                    # Format: $14,847,374,246|12/20/2020
                    parts = details_text.split("|")
                    amount_text = parts[0].strip() if parts else "0"
                    date_text = parts[1].strip() if len(parts) > 1 else ""

                    amount = self._parse_amount(amount_text)
                    date = self._parse_date(date_text)
                else:
                    amount = 0.0
                    date = None

                incidents.append({
                    "protocol": protocol,
                    "amount": amount,
                    "date": date.isoformat() if date else None,
                    "url": url,
                    "slug": slug,
                    "title": f"{protocol} - ${amount / 1e6:.1f}M" if amount > 0 else protocol,
                    "audit_status": audit_status,
                })

            except Exception as e:
                # Log but continue
                continue

        return incidents

    def _parse_generic_table(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Fallback parser for generic table structure."""
        incidents = []
        table = soup.find("table")
        if not table:
            return incidents

        rows = table.find_all("tr")[1:]  # Skip header
        for row in rows:
            try:
                cells = row.find_all("td")
                if len(cells) >= 3:
                    protocol = cells[0].get_text(strip=True)
                    amount_text = cells[1].get_text(strip=True)
                    date_text = cells[2].get_text(strip=True)

                    amount = self._parse_amount(amount_text)
                    date = self._parse_date(date_text)

                    link = row.find("a")
                    url = link["href"] if link and "href" in link.attrs else None
                    if url and not url.startswith("http"):
                        url = f"https://rekt.news{url}"

                    slug = None
                    if url:
                        slug_match = re.search(r'/([^/]+)/?$', url)
                        if slug_match:
                            slug = slug_match.group(1)

                    incidents.append({
                        "protocol": protocol,
                        "amount": amount,
                        "date": date.isoformat() if date else None,
                        "url": url,
                        "slug": slug,
                        "title": f"{protocol} - ${amount / 1e6:.1f}M",
                    })
            except Exception:
                continue

        return incidents

    def _parse_amount(self, amount_text: str) -> float:
        """Parse amount string to USD value."""
        # Remove currency symbols and whitespace
        amount_text = re.sub(r'[$,\s]', '', amount_text.upper())

        # Extract number and multiplier
        match = re.search(r'([\d.]+)([KMB])?', amount_text)
        if not match:
            return 0.0

        number = float(match.group(1))
        multiplier = match.group(2)

        if multiplier == 'K':
            return number * 1_000
        elif multiplier == 'M':
            return number * 1_000_000
        elif multiplier == 'B':
            return number * 1_000_000_000

        return number

    def _parse_date(self, date_text: str) -> datetime | None:
        """Parse date string to datetime."""
        try:
            # Try common date formats
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%B %d, %Y", "%d %B %Y"]:
                try:
                    return datetime.strptime(date_text.strip(), fmt)
                except ValueError:
                    continue

            # Try parsing with dateutil if available
            try:
                from dateutil import parser
                return parser.parse(date_text)
            except (ImportError, ValueError):
                pass

        except Exception:
            pass

        return None

    async def fetch_protocol_incidents(
        self,
        slug: str,
        protocol_name: str | None = None,
    ) -> list[ExploitIncident]:
        """
        Fetch incidents for a specific protocol.

        Args:
            slug: Protocol slug (e.g., "cream-finance")
            protocol_name: Optional protocol name for matching

        Returns:
            List of ExploitIncident objects for this protocol
        """
        leaderboard_data = await self.fetch_leaderboard_data()

        if not leaderboard_data:
            return []

        # Normalize search terms
        normalized_slug = self._normalize_protocol_name(slug)
        normalized_name = self._normalize_protocol_name(protocol_name) if protocol_name else None

        incidents = []
        for item in leaderboard_data:
            # Match by slug, protocol name, or tags
            item_protocol = self._normalize_protocol_name(item.get("protocol", ""))
            item_slug = self._normalize_protocol_name(item.get("slug", ""))
            item_tags = [self._normalize_protocol_name(tag) for tag in item.get("tags", [])]

            # Check for exact matches first
            exact_match = (
                item_slug == normalized_slug
                or item_protocol == normalized_slug
                or (normalized_name and item_protocol == normalized_name)
            )

            # Check for partial matches (e.g., "cream" in "cream-rekt")
            partial_match = False
            if not exact_match and normalized_slug:
                # Extract base name (before hyphen)
                base_slug = normalized_slug.split('-')[0]
                base_item_slug = item_slug.split('-')[0] if item_slug else ""

                # Match if base names match or if one contains the other
                if (
                    base_slug and base_item_slug and
                    (base_slug in item_slug or item_slug.startswith(base_slug) or
                     base_slug in item_protocol or item_protocol.startswith(base_slug))
                ):
                    partial_match = True

            # Check tags
            tag_match = (
                normalized_slug in item_tags or
                (normalized_name and normalized_name in item_tags)
            )

            if exact_match or partial_match or tag_match:
                # Create ExploitIncident
                amount = float(item.get("amount", 0))
                date_str = item.get("date")
                date = datetime.fromisoformat(date_str) if date_str else datetime.utcnow()

                incident = ExploitIncident(
                    protocol_name=item.get("protocol", protocol_name or slug),
                    date=date,
                    amount_lost_usd=amount,
                    severity=self._classify_severity(amount),
                    title=item.get("title", f"Security Incident - ${amount / 1e6:.1f}M"),
                    description=item.get("description"),
                    tags=item.get("tags", []),
                    audit_status=item.get("audit_status"),
                    fixed=item.get("fixed", False),
                    details_url=item.get("url"),
                    slug=item.get("slug"),
                )
                incidents.append(incident)

        # Sort by date (most recent first)
        incidents.sort(key=lambda x: x.date, reverse=True)

        return incidents

    def _classify_severity(self, amount_usd: float) -> IncidentSeverity:
        """
        Classify incident severity based on amount lost.

        Args:
            amount_usd: Amount lost in USD

        Returns:
            IncidentSeverity enum value
        """
        if amount_usd > 50_000_000:
            return IncidentSeverity.CRITICAL
        elif amount_usd > 10_000_000:
            return IncidentSeverity.HIGH
        elif amount_usd > 1_000_000:
            return IncidentSeverity.MEDIUM
        else:
            return IncidentSeverity.LOW

    def _normalize_protocol_name(self, name: str | None) -> str:
        """
        Normalize protocol name for matching.

        Args:
            name: Protocol name to normalize

        Returns:
            Normalized name (lowercase, no special chars)
        """
        if not name:
            return ""

        # Convert to lowercase
        normalized = name.lower()

        # Remove common suffixes
        normalized = re.sub(r'\s+(finance|protocol|defi|network|v\d+)$', '', normalized)

        # Remove special characters except hyphens
        normalized = re.sub(r'[^\w\s-]', '', normalized)

        # Replace spaces with hyphens
        normalized = re.sub(r'\s+', '-', normalized)

        # Remove multiple hyphens
        normalized = re.sub(r'-+', '-', normalized)

        # Remove leading/trailing hyphens
        normalized = normalized.strip('-')

        return normalized


# Singleton instance
_scraper: RektScraper | None = None


def get_scraper() -> RektScraper:
    """Get singleton scraper instance."""
    global _scraper
    if _scraper is None:
        _scraper = RektScraper()
    return _scraper
