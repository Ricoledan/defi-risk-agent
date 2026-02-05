"""DefiLlama API client for fetching protocol data."""

from datetime import datetime
from typing import Any

import httpx

from src.models.schemas import ChainBreakdown, ProtocolData, TVLDataPoint
from src.tools.rekt_scraper import get_scraper

BASE_URL = "https://api.llama.fi"
TIMEOUT = 30.0


class DefiLlamaError(Exception):
    """Error from DefiLlama API."""

    pass


class DefiLlamaClient:
    """Client for DefiLlama API with caching."""

    def __init__(self, timeout: float = TIMEOUT) -> None:
        self.base_url = BASE_URL
        self.timeout = timeout
        self._cache: dict[str, tuple[datetime, Any]] = {}
        self._cache_ttl = 300  # 5 minutes

    def _get_cached(self, key: str) -> Any | None:
        """Get cached value if not expired."""
        if key in self._cache:
            cached_at, value = self._cache[key]
            if (datetime.utcnow() - cached_at).total_seconds() < self._cache_ttl:
                return value
            del self._cache[key]
        return None

    def _set_cache(self, key: str, value: Any) -> None:
        """Cache a value."""
        self._cache[key] = (datetime.utcnow(), value)

    async def _request(self, endpoint: str) -> Any:
        """Make HTTP request to DefiLlama API."""
        url = f"{self.base_url}{endpoint}"

        cached = self._get_cached(url)
        if cached is not None:
            return cached

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                self._set_cache(url, data)
                return data
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise DefiLlamaError(f"Protocol not found: {endpoint}")
                raise DefiLlamaError(f"API error: {e.response.status_code}")
            except httpx.RequestError as e:
                raise DefiLlamaError(f"Request failed: {e}")

    async def get_protocols(self) -> list[dict[str, Any]]:
        """Fetch list of all protocols with metadata."""
        return await self._request("/protocols")

    async def get_protocol(self, slug: str) -> dict[str, Any]:
        """Fetch detailed protocol data including TVL history."""
        return await self._request(f"/protocol/{slug}")

    async def get_chains(self) -> list[dict[str, Any]]:
        """Fetch chain-level TVL data."""
        return await self._request("/chains")

    async def get_yields_pools(self) -> dict[str, Any]:
        """Fetch yield pool data with APY."""
        return await self._request("/pools")

    async def search_protocol(self, query: str) -> str | None:
        """Search for protocol by name and return slug."""
        protocols = await self.get_protocols()
        query_lower = query.lower()

        # Exact match first
        for p in protocols:
            if p.get("slug", "").lower() == query_lower:
                return p["slug"]
            if p.get("name", "").lower() == query_lower:
                return p["slug"]

        # Partial match
        for p in protocols:
            if query_lower in p.get("slug", "").lower():
                return p["slug"]
            if query_lower in p.get("name", "").lower():
                return p["slug"]

        return None

    async def fetch_protocol_data(self, protocol_name: str) -> ProtocolData:
        """Fetch and parse protocol data into structured format."""
        # Search for the protocol first
        slug = await self.search_protocol(protocol_name)
        if not slug:
            raise DefiLlamaError(f"Protocol '{protocol_name}' not found")

        # Fetch detailed data
        data = await self.get_protocol(slug)

        # Parse TVL history (tvl field is a list of historical data)
        tvl_history: list[TVLDataPoint] = []
        tvl_data = data.get("tvl", [])
        if isinstance(tvl_data, list) and tvl_data:
            for point in tvl_data[-90:]:
                try:
                    tvl_history.append(
                        TVLDataPoint(
                            date=datetime.fromtimestamp(point["date"]),
                            tvl=point.get("totalLiquidityUSD", 0),
                        )
                    )
                except (KeyError, ValueError):
                    continue

        # Get current TVL from the latest history point or currentChainTvls
        current_chain_tvls = data.get("currentChainTvls", {})

        # Calculate total TVL from currentChainTvls (exclude borrowed, staking, pool2)
        total_tvl = 0.0
        chain_tvls: list[ChainBreakdown] = []
        excluded_suffixes = ["-borrowed", "-staking", "-pool2"]

        for chain, tvl in current_chain_tvls.items():
            # Skip aggregate categories and borrowed amounts
            if chain in ["borrowed", "staking", "pool2"] or any(
                chain.endswith(suffix) for suffix in excluded_suffixes
            ):
                continue
            if isinstance(tvl, (int, float)) and tvl > 0:
                total_tvl += tvl
                chain_tvls.append(
                    ChainBreakdown(chain=chain, tvl=tvl, percentage=0)  # Will calculate after
                )

        # Calculate percentages
        if total_tvl > 0:
            for chain_tvl in chain_tvls:
                chain_tvl.percentage = (chain_tvl.tvl / total_tvl) * 100

        # If no currentChainTvls, use latest historical TVL
        if total_tvl == 0 and tvl_history:
            total_tvl = tvl_history[-1].tvl

        # Sort by TVL descending
        chain_tvls.sort(key=lambda x: x.tvl, reverse=True)

        # Extract audit info
        audits: list[str] = []
        audit_links: list[str] = []
        if "audits" in data:
            if isinstance(data["audits"], str) and data["audits"] != "0":
                audits.append(data["audits"])
        if "audit_links" in data:
            audit_links = data.get("audit_links", []) or []

        # Calculate TVL changes
        tvl_change_1d = data.get("change_1d")
        tvl_change_7d = data.get("change_7d")
        tvl_change_30d = data.get("change_1m")

        # Fetch incident data
        scraper = get_scraper()
        try:
            incidents = await scraper.fetch_protocol_incidents(slug, data.get("name", slug))
        except Exception:
            incidents = []  # Don't fail on scraper errors

        return ProtocolData(
            name=data.get("name", slug),
            slug=slug,
            symbol=data.get("symbol"),
            category=data.get("category"),
            description=data.get("description"),
            url=data.get("url"),
            logo=data.get("logo"),
            tvl=total_tvl,
            tvl_change_1d=tvl_change_1d,
            tvl_change_7d=tvl_change_7d,
            tvl_change_30d=tvl_change_30d,
            chains=data.get("chains", []) or [],
            chain_tvls=chain_tvls,
            tvl_history=tvl_history,
            audits=audits,
            audit_links=audit_links,
            oracles=data.get("oracles", []) or [],
            incidents=incidents,
            gecko_id=data.get("gecko_id"),
            twitter=data.get("twitter"),
            mcap=data.get("mcap"),
        )


# Singleton instance
_client: DefiLlamaClient | None = None


def get_client() -> DefiLlamaClient:
    """Get or create DefiLlama client singleton."""
    global _client
    if _client is None:
        _client = DefiLlamaClient()
    return _client
