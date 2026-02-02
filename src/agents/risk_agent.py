"""Risk Agent - Analyzes protocol risk factors."""

from langchain_core.prompts import ChatPromptTemplate

from src.models.schemas import AgentState, ProtocolData, RiskAssessment
from src.tools.risk_metrics import RiskCalculator, get_calculator


RISK_AGENT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a DeFi risk analyst agent. Your role is to evaluate protocol risk
based on quantitative metrics and qualitative factors.

Risk factors to consider:
1. TVL size and stability - larger, more stable TVL indicates lower risk
2. Chain concentration - diversified chain presence reduces single-point-of-failure risk
3. Audit status - audited protocols have verified security
4. Oracle dependencies - reliance on price feeds introduces oracle risk
5. Historical incidents - past exploits or issues

When assessing risk:
- Use data-driven analysis with specific metrics
- Provide clear reasoning for risk ratings
- Highlight both strengths and concerns
- Be objective and balanced in assessments
""",
    ),
    ("human", "{input}"),
])


class RiskAgent:
    """Agent responsible for protocol risk analysis."""

    def __init__(self, calculator: RiskCalculator | None = None) -> None:
        self.calculator = calculator or get_calculator()
        self.name = "risk_agent"

    def assess_protocol(self, protocol: ProtocolData) -> RiskAssessment:
        """Perform risk assessment on a protocol."""
        return self.calculator.assess_protocol(protocol)

    def assess_protocols(
        self, protocols: dict[str, ProtocolData]
    ) -> dict[str, RiskAssessment]:
        """Assess multiple protocols."""
        return {slug: self.assess_protocol(data) for slug, data in protocols.items()}

    async def run(self, state: AgentState) -> AgentState:
        """Execute risk analysis step in the workflow."""
        protocol_data = state.get("protocol_data", {})

        if not protocol_data:
            return {
                **state,
                "error": "No protocol data available for risk analysis",
                "current_agent": self.name,
                "next_agent": None,
            }

        try:
            assessments = self.assess_protocols(protocol_data)

            # Add message about assessments
            messages = state.get("messages", [])
            message_lines = ["Risk analysis complete:"]

            for slug, assessment in assessments.items():
                score = assessment.score
                message_lines.append(
                    f"- {assessment.protocol_name}: {score.level.value.upper()} risk "
                    f"(score: {score.overall:.1f}/10)"
                )

                if assessment.warnings:
                    for warning in assessment.warnings[:2]:
                        message_lines.append(f"  ⚠️ {warning}")

            messages.append({
                "role": "assistant",
                "content": "\n".join(message_lines),
                "agent": self.name,
            })

            return {
                **state,
                "risk_assessments": assessments,
                "messages": messages,
                "current_agent": self.name,
                "next_agent": "report_agent",
                "error": None,
            }

        except Exception as e:
            return {
                **state,
                "error": f"Risk analysis failed: {e}",
                "current_agent": self.name,
                "next_agent": None,
            }

    def format_assessment(self, assessment: RiskAssessment) -> str:
        """Format risk assessment as human-readable report."""
        lines = [
            f"# Risk Assessment: {assessment.protocol_name}",
            "",
            f"## Overall Risk: {assessment.score.level.value.upper()}",
            f"**Score:** {assessment.score.overall:.1f}/10",
            "",
            "## Risk Factor Breakdown",
        ]

        for factor in assessment.score.factors:
            lines.append(f"### {factor.name}")
            lines.append(f"**Score:** {factor.score:.1f}/10 (weight: {factor.weight:.0%})")
            lines.append(f"**Summary:** {factor.description}")
            if factor.details:
                lines.append(f"**Details:** {factor.details}")
            lines.append("")

        lines.extend([
            "## TVL Analysis",
            assessment.tvl_analysis,
            "",
            "## Chain Distribution Analysis",
            assessment.chain_analysis,
            "",
            "## Audit Analysis",
            assessment.audit_analysis,
            "",
        ])

        if assessment.warnings:
            lines.append("## ⚠️ Warnings")
            for warning in assessment.warnings:
                lines.append(f"- {warning}")
            lines.append("")

        if assessment.recommendations:
            lines.append("## Recommendations")
            for rec in assessment.recommendations:
                lines.append(f"- {rec}")
            lines.append("")

        lines.append(f"_Assessment generated: {assessment.assessed_at.strftime('%Y-%m-%d %H:%M UTC')}_")

        return "\n".join(lines)

    def compare_assessments(
        self, assessments: dict[str, RiskAssessment]
    ) -> str:
        """Generate comparison summary for multiple assessments."""
        if len(assessments) < 2:
            return "Need at least 2 protocols to compare"

        sorted_assessments = sorted(
            assessments.values(),
            key=lambda a: a.score.overall,
        )

        lines = [
            "# Protocol Risk Comparison",
            "",
            "## Risk Ranking (lowest to highest)",
        ]

        for i, assessment in enumerate(sorted_assessments, 1):
            lines.append(
                f"{i}. **{assessment.protocol_name}**: "
                f"{assessment.score.level.value.upper()} ({assessment.score.overall:.1f}/10)"
            )

        lines.extend(["", "## Factor Comparison", ""])

        # Compare each factor
        factor_names = ["TVL Risk", "Chain Concentration", "Audit Status", "Oracle Risk"]

        for factor_name in factor_names:
            lines.append(f"### {factor_name}")
            for assessment in sorted_assessments:
                factor = next(
                    (f for f in assessment.score.factors if f.name == factor_name),
                    None,
                )
                if factor:
                    lines.append(f"- {assessment.protocol_name}: {factor.score:.1f}/10")
            lines.append("")

        # Recommendation
        lowest_risk = sorted_assessments[0]
        highest_risk = sorted_assessments[-1]

        lines.extend([
            "## Summary",
            f"**Lowest Risk:** {lowest_risk.protocol_name} ({lowest_risk.score.overall:.1f}/10)",
            f"**Highest Risk:** {highest_risk.protocol_name} ({highest_risk.score.overall:.1f}/10)",
        ])

        return "\n".join(lines)
