"""Supervisor Agent - Routes queries to appropriate specialist agents."""

from typing import Literal

from langchain_core.prompts import ChatPromptTemplate

from src.models.schemas import AgentState

SUPERVISOR_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a DeFi risk analysis supervisor agent. Your role is to:
1. Understand user queries about DeFi protocol risk
2. Route requests to the appropriate specialist agents
3. Manage multi-step analysis workflows
4. Ensure quality and completeness of responses

Agent routing:
- data_agent: For fetching protocol data from DefiLlama
- risk_agent: For analyzing risk factors and generating scores
- report_agent: For synthesizing findings into reports

Workflow order for analysis requests:
1. data_agent (fetch data) -> 2. risk_agent (analyze) -> 3. report_agent (generate report)

For simple data queries, you may skip directly to data_agent.
For risk questions, route through the full workflow.
""",
        ),
        ("human", "{input}"),
    ]
)


AgentName = Literal["data_agent", "risk_agent", "report_agent", "supervisor"]


class SupervisorAgent:
    """Supervisor agent that routes queries and manages workflow."""

    def __init__(self) -> None:
        self.name = "supervisor"

    def parse_query(self, query: str) -> tuple[str, list[str]]:
        """Parse user query to determine intent and extract protocol names."""
        query_lower = query.lower()

        # Determine intent
        if any(word in query_lower for word in ["compare", "vs", "versus", "difference"]):
            intent = "compare"
        elif any(word in query_lower for word in ["analyze", "risk", "assess", "report"]):
            intent = "analyze"
        elif any(word in query_lower for word in ["data", "tvl", "info", "fetch"]):
            intent = "data"
        else:
            intent = "analyze"  # Default to full analysis

        # Extract protocol names (simple heuristic)
        # Common DeFi protocols for matching
        known_protocols = [
            "aave",
            "compound",
            "makerdao",
            "maker",
            "uniswap",
            "curve",
            "lido",
            "rocket pool",
            "rocketpool",
            "convex",
            "yearn",
            "balancer",
            "sushiswap",
            "pancakeswap",
            "gmx",
            "dydx",
            "morpho",
            "euler",
            "venus",
            "benqi",
            "traderjoe",
            "instadapp",
            "radiant",
            "spark",
            "frax",
            "eigenlayer",
        ]

        protocols = []
        for protocol in known_protocols:
            if protocol in query_lower:
                # Normalize name
                normalized = protocol.replace(" ", "-")
                if normalized not in protocols:
                    protocols.append(normalized)

        # If no known protocols found, try to extract words that might be protocol names
        if not protocols:
            # Simple extraction: look for capitalized words or words after "analyze/compare"
            words = query.split()
            for i, word in enumerate(words):
                clean_word = word.strip(",.!?").lower()
                if clean_word and clean_word not in [
                    "analyze",
                    "compare",
                    "risk",
                    "report",
                    "the",
                    "and",
                    "vs",
                    "versus",
                    "with",
                    "for",
                    "of",
                    "to",
                    "a",
                    "an",
                    "protocol",
                ]:
                    if len(clean_word) >= 2 and clean_word.isalpha():
                        protocols.append(clean_word)
                        if len(protocols) >= 5:  # Max 5 protocols
                            break

        return intent, protocols[:5]  # Limit to 5 protocols

    def determine_first_agent(self, intent: str) -> AgentName:
        """Determine which agent should handle the query first."""
        # All intents start with data fetching
        return "data_agent"

    def determine_next_agent(self, current_agent: AgentName, state: AgentState) -> AgentName | None:
        """Determine next agent based on current state."""
        # Check for errors
        if state.get("error"):
            return None

        # Standard workflow progression
        if current_agent == "data_agent":
            return "risk_agent"
        elif current_agent == "risk_agent":
            return "report_agent"
        elif current_agent == "report_agent":
            return None  # Workflow complete

        return None

    async def run(self, state: AgentState) -> AgentState:
        """Process query and initialize workflow."""
        query = state.get("query", "")

        if not query:
            return {
                **state,
                "error": "No query provided",
                "current_agent": self.name,
                "next_agent": None,
            }

        # Parse query
        intent, protocols = self.parse_query(query)

        if not protocols:
            error_msg = (
                "Could not identify any protocol names in the query. "
                "Please specify a protocol name (e.g., 'analyze aave')"
            )
            return {
                **state,
                "error": error_msg,
                "current_agent": self.name,
                "next_agent": None,
            }

        # Initialize workflow
        first_agent = self.determine_first_agent(intent)

        messages = state.get("messages", [])
        messages.append(
            {
                "role": "assistant",
                "content": f"Starting {intent} workflow for: {', '.join(protocols)}",
                "agent": self.name,
            }
        )

        return {
            **state,
            "protocol_names": protocols,
            "messages": messages,
            "current_agent": self.name,
            "next_agent": first_agent,
            "error": None,
        }
