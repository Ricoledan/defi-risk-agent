"""Tests for risk metrics calculator."""

from datetime import datetime, timedelta

import pytest

from src.models.schemas import ChainBreakdown, ProtocolData, RiskLevel, TVLDataPoint
from src.tools.risk_metrics import RiskCalculator


@pytest.fixture
def calculator():
    """Create risk calculator."""
    return RiskCalculator()


@pytest.fixture
def sample_protocol():
    """Create sample protocol data for testing."""
    now = datetime.utcnow()
    return ProtocolData(
        name="Test Protocol",
        slug="test-protocol",
        symbol="TEST",
        category="Lending",
        tvl=5_000_000_000,  # $5B
        tvl_change_1d=1.5,
        tvl_change_7d=5.0,
        tvl_change_30d=10.0,
        chains=["Ethereum", "Arbitrum", "Polygon", "Optimism", "BSC"],
        chain_tvls=[
            ChainBreakdown(chain="Ethereum", tvl=3_000_000_000, percentage=60),
            ChainBreakdown(chain="Arbitrum", tvl=1_000_000_000, percentage=20),
            ChainBreakdown(chain="Polygon", tvl=500_000_000, percentage=10),
            ChainBreakdown(chain="Optimism", tvl=300_000_000, percentage=6),
            ChainBreakdown(chain="BSC", tvl=200_000_000, percentage=4),
        ],
        tvl_history=[
            TVLDataPoint(date=now - timedelta(days=i), tvl=5_000_000_000 * (1 - i * 0.001))
            for i in range(90)
        ],
        audit_links=["https://audit1.com", "https://audit2.com"],
        oracles=["Chainlink"],
    )


@pytest.fixture
def high_risk_protocol():
    """Create high-risk protocol data."""
    now = datetime.utcnow()
    return ProtocolData(
        name="Risky Protocol",
        slug="risky-protocol",
        symbol="RISK",
        category="Yield",
        tvl=5_000_000,  # $5M - small
        tvl_change_1d=-5.0,
        tvl_change_7d=-15.0,
        tvl_change_30d=-40.0,  # Sharp decline
        chains=["Ethereum"],
        chain_tvls=[
            ChainBreakdown(chain="Ethereum", tvl=5_000_000, percentage=100),
        ],
        tvl_history=[
            TVLDataPoint(date=now - timedelta(days=i), tvl=5_000_000 * (1 + i * 0.02))
            for i in range(90)
        ],
        audits=[],  # No audits
        audit_links=[],
        oracles=[],
    )


def test_calculate_tvl_volatility(calculator: RiskCalculator, sample_protocol: ProtocolData):
    """Test TVL volatility calculation."""
    volatility = calculator.calculate_tvl_volatility(sample_protocol.tvl_history)

    assert volatility >= 0
    assert volatility < 1  # Should be low for stable protocol


def test_calculate_tvl_volatility_empty(calculator: RiskCalculator):
    """Test volatility with empty history."""
    volatility = calculator.calculate_tvl_volatility([])
    assert volatility == 0.0


def test_calculate_chain_concentration(calculator: RiskCalculator, sample_protocol: ProtocolData):
    """Test chain concentration calculation (HHI)."""
    hhi = calculator.calculate_chain_concentration(sample_protocol.chain_tvls)

    # HHI for diversified protocol should be moderate
    assert 0 < hhi < 100
    # With 60% on one chain, HHI should be around 36-45
    assert 30 < hhi < 50


def test_calculate_chain_concentration_single(calculator: RiskCalculator):
    """Test concentration with single chain."""
    single_chain = [ChainBreakdown(chain="Ethereum", tvl=1e9, percentage=100)]
    hhi = calculator.calculate_chain_concentration(single_chain)

    # Single chain = 100% = HHI of 100
    assert hhi == 100


def test_assess_tvl_risk_low(calculator: RiskCalculator, sample_protocol: ProtocolData):
    """Test TVL risk assessment for healthy protocol."""
    factor = calculator.assess_tvl_risk(sample_protocol)

    assert factor.name == "TVL Risk"
    assert factor.weight == 0.35
    assert factor.score < 5  # Should be low risk


def test_assess_tvl_risk_high(calculator: RiskCalculator, high_risk_protocol: ProtocolData):
    """Test TVL risk assessment for risky protocol."""
    factor = calculator.assess_tvl_risk(high_risk_protocol)

    assert factor.score > 6  # Should be high risk due to small TVL and decline


def test_assess_chain_risk_diversified(calculator: RiskCalculator, sample_protocol: ProtocolData):
    """Test chain risk for diversified protocol."""
    factor = calculator.assess_chain_risk(sample_protocol)

    assert factor.name == "Chain Concentration"
    assert factor.score < 6  # Diversified = lower risk


def test_assess_chain_risk_concentrated(calculator: RiskCalculator, high_risk_protocol: ProtocolData):
    """Test chain risk for single-chain protocol."""
    factor = calculator.assess_chain_risk(high_risk_protocol)

    assert factor.score > 5  # Single chain = higher risk


def test_assess_audit_risk_audited(calculator: RiskCalculator, sample_protocol: ProtocolData):
    """Test audit risk for audited protocol."""
    factor = calculator.assess_audit_risk(sample_protocol)

    assert factor.name == "Audit Status"
    assert factor.score < 5  # Audited = lower risk


def test_assess_audit_risk_unaudited(calculator: RiskCalculator, high_risk_protocol: ProtocolData):
    """Test audit risk for unaudited protocol."""
    factor = calculator.assess_audit_risk(high_risk_protocol)

    assert factor.score > 6  # No audits = higher risk


def test_calculate_overall_risk(calculator: RiskCalculator, sample_protocol: ProtocolData):
    """Test overall risk calculation."""
    factors = [
        calculator.assess_tvl_risk(sample_protocol),
        calculator.assess_chain_risk(sample_protocol),
        calculator.assess_audit_risk(sample_protocol),
        calculator.assess_oracle_risk(sample_protocol),
    ]

    score = calculator.calculate_overall_risk(factors)

    assert score.overall >= 0
    assert score.overall <= 10
    assert score.level in RiskLevel
    assert len(score.factors) == 4


def test_assess_protocol_full(calculator: RiskCalculator, sample_protocol: ProtocolData):
    """Test full protocol assessment."""
    assessment = calculator.assess_protocol(sample_protocol)

    assert assessment.protocol_name == "Test Protocol"
    assert assessment.protocol_slug == "test-protocol"
    assert assessment.score.overall >= 0
    assert len(assessment.score.factors) == 4
    assert assessment.tvl_analysis
    assert assessment.chain_analysis
    assert assessment.audit_analysis


def test_risk_level_classification(calculator: RiskCalculator):
    """Test risk level thresholds."""
    from src.models.schemas import RiskFactor, RiskScore

    # Low risk
    low_factors = [RiskFactor(name="Test", score=2.0, weight=1.0, description="test")]
    low_score = calculator.calculate_overall_risk(low_factors)
    assert low_score.level == RiskLevel.LOW

    # Medium risk
    med_factors = [RiskFactor(name="Test", score=4.0, weight=1.0, description="test")]
    med_score = calculator.calculate_overall_risk(med_factors)
    assert med_score.level == RiskLevel.MEDIUM

    # High risk
    high_factors = [RiskFactor(name="Test", score=6.0, weight=1.0, description="test")]
    high_score = calculator.calculate_overall_risk(high_factors)
    assert high_score.level == RiskLevel.HIGH

    # Critical risk
    crit_factors = [RiskFactor(name="Test", score=8.5, weight=1.0, description="test")]
    crit_score = calculator.calculate_overall_risk(crit_factors)
    assert crit_score.level == RiskLevel.CRITICAL
