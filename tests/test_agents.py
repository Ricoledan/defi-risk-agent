"""Tests for agent implementations."""

from datetime import datetime

import pytest

from src.agents.data_agent import DataAgent
from src.agents.report_agent import ReportAgent
from src.agents.risk_agent import RiskAgent
from src.agents.supervisor import SupervisorAgent
from src.models.schemas import (
    ChainBreakdown,
    ProtocolData,
    RiskAssessment,
    RiskFactor,
    RiskLevel,
    RiskScore,
)


@pytest.fixture
def sample_protocol():
    """Create sample protocol data."""
    return ProtocolData(
        name="Aave",
        slug="aave",
        symbol="AAVE",
        category="Lending",
        tvl=10_000_000_000,
        tvl_change_1d=0.5,
        tvl_change_7d=2.0,
        tvl_change_30d=5.0,
        chains=["Ethereum", "Polygon", "Arbitrum", "Optimism"],
        chain_tvls=[
            ChainBreakdown(chain="Ethereum", tvl=7_000_000_000, percentage=70),
            ChainBreakdown(chain="Polygon", tvl=1_500_000_000, percentage=15),
            ChainBreakdown(chain="Arbitrum", tvl=1_000_000_000, percentage=10),
            ChainBreakdown(chain="Optimism", tvl=500_000_000, percentage=5),
        ],
        audit_links=["https://audit1.com", "https://audit2.com", "https://audit3.com"],
        oracles=["Chainlink"],
    )


@pytest.fixture
def sample_assessment(sample_protocol: ProtocolData):
    """Create sample risk assessment."""
    return RiskAssessment(
        protocol_name=sample_protocol.name,
        protocol_slug=sample_protocol.slug,
        score=RiskScore(
            overall=3.5,
            level=RiskLevel.MEDIUM,
            factors=[
                RiskFactor(name="TVL Risk", score=2.5, weight=0.35, description="Large TVL"),
                RiskFactor(name="Chain Concentration", score=4.0, weight=0.25, description="Moderate"),
                RiskFactor(name="Audit Status", score=2.0, weight=0.25, description="Multiple audits"),
                RiskFactor(name="Oracle Risk", score=2.0, weight=0.15, description="Chainlink"),
            ],
        ),
        tvl_analysis="Strong TVL metrics",
        chain_analysis="Good diversification",
        audit_analysis="Well audited",
        recommendations=["Continue monitoring"],
        warnings=[],
    )


class TestSupervisorAgent:
    """Tests for SupervisorAgent."""

    def test_parse_query_analyze(self):
        """Test parsing analyze query."""
        supervisor = SupervisorAgent()

        intent, protocols = supervisor.parse_query("analyze aave risk")

        assert intent == "analyze"
        assert "aave" in protocols

    def test_parse_query_compare(self):
        """Test parsing compare query."""
        supervisor = SupervisorAgent()

        intent, protocols = supervisor.parse_query("compare aave vs compound")

        assert intent == "compare"
        assert "aave" in protocols
        assert "compound" in protocols

    def test_parse_query_data(self):
        """Test parsing data query."""
        supervisor = SupervisorAgent()

        intent, protocols = supervisor.parse_query("get tvl data for uniswap")

        assert intent == "data"
        assert "uniswap" in protocols

    def test_parse_query_unknown_protocol(self):
        """Test parsing query with unknown protocol."""
        supervisor = SupervisorAgent()

        intent, protocols = supervisor.parse_query("analyze someprotocol")

        assert intent == "analyze"
        assert "someprotocol" in protocols

    @pytest.mark.asyncio
    async def test_run_with_valid_query(self):
        """Test running supervisor with valid query."""
        supervisor = SupervisorAgent()
        state = {
            "messages": [],
            "query": "analyze aave",
            "protocol_names": [],
            "protocol_data": {},
            "risk_assessments": {},
            "report": None,
            "current_agent": "",
            "next_agent": None,
            "error": None,
        }

        result = await supervisor.run(state)

        assert result["protocol_names"] == ["aave"]
        assert result["next_agent"] == "data_agent"
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_run_with_empty_query(self):
        """Test running supervisor with empty query."""
        supervisor = SupervisorAgent()
        state = {
            "messages": [],
            "query": "",
            "protocol_names": [],
            "protocol_data": {},
            "risk_assessments": {},
            "report": None,
            "current_agent": "",
            "next_agent": None,
            "error": None,
        }

        result = await supervisor.run(state)

        assert result["error"] is not None


class TestDataAgent:
    """Tests for DataAgent."""

    def test_format_protocol_summary(self, sample_protocol: ProtocolData):
        """Test formatting protocol summary."""
        agent = DataAgent()

        summary = agent.format_protocol_summary(sample_protocol)

        assert "Aave" in summary
        assert "TVL" in summary
        assert "Ethereum" in summary


class TestRiskAgent:
    """Tests for RiskAgent."""

    def test_assess_protocol(self, sample_protocol: ProtocolData):
        """Test assessing protocol risk."""
        agent = RiskAgent()

        assessment = agent.assess_protocol(sample_protocol)

        assert assessment.protocol_name == "Aave"
        assert assessment.score.overall >= 0
        assert assessment.score.overall <= 10
        assert len(assessment.score.factors) == 4

    def test_format_assessment(self, sample_assessment: RiskAssessment):
        """Test formatting assessment."""
        agent = RiskAgent()

        formatted = agent.format_assessment(sample_assessment)

        assert "Aave" in formatted
        assert "Risk Assessment" in formatted
        assert "MEDIUM" in formatted

    def test_compare_assessments(self, sample_assessment: RiskAssessment):
        """Test comparing multiple assessments."""
        agent = RiskAgent()

        assessment2 = RiskAssessment(
            protocol_name="Compound",
            protocol_slug="compound",
            score=RiskScore(
                overall=4.0,
                level=RiskLevel.MEDIUM,
                factors=[],
            ),
            tvl_analysis="Test",
            chain_analysis="Test",
            audit_analysis="Test",
        )

        comparison = agent.compare_assessments({
            "aave": sample_assessment,
            "compound": assessment2,
        })

        assert "Risk Comparison" in comparison
        assert "Aave" in comparison
        assert "Compound" in comparison


class TestReportAgent:
    """Tests for ReportAgent."""

    def test_generate_executive_summary(
        self, sample_protocol: ProtocolData, sample_assessment: RiskAssessment
    ):
        """Test generating executive summary."""
        agent = ReportAgent()

        summary = agent.generate_executive_summary(sample_protocol, sample_assessment)

        assert "Aave" in summary
        assert "MEDIUM" in summary
        assert "$" in summary  # TVL amount

    def test_generate_report(
        self, sample_protocol: ProtocolData, sample_assessment: RiskAssessment
    ):
        """Test generating full report."""
        agent = ReportAgent()

        report = agent.generate_report(sample_protocol, sample_assessment)

        assert report.protocol.name == "Aave"
        assert report.assessment.protocol_name == "Aave"
        assert report.executive_summary
        assert report.detailed_analysis
        assert len(report.data_sources) > 0

    def test_format_report(
        self, sample_protocol: ProtocolData, sample_assessment: RiskAssessment
    ):
        """Test formatting report as markdown."""
        agent = ReportAgent()
        report = agent.generate_report(sample_protocol, sample_assessment)

        formatted = agent.format_report(report)

        assert "# DeFi Risk Report" in formatted
        assert "Executive Summary" in formatted
        assert "Data Sources" in formatted
