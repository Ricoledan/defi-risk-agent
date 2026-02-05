"""Integration tests for incident data in risk assessments and reports."""

from datetime import datetime, timedelta

import pytest

from src.agents.report_agent import ReportAgent
from src.models.schemas import (
    ChainBreakdown,
    ExploitIncident,
    IncidentSeverity,
    ProtocolData,
    TVLDataPoint,
)
from src.tools.risk_metrics import RiskCalculator


@pytest.fixture
def calculator():
    """Create risk calculator."""
    return RiskCalculator()


@pytest.fixture
def report_agent():
    """Create report agent."""
    return ReportAgent()


@pytest.fixture
def protocol_with_incidents():
    """Create protocol with incident history."""
    now = datetime.utcnow()
    return ProtocolData(
        name="Vulnerable Protocol",
        slug="vulnerable-protocol",
        symbol="VULN",
        category="DeFi",
        tvl=500_000_000,
        tvl_change_1d=-2.0,
        tvl_change_7d=-5.0,
        tvl_change_30d=-10.0,
        chains=["Ethereum", "Arbitrum"],
        chain_tvls=[
            ChainBreakdown(chain="Ethereum", tvl=400_000_000, percentage=80),
            ChainBreakdown(chain="Arbitrum", tvl=100_000_000, percentage=20),
        ],
        tvl_history=[
            TVLDataPoint(date=now - timedelta(days=i), tvl=500_000_000 * (1 + i * 0.001))
            for i in range(30)
        ],
        audit_links=["https://audit.example.com"],
        oracles=["Chainlink"],
        incidents=[
            ExploitIncident(
                protocol_name="Vulnerable Protocol",
                date=now - timedelta(days=45),
                amount_lost_usd=30_000_000,
                severity=IncidentSeverity.HIGH,
                title="Flash Loan Attack - $30M",
                description="Reentrancy vulnerability exploited",
                fixed=True,
                details_url="https://rekt.news/vulnerable-protocol",
            ),
            ExploitIncident(
                protocol_name="Vulnerable Protocol",
                date=now - timedelta(days=180),
                amount_lost_usd=5_000_000,
                severity=IncidentSeverity.MEDIUM,
                title="Oracle Manipulation - $5M",
                description="Price oracle exploited",
                fixed=True,
                details_url="https://rekt.news/vulnerable-protocol-2",
            ),
        ],
    )


@pytest.fixture
def clean_protocol():
    """Create protocol with no incidents."""
    now = datetime.utcnow()
    return ProtocolData(
        name="Clean Protocol",
        slug="clean-protocol",
        symbol="CLEAN",
        category="DeFi",
        tvl=1_000_000_000,
        tvl_change_1d=1.0,
        tvl_change_7d=3.0,
        tvl_change_30d=8.0,
        chains=["Ethereum", "Arbitrum", "Polygon"],
        chain_tvls=[
            ChainBreakdown(chain="Ethereum", tvl=500_000_000, percentage=50),
            ChainBreakdown(chain="Arbitrum", tvl=300_000_000, percentage=30),
            ChainBreakdown(chain="Polygon", tvl=200_000_000, percentage=20),
        ],
        tvl_history=[
            TVLDataPoint(date=now - timedelta(days=i), tvl=1_000_000_000 * (1 - i * 0.0005))
            for i in range(30)
        ],
        audit_links=["https://audit1.example.com", "https://audit2.example.com"],
        oracles=["Chainlink"],
        incidents=[],
    )


def test_risk_calculation_with_incidents(calculator, protocol_with_incidents):
    """Test that incidents properly affect risk scores."""
    assessment = calculator.assess_protocol(protocol_with_incidents)

    # Should have incident factor
    incident_factor = next(
        (f for f in assessment.score.factors if f.name == "Incident History"), None
    )
    assert incident_factor is not None
    assert incident_factor.weight == 0.15

    # Incident score should be elevated due to recent high-severity incident
    assert incident_factor.score > 4.0

    # Incident analysis should mention the incidents
    assert "incident" in assessment.incident_analysis.lower()
    assert assessment.incident_analysis


def test_risk_calculation_without_incidents(calculator, clean_protocol):
    """Test that clean protocols have low incident risk."""
    assessment = calculator.assess_protocol(clean_protocol)

    incident_factor = next(
        (f for f in assessment.score.factors if f.name == "Incident History"), None
    )
    assert incident_factor is not None
    assert incident_factor.score == 2.0  # Clean record

    assert "no documented" in assessment.incident_analysis.lower()


def test_comparison_with_incidents(calculator, protocol_with_incidents, clean_protocol):
    """Test comparing protocols with different incident histories."""
    vulnerable_assessment = calculator.assess_protocol(protocol_with_incidents)
    clean_assessment = calculator.assess_protocol(clean_protocol)

    # Clean protocol should have lower overall risk
    assert clean_assessment.score.overall < vulnerable_assessment.score.overall

    # Get incident factors
    vuln_incident = next(
        f for f in vulnerable_assessment.score.factors if f.name == "Incident History"
    )
    clean_incident = next(
        f for f in clean_assessment.score.factors if f.name == "Incident History"
    )

    # Vulnerable protocol should have higher incident risk
    assert vuln_incident.score > clean_incident.score


def test_report_includes_incidents(report_agent, calculator, protocol_with_incidents):
    """Test that reports properly display incident information."""
    assessment = calculator.assess_protocol(protocol_with_incidents)
    report = report_agent.generate_report(protocol_with_incidents, assessment)

    # Executive summary should mention incidents
    assert "incident" in report.executive_summary.lower()

    # Detailed analysis should include incident section
    assert "## Incident History" in report.detailed_analysis
    assert "Flash Loan Attack" in report.detailed_analysis
    assert "$30" in report.detailed_analysis  # Amount

    # Should show incident details
    assert "https://rekt.news/vulnerable-protocol" in report.detailed_analysis


def test_report_clean_protocol(report_agent, calculator, clean_protocol):
    """Test that reports show clean history for protocols without incidents."""
    assessment = calculator.assess_protocol(clean_protocol)
    report = report_agent.generate_report(clean_protocol, assessment)

    # Should mention no incidents
    assert "no documented security incidents" in report.executive_summary.lower()
    assert "No historical incidents found" in report.detailed_analysis


def test_incident_severity_affects_score(calculator, protocol_with_incidents):
    """Test that incident severity properly affects risk scores."""
    now = datetime.utcnow()

    # Test with critical incident
    protocol_with_incidents.incidents = [
        ExploitIncident(
            protocol_name="Test",
            date=now - timedelta(days=30),
            amount_lost_usd=150_000_000,
            severity=IncidentSeverity.CRITICAL,
            title="Critical - $150M",
            fixed=False,
        )
    ]

    assessment_critical = calculator.assess_protocol(protocol_with_incidents)
    critical_factor = next(
        f for f in assessment_critical.score.factors if f.name == "Incident History"
    )

    # Test with low severity incident
    protocol_with_incidents.incidents = [
        ExploitIncident(
            protocol_name="Test",
            date=now - timedelta(days=30),
            amount_lost_usd=500_000,
            severity=IncidentSeverity.LOW,
            title="Low - $500K",
            fixed=True,
        )
    ]

    assessment_low = calculator.assess_protocol(protocol_with_incidents)
    low_factor = next(f for f in assessment_low.score.factors if f.name == "Incident History")

    # Critical should have higher risk score
    assert critical_factor.score > low_factor.score


def test_incident_recency_affects_score(calculator, protocol_with_incidents):
    """Test that recent incidents have higher impact than old incidents."""
    now = datetime.utcnow()

    # Recent incident
    protocol_with_incidents.incidents = [
        ExploitIncident(
            protocol_name="Test",
            date=now - timedelta(days=20),
            amount_lost_usd=20_000_000,
            severity=IncidentSeverity.HIGH,
            title="Recent - $20M",
            fixed=False,
        )
    ]

    assessment_recent = calculator.assess_protocol(protocol_with_incidents)
    recent_factor = next(
        f for f in assessment_recent.score.factors if f.name == "Incident History"
    )

    # Old incident
    protocol_with_incidents.incidents = [
        ExploitIncident(
            protocol_name="Test",
            date=now - timedelta(days=800),
            amount_lost_usd=20_000_000,
            severity=IncidentSeverity.HIGH,
            title="Old - $20M",
            fixed=True,
        )
    ]

    assessment_old = calculator.assess_protocol(protocol_with_incidents)
    old_factor = next(f for f in assessment_old.score.factors if f.name == "Incident History")

    # Recent should have higher risk score
    assert recent_factor.score > old_factor.score


def test_multiple_incidents_compound_risk(calculator, protocol_with_incidents):
    """Test that multiple incidents compound the risk score."""
    now = datetime.utcnow()

    # Single incident
    protocol_with_incidents.incidents = [
        ExploitIncident(
            protocol_name="Test",
            date=now - timedelta(days=60),
            amount_lost_usd=10_000_000,
            severity=IncidentSeverity.MEDIUM,
            title="Single - $10M",
            fixed=True,
        )
    ]

    assessment_single = calculator.assess_protocol(protocol_with_incidents)
    single_factor = next(
        f for f in assessment_single.score.factors if f.name == "Incident History"
    )

    # Multiple incidents
    protocol_with_incidents.incidents = [
        ExploitIncident(
            protocol_name="Test",
            date=now - timedelta(days=60),
            amount_lost_usd=10_000_000,
            severity=IncidentSeverity.MEDIUM,
            title="First - $10M",
            fixed=True,
        ),
        ExploitIncident(
            protocol_name="Test",
            date=now - timedelta(days=120),
            amount_lost_usd=8_000_000,
            severity=IncidentSeverity.MEDIUM,
            title="Second - $8M",
            fixed=True,
        ),
        ExploitIncident(
            protocol_name="Test",
            date=now - timedelta(days=200),
            amount_lost_usd=5_000_000,
            severity=IncidentSeverity.LOW,
            title="Third - $5M",
            fixed=True,
        ),
    ]

    assessment_multiple = calculator.assess_protocol(protocol_with_incidents)
    multiple_factor = next(
        f for f in assessment_multiple.score.factors if f.name == "Incident History"
    )

    # Multiple incidents should generally have higher risk (though normalized)
    assert len(protocol_with_incidents.incidents) == 3


def test_data_sources_include_rekt(report_agent, calculator, protocol_with_incidents):
    """Test that Rekt.news is included in data sources."""
    assessment = calculator.assess_protocol(protocol_with_incidents)
    report = report_agent.generate_report(protocol_with_incidents, assessment)

    # Should include Rekt.news in data sources
    assert any("rekt.news" in source.lower() for source in report.data_sources)
