"""Tests for DefiLlama client."""

import pytest

from src.tools.defillama import DefiLlamaClient, DefiLlamaError


@pytest.fixture
def client():
    """Create DefiLlama client."""
    return DefiLlamaClient()


@pytest.mark.asyncio
async def test_get_protocols(client: DefiLlamaClient):
    """Test fetching protocol list."""
    protocols = await client.get_protocols()

    assert isinstance(protocols, list)
    assert len(protocols) > 0

    # Check structure of first protocol
    first = protocols[0]
    assert "name" in first
    assert "slug" in first


@pytest.mark.asyncio
async def test_search_protocol_exact(client: DefiLlamaClient):
    """Test searching for protocol by exact name."""
    slug = await client.search_protocol("aave")

    assert slug is not None
    assert "aave" in slug.lower()


@pytest.mark.asyncio
async def test_search_protocol_partial(client: DefiLlamaClient):
    """Test searching for protocol by partial name."""
    slug = await client.search_protocol("uni")

    assert slug is not None


@pytest.mark.asyncio
async def test_search_protocol_not_found(client: DefiLlamaClient):
    """Test searching for non-existent protocol."""
    slug = await client.search_protocol("nonexistent_protocol_xyz123")

    assert slug is None


@pytest.mark.asyncio
async def test_fetch_protocol_data(client: DefiLlamaClient):
    """Test fetching detailed protocol data."""
    data = await client.fetch_protocol_data("aave")

    assert data.name.lower() == "aave" or "aave" in data.slug.lower()
    assert data.tvl > 0
    assert len(data.chains) > 0


@pytest.mark.asyncio
async def test_fetch_protocol_not_found(client: DefiLlamaClient):
    """Test fetching non-existent protocol raises error."""
    with pytest.raises(DefiLlamaError, match="not found"):
        await client.fetch_protocol_data("nonexistent_protocol_xyz123")


@pytest.mark.asyncio
async def test_caching(client: DefiLlamaClient):
    """Test that responses are cached."""
    # First call
    await client.get_protocols()

    # Second call should use cache
    await client.get_protocols()

    # Check cache has entry
    assert len(client._cache) > 0
