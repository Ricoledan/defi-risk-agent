"""Pydantic models for DeFi risk analysis."""

from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class RiskLevel(str, Enum):
    """Risk level classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ChainBreakdown(BaseModel):
    """TVL breakdown by chain."""

    chain: str
    tvl: float = Field(ge=0, description="Total Value Locked in USD")
    percentage: float = Field(ge=0, le=100, description="Percentage of total TVL")


class TVLDataPoint(BaseModel):
    """Historical TVL data point."""

    date: datetime
    tvl: float = Field(ge=0)


class ProtocolData(BaseModel):
    """Protocol data from DefiLlama."""

    name: str
    slug: str
    symbol: str | None = None
    category: str | None = None
    description: str | None = None
    url: str | None = None
    logo: str | None = None
    tvl: float = Field(ge=0, description="Current TVL in USD")
    tvl_change_1d: float | None = Field(default=None, description="24h TVL change percentage")
    tvl_change_7d: float | None = Field(default=None, description="7d TVL change percentage")
    tvl_change_30d: float | None = Field(default=None, description="30d TVL change percentage")
    chains: list[str] = Field(default_factory=list)
    chain_tvls: list[ChainBreakdown] = Field(default_factory=list)
    tvl_history: list[TVLDataPoint] = Field(default_factory=list)
    audits: list[str] = Field(default_factory=list, description="List of audit firms")
    audit_links: list[str] = Field(default_factory=list)
    oracles: list[str] = Field(default_factory=list)
    gecko_id: str | None = None
    twitter: str | None = None
    mcap: float | None = None
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class RiskFactor(BaseModel):
    """Individual risk factor assessment."""

    name: str
    score: float = Field(ge=0, le=10, description="Risk score from 0-10")
    weight: float = Field(ge=0, le=1, description="Weight in overall calculation")
    description: str
    details: str | None = None


class RiskScore(BaseModel):
    """Overall risk score with breakdown."""

    overall: float = Field(ge=0, le=10, description="Overall risk score 0-10")
    level: RiskLevel
    factors: list[RiskFactor] = Field(default_factory=list)

    @classmethod
    def from_score(cls, score: float, factors: list[RiskFactor]) -> "RiskScore":
        """Create RiskScore from numerical score."""
        if score <= 3:
            level = RiskLevel.LOW
        elif score <= 5:
            level = RiskLevel.MEDIUM
        elif score <= 7:
            level = RiskLevel.HIGH
        else:
            level = RiskLevel.CRITICAL
        return cls(overall=score, level=level, factors=factors)


class RiskAssessment(BaseModel):
    """Complete risk assessment for a protocol."""

    protocol_name: str
    protocol_slug: str
    score: RiskScore
    tvl_analysis: str
    chain_analysis: str
    audit_analysis: str
    recommendations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    assessed_at: datetime = Field(default_factory=datetime.utcnow)


class RiskReport(BaseModel):
    """Final risk report with executive summary."""

    protocol: ProtocolData
    assessment: RiskAssessment
    executive_summary: str
    detailed_analysis: str
    data_sources: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ComparisonReport(BaseModel):
    """Side-by-side protocol comparison report."""

    protocols: list[ProtocolData]
    assessments: list[RiskAssessment]
    comparison_summary: str
    recommendation: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# LangGraph State Models


class AgentMessage(TypedDict):
    """Message in agent conversation."""

    role: str
    content: str
    agent: str | None


class AgentState(TypedDict):
    """State for LangGraph workflow."""

    messages: Annotated[list[AgentMessage], "Conversation messages"]
    query: str
    protocol_names: list[str]
    protocol_data: dict[str, ProtocolData]
    risk_assessments: dict[str, RiskAssessment]
    report: RiskReport | ComparisonReport | None
    current_agent: str
    next_agent: str | None
    error: str | None


# API Request/Response Models


class AnalyzeRequest(BaseModel):
    """Request to analyze a protocol."""

    protocol: str = Field(min_length=1, description="Protocol name or slug")


class CompareRequest(BaseModel):
    """Request to compare protocols."""

    protocols: list[str] = Field(
        min_length=2, max_length=5, description="Protocol names to compare"
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
