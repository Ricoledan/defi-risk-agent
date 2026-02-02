"""Data Agent - Fetches protocol data from DefiLlama."""

from langchain_core.prompts import ChatPromptTemplate

from src.models.schemas import AgentState, ProtocolData
from src.tools.defillama import DefiLlamaClient, DefiLlamaError, get_client

DATA_AGENT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a DeFi data specialist agent. Your role is to fetch and validate
protocol data from DefiLlama. You have access to comprehensive DeFi protocol information
including TVL, chain breakdowns, and audit status.

When reporting data:
- Always cite DefiLlama as the source
- Include timestamps for data freshness
- Flag any missing or incomplete data
- Format numbers in human-readable form (e.g., $1.5B instead of 1500000000)
""",
        ),
        ("human", "{input}"),
    ]
)


class DataAgent:
    """Agent responsible for fetching DeFi protocol data."""

    def __init__(self, client: DefiLlamaClient | None = None) -> None:
        self.client = client or get_client()
        self.name = "data_agent"

    async def fetch_protocol(self, protocol_name: str) -> ProtocolData:
        """Fetch data for a single protocol."""
        return await self.client.fetch_protocol_data(protocol_name)

    async def fetch_protocols(self, protocol_names: list[str]) -> dict[str, ProtocolData]:
        """Fetch data for multiple protocols."""
        results: dict[str, ProtocolData] = {}
        errors: list[str] = []

        for name in protocol_names:
            try:
                data = await self.fetch_protocol(name)
                results[data.slug] = data
            except DefiLlamaError as e:
                errors.append(f"{name}: {e}")

        if errors and not results:
            raise DefiLlamaError(f"Failed to fetch all protocols: {', '.join(errors)}")

        return results

    async def run(self, state: AgentState) -> AgentState:
        """Execute data fetching step in the workflow."""
        protocol_names = state.get("protocol_names", [])

        if not protocol_names:
            return {
                **state,
                "error": "No protocols specified for data fetching",
                "current_agent": self.name,
                "next_agent": None,
            }

        try:
            protocol_data = await self.fetch_protocols(protocol_names)

            # Add message about fetched data
            messages = state.get("messages", [])
            fetched_names = list(protocol_data.keys())
            message_content = f"Successfully fetched data for: {', '.join(fetched_names)}"

            for slug, data in protocol_data.items():
                message_content += (
                    f"\n- {data.name}: TVL ${data.tvl / 1e9:.2f}B across {len(data.chains)} chains"
                )

            messages.append(
                {
                    "role": "assistant",
                    "content": message_content,
                    "agent": self.name,
                }
            )

            return {
                **state,
                "protocol_data": protocol_data,
                "messages": messages,
                "current_agent": self.name,
                "next_agent": "risk_agent",
                "error": None,
            }

        except DefiLlamaError as e:
            return {
                **state,
                "error": str(e),
                "current_agent": self.name,
                "next_agent": None,
            }

    def format_protocol_summary(self, data: ProtocolData) -> str:
        """Format protocol data as human-readable summary."""
        lines = [
            f"# {data.name} ({data.symbol or 'N/A'})",
            f"**Category:** {data.category or 'Unknown'}",
            f"**TVL:** ${data.tvl / 1e9:.2f}B",
            "",
            "## TVL Changes",
            f"- 24h: {data.tvl_change_1d or 0:+.2f}%",
            f"- 7d: {data.tvl_change_7d or 0:+.2f}%",
            f"- 30d: {data.tvl_change_30d or 0:+.2f}%",
            "",
            "## Chain Distribution",
        ]

        for chain in data.chain_tvls[:5]:
            lines.append(f"- {chain.chain}: ${chain.tvl / 1e9:.2f}B ({chain.percentage:.1f}%)")

        lines.extend(
            [
                "",
                "## Security",
                f"**Audits:** {len(data.audit_links)} on record"
                if data.audit_links
                else "**Audits:** None found",
                f"**Oracles:** {', '.join(data.oracles) if data.oracles else 'None specified'}",
                "",
                f"_Data source: DefiLlama | Fetched: {data.fetched_at:%Y-%m-%d %H:%M UTC}_",
            ]
        )

        return "\n".join(lines)
