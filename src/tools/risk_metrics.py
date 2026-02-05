"""Risk calculation utilities for DeFi protocol analysis."""

import statistics
from datetime import datetime, timedelta

from src.models.schemas import (
    ChainBreakdown,
    IncidentSeverity,
    ProtocolData,
    RiskAssessment,
    RiskFactor,
    RiskLevel,
    RiskScore,
    TVLDataPoint,
)


class RiskCalculator:
    """Calculate risk metrics for DeFi protocols."""

    # Thresholds for risk scoring
    TVL_HIGH_THRESHOLD = 1_000_000_000  # $1B
    TVL_MEDIUM_THRESHOLD = 100_000_000  # $100M
    TVL_LOW_THRESHOLD = 10_000_000  # $10M

    VOLATILITY_LOW = 0.1  # 10%
    VOLATILITY_MEDIUM = 0.25  # 25%
    VOLATILITY_HIGH = 0.5  # 50%

    CONCENTRATION_LOW = 50  # 50% on one chain is concerning
    CONCENTRATION_HIGH = 80  # 80% on one chain is high risk

    def calculate_tvl_volatility(self, history: list[TVLDataPoint]) -> float:
        """Calculate TVL volatility as coefficient of variation."""
        if len(history) < 2:
            return 0.0

        tvls = [point.tvl for point in history if point.tvl > 0]
        if len(tvls) < 2:
            return 0.0

        mean = statistics.mean(tvls)
        if mean == 0:
            return 0.0

        stdev = statistics.stdev(tvls)
        return stdev / mean

    def calculate_tvl_trend(self, history: list[TVLDataPoint], days: int = 30) -> float:
        """Calculate TVL trend over specified days as percentage change."""
        if len(history) < 2:
            return 0.0

        cutoff = datetime.utcnow() - timedelta(days=days)
        recent = [p for p in history if p.date >= cutoff]

        if len(recent) < 2:
            recent = history[-min(len(history), 30) :]

        if len(recent) < 2:
            return 0.0

        start_tvl = recent[0].tvl
        end_tvl = recent[-1].tvl

        if start_tvl == 0:
            return 0.0

        return ((end_tvl - start_tvl) / start_tvl) * 100

    def calculate_chain_concentration(self, chain_tvls: list[ChainBreakdown]) -> float:
        """Calculate chain concentration (Herfindahl-Hirschman Index)."""
        if not chain_tvls:
            return 0.0

        # HHI: sum of squared market shares
        hhi = sum((c.percentage / 100) ** 2 for c in chain_tvls)
        # Normalize to 0-100 scale
        return hhi * 100

    def assess_tvl_risk(self, protocol: ProtocolData) -> RiskFactor:
        """Assess risk based on TVL size and trends."""
        tvl = protocol.tvl
        volatility = self.calculate_tvl_volatility(protocol.tvl_history)
        trend = protocol.tvl_change_30d or self.calculate_tvl_trend(protocol.tvl_history)

        # Size component (larger = safer)
        if tvl >= self.TVL_HIGH_THRESHOLD:
            size_score = 2.0
            size_detail = f"Large TVL (${tvl / 1e9:.2f}B) indicates maturity"
        elif tvl >= self.TVL_MEDIUM_THRESHOLD:
            size_score = 4.0
            size_detail = f"Medium TVL (${tvl / 1e6:.0f}M)"
        elif tvl >= self.TVL_LOW_THRESHOLD:
            size_score = 6.0
            size_detail = f"Lower TVL (${tvl / 1e6:.0f}M) - higher relative risk"
        else:
            size_score = 8.0
            size_detail = f"Small TVL (${tvl / 1e6:.2f}M) - early stage risk"

        # Volatility component
        if volatility <= self.VOLATILITY_LOW:
            vol_score = 2.0
            vol_detail = f"Low volatility ({volatility:.1%})"
        elif volatility <= self.VOLATILITY_MEDIUM:
            vol_score = 5.0
            vol_detail = f"Moderate volatility ({volatility:.1%})"
        else:
            vol_score = 8.0
            vol_detail = f"High volatility ({volatility:.1%})"

        # Trend component (declining is bad)
        if trend >= 10:
            trend_score = 2.0
            trend_detail = f"Strong growth ({trend:+.1f}% 30d)"
        elif trend >= -10:
            trend_score = 4.0
            trend_detail = f"Stable ({trend:+.1f}% 30d)"
        elif trend >= -30:
            trend_score = 6.0
            trend_detail = f"Declining ({trend:+.1f}% 30d)"
        else:
            trend_score = 9.0
            trend_detail = f"Sharp decline ({trend:+.1f}% 30d)"

        # Weighted average
        final_score = size_score * 0.4 + vol_score * 0.3 + trend_score * 0.3

        tvl_b = tvl / 1e9
        desc = f"TVL: ${tvl_b:.2f}B | Volatility: {volatility:.1%} | 30d: {trend:+.1f}%"
        return RiskFactor(
            name="TVL Risk",
            score=final_score,
            weight=0.30,
            description=desc,
            details=f"{size_detail}. {vol_detail}. {trend_detail}.",
        )

    def assess_chain_risk(self, protocol: ProtocolData) -> RiskFactor:
        """Assess risk based on chain diversification."""
        chain_tvls = protocol.chain_tvls
        num_chains = len(protocol.chains)

        if not chain_tvls:
            return RiskFactor(
                name="Chain Concentration",
                score=5.0,
                weight=0.25,
                description="Unable to analyze chain distribution",
                details="Chain TVL breakdown not available",
            )

        concentration = self.calculate_chain_concentration(chain_tvls)
        top_chain_pct = chain_tvls[0].percentage if chain_tvls else 100

        # Score based on concentration
        if top_chain_pct >= self.CONCENTRATION_HIGH:
            score = 7.0
            level = "High concentration"
        elif top_chain_pct >= self.CONCENTRATION_LOW:
            score = 5.0
            level = "Moderate concentration"
        else:
            score = 3.0
            level = "Well diversified"

        # Bonus for multi-chain
        if num_chains >= 5:
            score = max(2.0, score - 1.5)
        elif num_chains >= 3:
            score = max(2.0, score - 0.5)

        top_chains = chain_tvls[:3]
        chain_summary = ", ".join(f"{c.chain}: {c.percentage:.1f}%" for c in top_chains)

        return RiskFactor(
            name="Chain Concentration",
            score=score,
            weight=0.25,
            description=f"{num_chains} chains | Top: {chain_summary}",
            details=f"{level}. HHI: {concentration:.0f}/10000. "
            f"Top chain ({chain_tvls[0].chain}) has {top_chain_pct:.1f}% of TVL.",
        )

    def assess_audit_risk(self, protocol: ProtocolData) -> RiskFactor:
        """Assess risk based on audit status."""
        has_audits = len(protocol.audits) > 0 or len(protocol.audit_links) > 0
        num_audits = len(protocol.audit_links) if protocol.audit_links else (1 if has_audits else 0)

        if num_audits >= 3:
            score = 2.0
            description = f"Multiple audits ({num_audits})"
            details = "Well-audited protocol with multiple security reviews"
        elif num_audits >= 1:
            score = 4.0
            description = f"Audited ({num_audits} audit{'s' if num_audits > 1 else ''})"
            details = "Has security audit(s) on record"
        else:
            score = 8.0
            description = "No audits found"
            details = "No public audit records found - higher smart contract risk"

        return RiskFactor(
            name="Audit Status",
            score=score,
            weight=0.20,
            description=description,
            details=details,
        )

    def assess_oracle_risk(self, protocol: ProtocolData) -> RiskFactor:
        """Assess risk based on oracle usage."""
        oracles = protocol.oracles

        trusted_oracles = {"chainlink", "pyth", "redstone", "band", "api3", "uma"}
        uses_trusted = any(o.lower() in trusted_oracles for o in oracles)

        if not oracles:
            # Many protocols don't need oracles
            return RiskFactor(
                name="Oracle Risk",
                score=4.0,
                weight=0.10,
                description="No oracle dependency detected",
                details="Protocol may not require price feeds or uses internal pricing",
            )

        if uses_trusted and len(oracles) >= 1:
            score = 2.0
            description = f"Uses trusted oracle(s): {', '.join(oracles[:3])}"
            details = "Relies on established oracle infrastructure"
        elif len(oracles) >= 1:
            score = 5.0
            description = f"Uses oracle(s): {', '.join(oracles[:3])}"
            details = "Oracle dependency present - verify oracle security"
        else:
            score = 6.0
            description = "Unknown oracle status"
            details = "Unable to determine oracle usage"

        return RiskFactor(
            name="Oracle Risk",
            score=score,
            weight=0.10,
            description=description,
            details=details,
        )

    def assess_incident_risk(self, protocol: ProtocolData) -> RiskFactor:
        """Assess risk based on historical incidents."""
        incidents = protocol.incidents

        if not incidents:
            return RiskFactor(
                name="Incident History",
                score=2.0,
                weight=0.15,
                description="No documented security incidents",
                details="Clean security track record with no major exploits on record",
            )

        # Calculate recency score (more recent = worse)
        now = datetime.utcnow()
        recency_score = 0.0
        for incident in incidents:
            days_ago = (now - incident.date).days
            if days_ago <= 30:
                recency_score += 10
            elif days_ago <= 180:
                recency_score += 8
            elif days_ago <= 365:
                recency_score += 5
            elif days_ago <= 730:
                recency_score += 3
            else:
                recency_score += 1

        # Normalize recency score (cap at 10)
        recency_score = min(10.0, recency_score / len(incidents))

        # Calculate severity score
        severity_score = 0.0
        severity_weights = {
            IncidentSeverity.CRITICAL: 10,
            IncidentSeverity.HIGH: 7,
            IncidentSeverity.MEDIUM: 4,
            IncidentSeverity.LOW: 2,
        }
        for incident in incidents:
            severity_score += severity_weights.get(incident.severity, 5)

        # Normalize severity score
        severity_score = min(10.0, severity_score / len(incidents))

        # Calculate resolution score (unfixed = higher risk)
        unfixed_count = sum(1 for i in incidents if not i.fixed)
        resolution_score = min(10.0, (unfixed_count / len(incidents)) * 10)

        # Final weighted score: 50% recency + 40% severity + 10% resolution
        final_score = (recency_score * 0.5) + (severity_score * 0.4) + (resolution_score * 0.1)

        # Generate description
        critical_count = sum(1 for i in incidents if i.severity == IncidentSeverity.CRITICAL)
        high_count = sum(1 for i in incidents if i.severity == IncidentSeverity.HIGH)
        total_loss = sum(i.amount_lost_usd for i in incidents)

        if critical_count > 0:
            description = f"{len(incidents)} incident(s), {critical_count} critical (${total_loss / 1e6:.1f}M lost)"
        elif high_count > 0:
            description = f"{len(incidents)} incident(s), {high_count} high severity (${total_loss / 1e6:.1f}M lost)"
        else:
            description = f"{len(incidents)} incident(s) (${total_loss / 1e6:.1f}M lost)"

        # Generate details
        most_recent = incidents[0]
        days_since = (now - most_recent.date).days
        details = f"Most recent incident: {most_recent.title} ({days_since} days ago). "

        if unfixed_count > 0:
            details += f"{unfixed_count} incident(s) not confirmed fixed. "

        if critical_count > 0:
            details += f"{critical_count} critical-severity exploit(s) indicate significant security risks."
        elif high_count > 0:
            details += f"{high_count} high-severity incident(s) warrant careful review."
        else:
            details += "Lower severity incidents - review for patterns."

        return RiskFactor(
            name="Incident History",
            score=final_score,
            weight=0.15,
            description=description,
            details=details,
        )

    def calculate_overall_risk(self, factors: list[RiskFactor]) -> RiskScore:
        """Calculate weighted overall risk score."""
        if not factors:
            return RiskScore(overall=5.0, level=RiskLevel.MEDIUM, factors=[])

        total_weight = sum(f.weight for f in factors)
        if total_weight == 0:
            return RiskScore(overall=5.0, level=RiskLevel.MEDIUM, factors=factors)

        weighted_sum = sum(f.score * f.weight for f in factors)
        overall = weighted_sum / total_weight

        return RiskScore.from_score(overall, factors)

    def assess_protocol(self, protocol: ProtocolData) -> RiskAssessment:
        """Perform complete risk assessment on a protocol."""
        factors = [
            self.assess_tvl_risk(protocol),
            self.assess_chain_risk(protocol),
            self.assess_audit_risk(protocol),
            self.assess_oracle_risk(protocol),
            self.assess_incident_risk(protocol),
        ]

        score = self.calculate_overall_risk(factors)

        # Generate analysis summaries
        tvl_factor = next(f for f in factors if f.name == "TVL Risk")
        chain_factor = next(f for f in factors if f.name == "Chain Concentration")
        audit_factor = next(f for f in factors if f.name == "Audit Status")
        incident_factor = next(f for f in factors if f.name == "Incident History")

        tvl_analysis = f"{tvl_factor.description}. {tvl_factor.details}"
        chain_analysis = f"{chain_factor.description}. {chain_factor.details}"
        audit_analysis = f"{audit_factor.description}. {audit_factor.details}"
        incident_analysis = f"{incident_factor.description}. {incident_factor.details}"

        # Generate recommendations
        recommendations: list[str] = []
        warnings: list[str] = []

        if score.level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            warnings.append(
                f"Protocol has {score.level.value} overall risk (score: {score.overall:.1f}/10)"
            )

        for factor in factors:
            if factor.score >= 7:
                warnings.append(f"High {factor.name.lower()}: {factor.description}")
            elif factor.score >= 5:
                recommendations.append(f"Monitor {factor.name.lower()}: {factor.description}")

        if not protocol.audit_links:
            recommendations.append("Verify audit status through official protocol channels")

        if len(protocol.chains) == 1:
            recommendations.append("Single-chain deployment - monitor chain-specific risks")

        return RiskAssessment(
            protocol_name=protocol.name,
            protocol_slug=protocol.slug,
            score=score,
            tvl_analysis=tvl_analysis,
            chain_analysis=chain_analysis,
            audit_analysis=audit_analysis,
            incident_analysis=incident_analysis,
            recommendations=recommendations,
            warnings=warnings,
        )


# Singleton instance
_calculator: RiskCalculator | None = None


def get_calculator() -> RiskCalculator:
    """Get or create RiskCalculator singleton."""
    global _calculator
    if _calculator is None:
        _calculator = RiskCalculator()
    return _calculator
