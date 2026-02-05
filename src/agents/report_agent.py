"""Report Agent - Synthesizes findings into professional reports."""

from langchain_core.prompts import ChatPromptTemplate

from src.models.schemas import (
    AgentState,
    ComparisonReport,
    IncidentSeverity,
    ProtocolData,
    RiskAssessment,
    RiskReport,
)

REPORT_AGENT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a DeFi report synthesis agent. Your role is to create
professional, enterprise-grade risk reports suitable for institutional review.

Report requirements:
1. Executive Summary - concise overview for decision-makers
2. Data Provenance - clear citation of all data sources
3. Methodology Transparency - explain how risk scores are calculated
4. Balanced Analysis - present both risks and mitigating factors
5. Actionable Insights - provide clear recommendations

Write in a professional tone suitable for EY-style advisory work.
Avoid speculation; stick to data-supported conclusions.
""",
        ),
        ("human", "{input}"),
    ]
)


class ReportAgent:
    """Agent responsible for generating risk reports."""

    def __init__(self) -> None:
        self.name = "report_agent"
        self.data_sources = [
            "DefiLlama API (https://defillama.com)",
            "On-chain TVL data aggregated across chains",
            "Public audit records and security disclosures",
            "Rekt.news Incident Database (https://rekt.news/leaderboard)",
        ]

    def generate_executive_summary(self, protocol: ProtocolData, assessment: RiskAssessment) -> str:
        """Generate executive summary for a protocol."""
        risk_level = assessment.score.level.value.upper()
        score = assessment.score.overall

        summary_parts = [
            f"{protocol.name} is a {protocol.category or 'DeFi'} protocol "
            f"with ${protocol.tvl / 1e9:.2f}B in Total Value Locked across "
            f"{len(protocol.chains)} blockchain{'s' if len(protocol.chains) > 1 else ''}.",
            "",
            f"**Risk Assessment:** {risk_level} (Score: {score:.1f}/10)",
            "",
        ]

        # Key findings
        findings = []

        # TVL trend
        if protocol.tvl_change_30d is not None:
            if protocol.tvl_change_30d >= 10:
                findings.append(f"Strong TVL growth ({protocol.tvl_change_30d:+.1f}% 30d)")
            elif protocol.tvl_change_30d <= -20:
                findings.append(f"Significant TVL decline ({protocol.tvl_change_30d:+.1f}% 30d)")

        # Chain diversification
        if len(protocol.chains) >= 5:
            findings.append(f"Well-diversified across {len(protocol.chains)} chains")
        elif len(protocol.chains) == 1:
            findings.append("Single-chain deployment limits diversification")

        # Audit status
        if protocol.audit_links:
            findings.append(f"{len(protocol.audit_links)} security audit(s) on record")
        else:
            findings.append("No public audit records identified")

        # Add incident findings
        if protocol.incidents:
            critical = sum(1 for i in protocol.incidents if i.severity == IncidentSeverity.CRITICAL)
            if critical > 0:
                findings.append(f"{critical} critical incident(s) in history")
            else:
                findings.append(f"{len(protocol.incidents)} historical incident(s)")
        else:
            findings.append("No documented security incidents")

        if findings:
            summary_parts.append("**Key Findings:**")
            for finding in findings:
                summary_parts.append(f"- {finding}")

        # Risk warnings
        if assessment.warnings:
            summary_parts.append("")
            summary_parts.append("**Risk Warnings:**")
            for warning in assessment.warnings[:3]:
                summary_parts.append(f"- {warning}")

        return "\n".join(summary_parts)

    def generate_detailed_analysis(self, protocol: ProtocolData, assessment: RiskAssessment) -> str:
        """Generate detailed analysis section."""
        sections = []

        # Protocol Overview
        sections.append("## Protocol Overview")
        sections.append(f"**Name:** {protocol.name}")
        sections.append(f"**Category:** {protocol.category or 'Unknown'}")
        sections.append(f"**Symbol:** {protocol.symbol or 'N/A'}")
        if protocol.description:
            sections.append(f"**Description:** {protocol.description[:300]}...")
        sections.append("")

        # TVL Analysis
        sections.append("## Total Value Locked Analysis")
        sections.append(f"**Current TVL:** ${protocol.tvl / 1e9:.2f}B")
        sections.append("")
        sections.append("### TVL Trends")
        sections.append(f"- 24-hour change: {protocol.tvl_change_1d or 0:+.2f}%")
        sections.append(f"- 7-day change: {protocol.tvl_change_7d or 0:+.2f}%")
        sections.append(f"- 30-day change: {protocol.tvl_change_30d or 0:+.2f}%")
        sections.append("")
        sections.append(assessment.tvl_analysis)
        sections.append("")

        # Chain Distribution
        sections.append("## Chain Distribution Analysis")
        sections.append(f"**Chains Supported:** {len(protocol.chains)}")
        sections.append("")
        if protocol.chain_tvls:
            sections.append("### TVL by Chain")
            for chain in protocol.chain_tvls[:10]:
                sections.append(
                    f"- {chain.chain}: ${chain.tvl / 1e9:.2f}B ({chain.percentage:.1f}%)"
                )
        sections.append("")
        sections.append(assessment.chain_analysis)
        sections.append("")

        # Security Analysis
        sections.append("## Security Analysis")
        sections.append("### Audit Status")
        if protocol.audit_links:
            sections.append(f"**Audits Found:** {len(protocol.audit_links)}")
            for link in protocol.audit_links[:5]:
                sections.append(f"- {link}")
        else:
            sections.append("No public audit records were identified for this protocol.")
        sections.append("")
        sections.append(assessment.audit_analysis)
        sections.append("")

        # Incident History
        sections.append("## Incident History")
        if protocol.incidents:
            sections.append(f"**Total Incidents:** {len(protocol.incidents)}")
            sections.append("")
            sections.append("### Documented Exploits")

            for incident in protocol.incidents[:5]:  # Show 5 most recent
                sections.append(f"\n#### {incident.title}")
                sections.append(f"- **Date:** {incident.date.strftime('%B %d, %Y')}")
                sections.append(f"- **Amount Lost:** ${incident.amount_lost_usd / 1e6:.2f}M")
                sections.append(f"- **Severity:** {incident.severity.value.upper()}")
                if incident.details_url:
                    sections.append(f"- **Details:** {incident.details_url}")

            if len(protocol.incidents) > 5:
                sections.append(f"\n*({len(protocol.incidents) - 5} additional incidents not shown)*")
        else:
            sections.append("No historical incidents found.")

        sections.append(f"\n{assessment.incident_analysis}\n")

        # Oracle Dependencies
        if protocol.oracles:
            sections.append("### Oracle Dependencies")
            sections.append(f"**Oracles Used:** {', '.join(protocol.oracles)}")
            sections.append("")

        # Risk Score Breakdown
        sections.append("## Risk Score Methodology")
        sections.append(
            "Risk scores are calculated on a 0-10 scale where lower scores indicate lower risk."
        )
        sections.append("")
        sections.append("### Factor Weights")
        for factor in assessment.score.factors:
            sections.append(f"- **{factor.name}:** {factor.weight:.0%} weight")
        sections.append("")

        sections.append("### Individual Factor Scores")
        for factor in assessment.score.factors:
            sections.append(f"#### {factor.name}: {factor.score:.1f}/10")
            sections.append(f"{factor.description}")
            if factor.details:
                sections.append(f"*{factor.details}*")
            sections.append("")

        return "\n".join(sections)

    def generate_report(self, protocol: ProtocolData, assessment: RiskAssessment) -> RiskReport:
        """Generate complete risk report."""
        return RiskReport(
            protocol=protocol,
            assessment=assessment,
            executive_summary=self.generate_executive_summary(protocol, assessment),
            detailed_analysis=self.generate_detailed_analysis(protocol, assessment),
            data_sources=self.data_sources,
        )

    def generate_comparison_report(
        self,
        protocols: list[ProtocolData],
        assessments: list[RiskAssessment],
    ) -> ComparisonReport:
        """Generate comparison report for multiple protocols."""
        # Sort by risk score
        sorted_pairs = sorted(
            zip(protocols, assessments),
            key=lambda x: x[1].score.overall,
        )

        # Generate comparison summary
        summary_lines = [
            "## Comparative Risk Analysis",
            "",
            f"This report compares {len(protocols)} DeFi protocols across key risk dimensions.",
            "",
            "### Risk Ranking",
        ]

        for i, (protocol, assessment) in enumerate(sorted_pairs, 1):
            summary_lines.append(
                f"{i}. **{protocol.name}** - {assessment.score.level.value.upper()} "
                f"(Score: {assessment.score.overall:.1f}/10)"
            )

        summary_lines.extend(["", "### TVL Comparison"])
        for protocol, _ in sorted_pairs:
            summary_lines.append(f"- {protocol.name}: ${protocol.tvl / 1e9:.2f}B")

        summary_lines.extend(["", "### Chain Diversification"])
        for protocol, _ in sorted_pairs:
            summary_lines.append(f"- {protocol.name}: {len(protocol.chains)} chains")

        summary_lines.extend(["", "### Audit Status"])
        for protocol, _ in sorted_pairs:
            audit_count = len(protocol.audit_links) if protocol.audit_links else 0
            summary_lines.append(f"- {protocol.name}: {audit_count} audits")

        # Generate recommendation
        lowest_risk = sorted_pairs[0]
        highest_risk = sorted_pairs[-1]

        lowest_score = lowest_risk[1].score.overall
        recommendation = (
            f"Based on quantitative risk analysis, **{lowest_risk[0].name}** presents "
            f"the lowest overall risk profile with a score of {lowest_score:.1f}/10. "
        )

        if highest_risk[1].score.overall - lowest_risk[1].score.overall > 2:
            recommendation += (
                f"**{highest_risk[0].name}** shows notably higher risk "
                f"({highest_risk[1].score.overall:.1f}/10) and warrants additional due diligence."
            )
        else:
            recommendation += "All analyzed protocols show relatively comparable risk profiles."

        return ComparisonReport(
            protocols=protocols,
            assessments=assessments,
            comparison_summary="\n".join(summary_lines),
            recommendation=recommendation,
        )

    async def run(self, state: AgentState) -> AgentState:
        """Execute report generation step in the workflow."""
        protocol_data = state.get("protocol_data", {})
        risk_assessments = state.get("risk_assessments", {})

        if not protocol_data or not risk_assessments:
            return {
                **state,
                "error": "Missing data or assessments for report generation",
                "current_agent": self.name,
                "next_agent": None,
            }

        try:
            messages = state.get("messages", [])

            # Generate appropriate report type
            if len(protocol_data) == 1:
                slug = list(protocol_data.keys())[0]
                protocol = protocol_data[slug]
                assessment = risk_assessments[slug]
                report = self.generate_report(protocol, assessment)

                messages.append(
                    {
                        "role": "assistant",
                        "content": f"Generated risk report for {protocol.name}",
                        "agent": self.name,
                    }
                )
            else:
                protocols = list(protocol_data.values())
                assessments = [risk_assessments[p.slug] for p in protocols]
                report = self.generate_comparison_report(protocols, assessments)

                protocol_names = [p.name for p in protocols]
                messages.append(
                    {
                        "role": "assistant",
                        "content": f"Generated comparison report for: {', '.join(protocol_names)}",
                        "agent": self.name,
                    }
                )

            return {
                **state,
                "report": report,
                "messages": messages,
                "current_agent": self.name,
                "next_agent": None,  # End of workflow
                "error": None,
            }

        except Exception as e:
            return {
                **state,
                "error": f"Report generation failed: {e}",
                "current_agent": self.name,
                "next_agent": None,
            }

    def format_report(self, report: RiskReport) -> str:
        """Format risk report as markdown."""
        lines = [
            f"# DeFi Risk Report: {report.protocol.name}",
            "",
            f"_Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}_",
            "",
            "---",
            "",
            "# Executive Summary",
            "",
            report.executive_summary,
            "",
            "---",
            "",
            report.detailed_analysis,
            "",
            "---",
            "",
            "## Data Sources",
        ]

        for source in report.data_sources:
            lines.append(f"- {source}")

        lines.extend(
            [
                "",
                "---",
                "",
                "*This report is generated algorithmically based on publicly available data. "
                "It should not be considered financial advice. Always conduct independent "
                "research before making investment decisions.*",
            ]
        )

        return "\n".join(lines)

    def format_comparison_report(self, report: ComparisonReport) -> str:
        """Format comparison report as markdown."""
        protocol_names = [p.name for p in report.protocols]

        lines = [
            f"# DeFi Risk Comparison: {' vs '.join(protocol_names)}",
            "",
            f"_Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M UTC')}_",
            "",
            "---",
            "",
            report.comparison_summary,
            "",
            "---",
            "",
            "## Recommendation",
            "",
            report.recommendation,
            "",
            "---",
            "",
            "## Data Sources",
            "- DefiLlama API (https://defillama.com)",
            "- On-chain TVL data aggregated across chains",
            "",
            "---",
            "",
            "*This report is generated algorithmically based on publicly available data. "
            "It should not be considered financial advice.*",
        ]

        return "\n".join(lines)
