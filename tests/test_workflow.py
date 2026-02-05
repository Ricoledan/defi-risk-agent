"""Tests for LangGraph workflow."""

import pytest

from src.graph.workflow import (
    DeFiRiskWorkflow,
    compile_workflow,
    create_initial_state,
    create_workflow,
)
from src.models.schemas import ComparisonReport, RiskReport


def test_create_initial_state():
    """Test creating initial state."""
    state = create_initial_state("analyze aave")

    assert state["query"] == "analyze aave"
    assert state["protocol_names"] == []
    assert state["protocol_data"] == {}
    assert state["risk_assessments"] == {}
    assert state["report"] is None
    assert state["next_agent"] == "supervisor"
    assert state["error"] is None


def test_create_workflow():
    """Test creating workflow graph."""
    workflow = create_workflow()

    # Check nodes exist
    assert "supervisor" in workflow.nodes
    assert "data_agent" in workflow.nodes
    assert "risk_agent" in workflow.nodes
    assert "report_agent" in workflow.nodes


def test_compile_workflow():
    """Test compiling workflow."""
    app = compile_workflow()

    assert app is not None


class TestDeFiRiskWorkflow:
    """Integration tests for DeFiRiskWorkflow."""

    @pytest.fixture
    def workflow(self):
        """Create workflow instance."""
        return DeFiRiskWorkflow()

    @pytest.mark.asyncio
    async def test_analyze_aave(self, workflow: DeFiRiskWorkflow):
        """Test analyzing Aave (real API call)."""
        report = await workflow.analyze("aave")

        assert report is not None
        assert isinstance(report, RiskReport)
        assert "aave" in report.protocol.slug.lower()
        assert report.protocol.tvl > 0
        assert report.assessment.score.overall >= 0
        assert report.executive_summary
        assert report.detailed_analysis

    @pytest.mark.asyncio
    async def test_compare_protocols(self, workflow: DeFiRiskWorkflow):
        """Test comparing protocols (real API call)."""
        report = await workflow.compare(["aave", "compound"])

        assert report is not None
        assert isinstance(report, ComparisonReport)
        assert len(report.protocols) == 2
        assert len(report.assessments) == 2
        assert report.comparison_summary
        assert report.recommendation

    @pytest.mark.asyncio
    async def test_run_query(self, workflow: DeFiRiskWorkflow):
        """Test running natural language query."""
        result = await workflow.run_query("analyze aave risk")

        assert result["error"] is None
        assert "aave" in result["protocol_names"]
        assert result["report"] is not None

    @pytest.mark.asyncio
    async def test_analyze_invalid_protocol(self, workflow: DeFiRiskWorkflow):
        """Test analyzing non-existent protocol."""
        with pytest.raises(RuntimeError):
            await workflow.analyze("nonexistent_protocol_xyz123")

    def test_format_risk_report(self, workflow: DeFiRiskWorkflow):
        """Test formatting risk report."""
        from src.models.schemas import (
            ChainBreakdown,
            ProtocolData,
            RiskAssessment,
            RiskLevel,
            RiskScore,
        )

        protocol = ProtocolData(
            name="Test",
            slug="test",
            tvl=1e9,
            chains=["Ethereum"],
            chain_tvls=[ChainBreakdown(chain="Ethereum", tvl=1e9, percentage=100)],
        )

        assessment = RiskAssessment(
            protocol_name="Test",
            protocol_slug="test",
            score=RiskScore(overall=3.0, level=RiskLevel.LOW, factors=[]),
            tvl_analysis="Test",
            chain_analysis="Test",
            audit_analysis="Test",
            incident_analysis="Test",
        )

        report = RiskReport(
            protocol=protocol,
            assessment=assessment,
            executive_summary="Test summary",
            detailed_analysis="Test analysis",
            data_sources=["Test source"],
        )

        formatted = workflow.format_report(report)

        assert "Test" in formatted
        assert "DeFi Risk Report" in formatted
