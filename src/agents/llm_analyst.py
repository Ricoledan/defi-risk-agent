"""LLM-powered analysis agent for enhanced risk insights."""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from src.models.schemas import ProtocolData, RiskAssessment


def _get_factor_score(assessment: RiskAssessment, name: str) -> str:
    """Extract a factor score by name from the assessment."""
    for f in assessment.score.factors:
        if f.name == name:
            return str(f.score)
    return "N/A"


ANALYST_SYSTEM_PROMPT = """You are a DeFi risk analyst. Analyze the provided protocol \
data and risk assessment to give actionable insights.

Your analysis should be:
- Concise (2-3 paragraphs max)
- Data-driven (reference specific numbers)
- Balanced (mention both strengths and concerns)
- Actionable (what should an investor consider?)

Do not make up information. Only reference data provided to you.
Do not give financial advice. Frame insights as considerations, not recommendations.
"""


def format_protocol_for_llm(protocol: ProtocolData, assessment: RiskAssessment) -> str:
    """Format protocol data for LLM consumption."""
    chain_info = ""
    if protocol.chain_tvls:
        top_chains = protocol.chain_tvls[:5]
        chain_info = "\n".join(
            f"  - {c.chain}: ${c.tvl / 1e9:.2f}B ({c.percentage:.1f}%)" for c in top_chains
        )

    return f"""
Protocol: {protocol.name}
Category: {protocol.category or "Unknown"}
Symbol: {protocol.symbol or "N/A"}

TVL Metrics:
- Current TVL: ${protocol.tvl / 1e9:.2f}B
- 24h Change: {protocol.tvl_change_1d or 0:+.2f}%
- 7d Change: {protocol.tvl_change_7d or 0:+.2f}%
- 30d Change: {protocol.tvl_change_30d or 0:+.2f}%

Chain Distribution ({len(protocol.chains)} chains):
{chain_info}

Security:
- Audits on record: {len(protocol.audit_links) if protocol.audit_links else 0}
- Oracles: {", ".join(protocol.oracles) if protocol.oracles else "None detected"}

Risk Assessment:
- Overall Score: {assessment.score.overall:.1f}/10 ({assessment.score.level.value.upper()})
- TVL Risk: {_get_factor_score(assessment, "TVL Risk")}/10
- Chain Concentration: {_get_factor_score(assessment, "Chain Concentration")}/10
- Audit Status: {_get_factor_score(assessment, "Audit Status")}/10
- Oracle Risk: {_get_factor_score(assessment, "Oracle Risk")}/10

Warnings: {", ".join(assessment.warnings) if assessment.warnings else "None"}
"""


class LLMAnalyst:
    """LLM-powered analyst for enhanced risk insights."""

    def __init__(self, llm: BaseChatModel | None = None):
        self._llm = llm

    @property
    def llm(self) -> BaseChatModel:
        """Lazy-load LLM to avoid import errors when Ollama not available."""
        if self._llm is None:
            from src.llm.provider import get_llm

            self._llm = get_llm()
        return self._llm

    def analyze(self, protocol: ProtocolData, assessment: RiskAssessment) -> str:
        """Generate LLM-powered analysis for a protocol."""
        protocol_info = format_protocol_for_llm(protocol, assessment)

        messages = [
            SystemMessage(content=ANALYST_SYSTEM_PROMPT),
            HumanMessage(
                content=f"Analyze this DeFi protocol and provide insights:\n{protocol_info}"
            ),
        ]

        response = self.llm.invoke(messages)
        return response.content

    def compare(
        self,
        protocols: list[ProtocolData],
        assessments: list[RiskAssessment],
    ) -> str:
        """Generate LLM-powered comparison analysis."""
        protocol_infos = []
        for protocol, assessment in zip(protocols, assessments):
            protocol_infos.append(format_protocol_for_llm(protocol, assessment))

        combined_info = "\n---\n".join(protocol_infos)

        prompt = (
            "Compare these DeFi protocols and provide insights "
            f"on their relative risk profiles:\n{combined_info}"
        )
        messages = [
            SystemMessage(content=ANALYST_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        response = self.llm.invoke(messages)
        return response.content

    def answer_question(
        self,
        question: str,
        protocol: ProtocolData,
        assessment: RiskAssessment,
    ) -> str:
        """Answer a specific question about a protocol."""
        protocol_info = format_protocol_for_llm(protocol, assessment)

        prompt = (
            f"Based on this protocol data:\n{protocol_info}\n\nAnswer this question: {question}"
        )
        messages = [
            SystemMessage(content=ANALYST_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]

        response = self.llm.invoke(messages)
        return response.content
