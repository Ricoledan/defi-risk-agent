# DeFi Risk Analysis Agent

A multi-agent system built with LangGraph that analyzes DeFi protocol risk using on-chain data from DefiLlama and historical incident data from Rekt.news.

## The Problem

Decentralized Finance (DeFi) protocols manage billions of dollars in user funds, yet assessing their risk remains challenging:

1. **Information Fragmentation** - Protocol data is scattered across multiple sources (on-chain data, audit reports, documentation, social channels)
2. **No Standardized Risk Framework** - Unlike traditional finance, DeFi lacks consistent risk rating methodologies
3. **Rapid Evolution** - New protocols launch daily; TVL and chain deployments change constantly
4. **Technical Complexity** - Understanding smart contract risk requires specialized knowledge

Investors, institutions, and developers need a systematic way to evaluate protocol risk before allocating capital or building integrations.

## The Solution

This project provides an automated risk analysis pipeline that:

- Aggregates protocol data from DefiLlama (TVL, chain distribution, audit status)
- Integrates historical exploit/incident data from Rekt.news
- Applies a quantitative risk scoring methodology across five dimensions
- Optionally enhances reports with LLM-powered insights (Ollama, OpenAI, or Anthropic)
- Generates professional reports with clear explanations and data provenance
- Exposes results via CLI, REST API, and Python library

The multi-agent architecture allows each component to specialize in its domain while the supervisor coordinates the overall workflow.

## How It Works

### Architecture

```mermaid
flowchart TD
    A[User Query] --> B[Supervisor Agent]
    B --> |Parse & Route| C[Data Agent]
    C --> |Fetch from DefiLlama & Rekt.news| D[Risk Agent]
    D --> |Calculate Scores| E[Report Agent]
    E --> F[Risk Report]
    E -.-> |Optional| G[LLM Analyst]
    G --> F

    B -.-> |Error| H[End with Error]
    C -.-> |Protocol Not Found| H

    subgraph "Data Agent"
        C1[TVL & Trends]
        C2[Chain Breakdown]
        C3[Audit Links]
        C4[Oracle Info]
        C5[Incident History]
    end

    subgraph "Risk Agent"
        D1[TVL Risk: 30%]
        D2[Chain Risk: 25%]
        D3[Audit Risk: 20%]
        D4[Oracle Risk: 10%]
        D5[Incident Risk: 15%]
    end
```

### Agent Responsibilities

| Agent | Role | Input | Output |
|-------|------|-------|--------|
| **Supervisor** | Query parsing, workflow routing | User query string | Protocol names, workflow intent |
| **Data Agent** | External data fetching | Protocol names | `ProtocolData` objects (DefiLlama + Rekt.news) |
| **Risk Agent** | Risk score calculation | Protocol data | `RiskAssessment` objects |
| **Report Agent** | Report generation | Data + Assessments | Formatted `RiskReport` |
| **LLM Analyst** | AI-powered insights (optional) | Protocol data + Assessment | Natural language analysis |

### LangGraph Workflow

The agents are orchestrated using [LangGraph](https://github.com/langchain-ai/langgraph), a framework for building stateful, multi-step AI applications. The workflow is defined as a directed graph:

```mermaid
stateDiagram-v2
    [*] --> Supervisor
    Supervisor --> DataAgent: protocols found
    Supervisor --> [*]: error (no protocols)

    DataAgent --> RiskAgent: data fetched
    DataAgent --> [*]: error (API failure)

    RiskAgent --> ReportAgent: scores calculated
    ReportAgent --> [*]: report generated
```

**Key concepts:**

- **Nodes** are agent functions that process and transform state
- **Edges** define transitions between agents (including conditional routing)
- **State** is a typed dictionary that accumulates data as it flows through the graph

```python
# Simplified workflow definition
workflow = StateGraph(WorkflowState)
workflow.add_node("supervisor", supervisor.run)
workflow.add_node("data_agent", data_agent.run)
workflow.add_node("risk_agent", risk_agent.run)
workflow.add_node("report_agent", report_agent.run)

workflow.set_entry_point("supervisor")
workflow.add_conditional_edges("supervisor", route_next_agent, {...})
workflow.add_conditional_edges("data_agent", route_next_agent, {...})
workflow.add_conditional_edges("risk_agent", route_next_agent, {...})
workflow.add_edge("report_agent", END)
```

This design enables:
- Clear separation of concerns
- Easy addition of new agents
- Debuggable state at each step
- Potential for human-in-the-loop interventions

### Data Flow

```mermaid
flowchart LR
    subgraph External
        API[(DefiLlama API)]
        REKT[(Rekt.news)]
    end

    subgraph "State Object"
        S1[query: str]
        S2[protocol_names: list]
        S3[protocol_data: dict]
        S4[risk_assessments: dict]
        S5[report: RiskReport]
    end

    API --> |HTTP GET| S3
    REKT --> |Scrape incidents| S3
    S1 --> |Supervisor parses| S2
    S3 --> |Risk Agent analyzes| S4
    S4 --> |Report Agent formats| S5
```

## Risk Assessment Methodology

### Scoring Model

Risk is scored on a 0-10 scale where **lower scores indicate lower risk**. The overall score is a weighted average of five factors:

```mermaid
pie title Risk Factor Weights
    "TVL Risk" : 30
    "Chain Concentration" : 25
    "Audit Status" : 20
    "Incident History" : 15
    "Oracle Risk" : 10
```

| Factor | Weight | What It Measures |
|--------|--------|------------------|
| **TVL Risk** | 30% | Protocol size, volatility, and 30-day trend |
| **Chain Concentration** | 25% | Diversification across blockchains |
| **Audit Status** | 20% | Presence and number of security audits |
| **Incident History** | 15% | Historical exploits, severity, recency, and resolution |
| **Oracle Risk** | 10% | Dependency on price oracles |

### Factor Details

#### TVL Risk (30%)

Evaluates Total Value Locked as a proxy for protocol maturity and market confidence.

| Metric | Low Risk | Medium Risk | High Risk |
|--------|----------|-------------|-----------|
| TVL Size | > $1B | $100M - $1B | < $100M |
| Volatility (CV) | < 10% | 10-25% | > 25% |
| 30-day Trend | Growing > 10% | Stable ±10% | Declining > 10% |

#### Chain Concentration (25%)

Measures diversification using the Herfindahl-Hirschman Index (HHI). Single-chain protocols face higher risk from chain-specific issues (outages, exploits, regulatory action).

| Distribution | Risk Level |
|--------------|------------|
| Top chain < 50% TVL | Low |
| Top chain 50-80% TVL | Medium |
| Top chain > 80% TVL | High |
| 5+ chains with meaningful TVL | Bonus reduction |

#### Audit Status (20%)

Checks for security audit records in DefiLlama metadata.

| Status | Score |
|--------|-------|
| 3+ audits on record | 2.0 (Low) |
| 1-2 audits | 4.0 (Medium) |
| No audits found | 8.0 (High) |

#### Incident History (15%)

Evaluates historical security incidents from the Rekt.news leaderboard. The score is a weighted combination of three sub-factors:

| Sub-factor | Weight | What It Measures |
|------------|--------|------------------|
| Recency | 50% | How recently incidents occurred (recent = higher risk) |
| Severity | 40% | Dollar amount lost (>$50M critical, >$10M high, >$1M medium) |
| Resolution | 10% | Whether incidents have been fixed |

Protocols with no documented incidents receive a baseline score of 2.0/10 (no evidence of problems, but not guaranteed safe).

#### Oracle Risk (10%)

Evaluates dependency on external price feeds.

| Oracle Usage | Score |
|--------------|-------|
| Chainlink, Pyth, or other trusted oracles | 2.0 |
| Unknown or custom oracles | 5.0 |
| No oracle dependency detected | 4.0 |

### Risk Levels

```mermaid
%%{init: {'themeVariables': { 'fontSize': '14px'}}}%%
graph LR
    subgraph Risk Scale
        L[0-3: LOW]
        M[3-5: MEDIUM]
        H[5-7: HIGH]
        C[7-10: CRITICAL]
    end

    L --> M --> H --> C

    style L fill:#22c55e,color:#fff
    style M fill:#eab308,color:#000
    style H fill:#f97316,color:#fff
    style C fill:#ef4444,color:#fff
```

| Level | Score Range | Interpretation |
|-------|-------------|----------------|
| **Low** | 0 - 3 | Well-established protocol with strong fundamentals |
| **Medium** | 3 - 5 | Moderate risk factors; standard due diligence recommended |
| **High** | 5 - 7 | Significant concerns; requires careful evaluation |
| **Critical** | 7 - 10 | Multiple high-risk factors; proceed with caution |

## Installation

### Using Nix (Recommended)

```bash
git clone https://github.com/Ricoledan/defi-risk-agent.git
cd defi-risk-agent

# Enter development shell (installs Python 3.11 + dependencies)
nix develop

# Or with direnv
direnv allow
```

### Using pip

```bash
git clone https://github.com/Ricoledan/defi-risk-agent.git
cd defi-risk-agent

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install package
pip install -e .

# With development dependencies
pip install -e ".[dev]"
```

### LLM Setup (Optional)

For AI-powered insights, install and run Ollama:

```bash
# macOS
brew install ollama

# Or use the setup script
./scripts/setup-ollama.sh

# Start Ollama server
ollama serve

# Pull the default model (in another terminal)
ollama pull llama3.2
```

You can also use OpenAI or Anthropic by setting environment variables:

```bash
# For OpenAI
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your-key

# For Anthropic
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=your-key
```

## Usage

### CLI

```bash
# Analyze a single protocol
defi-risk analyze aave

# With AI-powered insights (requires Ollama)
defi-risk analyze aave --llm

# Output as JSON
defi-risk analyze aave --json

# Compare multiple protocols
defi-risk compare aave compound

# Compare with AI insights
defi-risk compare aave compound --llm

# List top protocols by TVL
defi-risk protocols

# Natural language query
defi-risk query "analyze uniswap risk"

# Check LLM setup status
defi-risk setup-llm
```

### REST API

```bash
# Start server
uvicorn src.api.main:app --reload

# Health check
curl http://localhost:8000/health

# Analyze protocol
curl -X POST http://localhost:8000/analyze/aave

# Compare protocols
curl -X POST http://localhost:8000/compare \
  -H "Content-Type: application/json" \
  -d '{"protocols": ["aave", "compound"]}'

# List protocols
curl "http://localhost:8000/protocols?limit=20"
```

### Python Library

```python
import asyncio
from src.graph.workflow import DeFiRiskWorkflow

async def main():
    workflow = DeFiRiskWorkflow()

    # Single protocol analysis
    report = await workflow.analyze("aave")
    print(f"Risk Level: {report.assessment.score.level}")
    print(f"Score: {report.assessment.score.overall}/10")

    # Protocol comparison
    comparison = await workflow.compare(["aave", "compound", "maker"])
    print(comparison.recommendation)

asyncio.run(main())
```

## Example Output

```
$ defi-risk analyze aave

# DeFi Risk Report: Aave V3

Generated: 2025-02-10 14:30 UTC

## Executive Summary

Aave V3 is a Lending protocol with $28.03B in Total Value Locked across 18 blockchains.

**Risk Assessment:** MEDIUM (Score: 3.9/10)

**Key Findings:**
- Well-diversified across 18 chains
- 1 security audit(s) on record
- No documented security incidents

## Risk Score Breakdown

### TVL Risk: 3.2/10
Large TVL ($28.03B) indicates maturity. Low volatility (4.7%). Stable trends.

### Chain Concentration: 5.5/10
18 chains | Top: Ethereum: 81.5%, Arbitrum: 3.0%, Base: 2.7%
High concentration on Ethereum despite multi-chain presence.

### Audit Status: 4.0/10
Audited (1 audit). Has security audit(s) on record.

### Oracle Risk: 4.0/10
No oracle dependency detected in metadata.

### Incident History: 2.0/10
No documented security incidents. Clean security track record.

---

_Data sources: DefiLlama API (https://defillama.com), Rekt.news (https://rekt.news/leaderboard)_
```

## Project Structure

```mermaid
graph TD
    subgraph src/
        subgraph agents/
            A1[supervisor.py]
            A2[data_agent.py]
            A3[risk_agent.py]
            A4[report_agent.py]
            A5[llm_analyst.py]
        end

        subgraph graph/
            G1[workflow.py]
        end

        subgraph tools/
            T1[defillama.py]
            T2[risk_metrics.py]
            T3[rekt_scraper.py]
        end

        subgraph llm/
            L1[provider.py]
        end

        subgraph models/
            M1[schemas.py]
        end

        subgraph api/
            API1[main.py]
        end

        subgraph cli/
            CLI1[main.py]
        end
    end

    G1 --> A1 & A2 & A3 & A4
    A2 --> T1 & T3
    A3 --> T2
    A5 --> L1
    A1 & A2 & A3 & A4 --> M1
    API1 --> G1
    CLI1 --> G1
```

```
defi-risk-agent/
├── src/
│   ├── agents/
│   │   ├── supervisor.py      # Query parsing, workflow routing
│   │   ├── data_agent.py      # DefiLlama + Rekt.news data fetching
│   │   ├── risk_agent.py      # Risk score calculation
│   │   ├── report_agent.py    # Report generation
│   │   └── llm_analyst.py     # LLM-powered analysis (optional)
│   ├── graph/
│   │   └── workflow.py        # LangGraph StateGraph definition
│   ├── tools/
│   │   ├── defillama.py       # DefiLlama API client with caching
│   │   ├── risk_metrics.py    # Risk calculation algorithms (5 factors)
│   │   └── rekt_scraper.py    # Rekt.news incident scraper with caching
│   ├── llm/
│   │   └── provider.py        # LLM provider config (Ollama/OpenAI/Anthropic)
│   ├── models/
│   │   └── schemas.py         # Pydantic models for all data types
│   ├── api/
│   │   └── main.py            # FastAPI application
│   └── cli/
│       └── main.py            # Typer CLI application
├── tests/                     # 79 unit/integration tests
├── scripts/
│   └── setup-ollama.sh        # Ollama setup helper
├── flake.nix                  # Nix flake for reproducible dev env
├── pyproject.toml             # Python package configuration
└── README.md
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Agent Orchestration | LangGraph | Stateful multi-agent workflow |
| LLM (Optional) | Ollama / OpenAI / Anthropic | AI-powered insights |
| Data Validation | Pydantic | Type-safe data models |
| HTTP Client | httpx | Async API requests |
| Web Scraping | BeautifulSoup4 | Rekt.news incident parsing |
| REST API | FastAPI | Web API endpoints |
| CLI | Typer + Rich | Command-line interface |
| Testing | pytest + pytest-asyncio + respx | Async test support with HTTP mocking |
| Linting | Ruff | Fast Python linter |
| Dev Environment | Nix | Reproducible builds |

## Data Sources

### DefiLlama API

All protocol data is fetched from the [DefiLlama API](https://defillama.com/docs/api) with a 5-minute cache TTL:

| Endpoint | Data Retrieved |
|----------|----------------|
| `/protocols` | Protocol list with current TVL, category, chains |
| `/protocol/{name}` | Historical TVL, chain breakdown, audit links, oracles |

DefiLlama aggregates on-chain data across 200+ blockchains and 3000+ protocols. Data is typically updated every few minutes.

### Rekt.news

Historical exploit and incident data is scraped from the [Rekt.news leaderboard](https://rekt.news/leaderboard/) with a 24-hour cache TTL. The scraper uses multiple parsing strategies (embedded JSON, HTML table, generic fallback) to handle potential structure changes. Incidents are matched to protocols using multi-strategy name normalization (exact slug, base name extraction, partial string matching).

## Limitations

This tool has significant limitations that users should understand:

### Data Limitations

- **Limited Data Sources** - Relies on DefiLlama for protocol metrics and Rekt.news for incident history. If either source is incomplete, stale, or incorrect, our analysis will be too.
- **Audit Data Quality** - DefiLlama's audit links are community-maintained and may be incomplete. A protocol showing "no audits" may actually have audits that aren't indexed.
- **Incident Matching** - Protocol names vary across data sources (e.g., "cream-finance" vs "cream-rekt-2"). The multi-strategy name matching is not 100% accurate and may miss or misattribute incidents.
- **No Smart Contract Analysis** - We don't analyze actual smart contract code, only metadata about the protocol.

### Methodology Limitations

- **Simplified Risk Model** - Real DeFi risk assessment requires analyzing tokenomics, governance, team, code quality, economic attacks, and more. Our five-factor model is a simplification.
- **Arbitrary Weights** - The 30/25/20/15/10 weighting is a reasonable starting point but not empirically validated.
- **TVL as Proxy** - High TVL doesn't guarantee safety (see Terra/Luna). Low TVL doesn't mean a protocol is risky.
- **Chain Concentration** - Multi-chain isn't always better. It can mean more attack surface and bridge risks.
- **Incident "Fixed" Status** - Whether an incident has been resolved is not independently verified.

### Technical Limitations

- **No Real-time Data** - Protocol data is cached for 5 minutes; incident data for 24 hours. Not suitable for time-sensitive decisions.
- **Rekt.news Scraping** - Web scraping is inherently fragile. HTML structure changes on Rekt.news may temporarily break incident data fetching (the system gracefully degrades to empty results).
- **Optional LLM Integration** - LLM-powered insights require Ollama running locally, or an OpenAI/Anthropic API key. The base analysis is purely algorithmic.
- **Limited Protocol Recognition** - The supervisor uses a hardcoded keyword list to find protocols. Unusual or new protocol names may not be recognized.

### Not Financial Advice

This tool is for educational and research purposes. Risk scores should not be the sole basis for investment decisions. Always:
- Conduct your own research
- Review audit reports directly
- Understand the protocol's mechanics
- Consider risks not captured by this model
- Consult qualified financial advisors for investment decisions

## Development

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Linting
ruff check src/ tests/

# Auto-fix lint issues
ruff check src/ tests/ --fix

# Format code
ruff format src/ tests/
```

## Future Improvements

Potential enhancements (not currently implemented):

- [x] ~~Integrate historical exploit/incident data~~ (Added via Rekt.news scraper)
- [x] ~~Add LLM-powered analysis for qualitative factors~~ (Added via Ollama/OpenAI/Anthropic integration)
- [ ] Support more data sources (DeFi Safety, Exponential, etc.)
- [ ] Track risk score changes over time
- [ ] Add governance and tokenomics analysis
- [ ] WebSocket support for real-time updates
- [ ] User-configurable risk weights
- [ ] Dynamic protocol list (fetch from DefiLlama instead of hardcoded)

## License

MIT

## Contributing

Contributions welcome. Please open an issue to discuss significant changes before submitting a PR.
