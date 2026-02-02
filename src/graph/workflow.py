"""LangGraph workflow definition for DeFi risk analysis."""

from typing import Annotated, Any, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from src.agents.data_agent import DataAgent
from src.agents.report_agent import ReportAgent
from src.agents.risk_agent import RiskAgent
from src.agents.supervisor import SupervisorAgent
from src.models.schemas import (
    ComparisonReport,
    ProtocolData,
    RiskAssessment,
    RiskReport,
)


class WorkflowState(TypedDict):
    """State for the DeFi risk analysis workflow."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    query: str
    protocol_names: list[str]
    protocol_data: dict[str, ProtocolData]
    risk_assessments: dict[str, RiskAssessment]
    report: RiskReport | ComparisonReport | None
    current_agent: str
    next_agent: str | None
    error: str | None


def create_initial_state(query: str) -> dict[str, Any]:
    """Create initial state for workflow execution."""
    return {
        "messages": [],
        "query": query,
        "protocol_names": [],
        "protocol_data": {},
        "risk_assessments": {},
        "report": None,
        "current_agent": "",
        "next_agent": "supervisor",
        "error": None,
    }


def route_next_agent(state: WorkflowState) -> str:
    """Route to next agent based on state."""
    if state.get("error"):
        return END

    next_agent = state.get("next_agent")

    if next_agent is None:
        return END

    return next_agent


def create_workflow() -> StateGraph:
    """Create the LangGraph workflow for DeFi risk analysis."""

    # Initialize agents
    supervisor = SupervisorAgent()
    data_agent = DataAgent()
    risk_agent = RiskAgent()
    report_agent = ReportAgent()

    # Create graph
    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("supervisor", supervisor.run)
    workflow.add_node("data_agent", data_agent.run)
    workflow.add_node("risk_agent", risk_agent.run)
    workflow.add_node("report_agent", report_agent.run)

    # Set entry point
    workflow.set_entry_point("supervisor")

    # Add conditional edges from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        route_next_agent,
        {
            "data_agent": "data_agent",
            "risk_agent": "risk_agent",
            "report_agent": "report_agent",
            END: END,
        },
    )

    # Add conditional edges from data_agent
    workflow.add_conditional_edges(
        "data_agent",
        route_next_agent,
        {
            "risk_agent": "risk_agent",
            "report_agent": "report_agent",
            END: END,
        },
    )

    # Add conditional edges from risk_agent
    workflow.add_conditional_edges(
        "risk_agent",
        route_next_agent,
        {
            "report_agent": "report_agent",
            END: END,
        },
    )

    # Report agent always ends
    workflow.add_edge("report_agent", END)

    return workflow


def compile_workflow():
    """Compile the workflow for execution."""
    workflow = create_workflow()
    return workflow.compile()


class DeFiRiskWorkflow:
    """High-level interface for running DeFi risk analysis workflows."""

    def __init__(self) -> None:
        self.app = compile_workflow()
        self.report_agent = ReportAgent()

    async def analyze(self, protocol: str) -> RiskReport | None:
        """Analyze a single protocol and return risk report."""
        initial_state = create_initial_state(f"analyze {protocol}")
        result = await self.app.ainvoke(initial_state)

        if result.get("error"):
            raise RuntimeError(result["error"])

        report = result.get("report")
        if isinstance(report, RiskReport):
            return report

        return None

    async def compare(self, protocols: list[str]) -> ComparisonReport | None:
        """Compare multiple protocols and return comparison report."""
        protocol_str = " ".join(protocols)
        initial_state = create_initial_state(f"compare {protocol_str}")
        result = await self.app.ainvoke(initial_state)

        if result.get("error"):
            raise RuntimeError(result["error"])

        report = result.get("report")
        if isinstance(report, ComparisonReport):
            return report

        return None

    async def run_query(self, query: str) -> dict[str, Any]:
        """Run arbitrary query through the workflow."""
        initial_state = create_initial_state(query)
        return await self.app.ainvoke(initial_state)

    def format_report(self, report: RiskReport | ComparisonReport) -> str:
        """Format report as markdown string."""
        if isinstance(report, RiskReport):
            return self.report_agent.format_report(report)
        elif isinstance(report, ComparisonReport):
            return self.report_agent.format_comparison_report(report)
        else:
            return str(report)
