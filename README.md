# DeFi Risk Analysis Agent

A multi-agent system built with LangGraph that analyzes DeFi protocol risk. Designed for enterprise-grade risk assessment with data provenance and explainable AI.

## Architecture

```
                    ┌─────────────────┐
                    │   Supervisor    │
                    │   (Router)      │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Data Agent   │    │  Risk Agent   │    │ Report Agent  │
│  (DefiLlama)  │    │  (Analysis)   │    │  (Synthesis)  │
└───────────────┘    └───────────────┘    └───────────────┘
```

### Agent Responsibilities

1. **Supervisor Agent** - Routes queries, manages workflow state
2. **Data Agent** - Fetches protocol data from DefiLlama API
3. **Risk Agent** - Calculates risk scores and assessments
4. **Report Agent** - Generates professional reports with citations

## Tech Stack

| Layer | Technology |
|-------|------------|
| Agent Orchestration | LangGraph |
| API Framework | FastAPI |
| CLI | Typer + Rich |
| Data Source | DefiLlama API |
| Type Validation | Pydantic |
| Testing | pytest |

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/defi-risk-agent.git
cd defi-risk-agent

# Install with pip
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

## Quick Start

### CLI Usage

```bash
# Analyze a single protocol
defi-risk analyze aave

# Compare multiple protocols
defi-risk compare aave compound

# Get JSON output
defi-risk analyze aave --json

# Natural language query
defi-risk query "What is the risk profile of Uniswap?"

# List top protocols
defi-risk protocols
```

### API Usage

```bash
# Start the server
uvicorn src.api.main:app --reload

# Health check
curl http://localhost:8000/health

# Analyze a protocol
curl -X POST http://localhost:8000/analyze/aave

# Compare protocols
curl -X POST http://localhost:8000/compare \
  -H "Content-Type: application/json" \
  -d '{"protocols": ["aave", "compound"]}'

# List protocols
curl http://localhost:8000/protocols?limit=20
```

### Python API

```python
import asyncio
from src.graph.workflow import DeFiRiskWorkflow

async def main():
    workflow = DeFiRiskWorkflow()

    # Analyze single protocol
    report = await workflow.analyze("aave")
    print(workflow.format_report(report))

    # Compare protocols
    comparison = await workflow.compare(["aave", "compound"])
    print(workflow.format_report(comparison))

asyncio.run(main())
```

## Risk Assessment Methodology

### Risk Factors

| Factor | Weight | Description |
|--------|--------|-------------|
| TVL Risk | 35% | Size, volatility, and trends |
| Chain Concentration | 25% | Diversification across chains |
| Audit Status | 25% | Number and quality of audits |
| Oracle Risk | 15% | Oracle dependencies and trust |

### Risk Levels

| Level | Score Range | Description |
|-------|-------------|-------------|
| Low | 0-3 | Well-established, diversified, audited |
| Medium | 3-5 | Moderate risk factors present |
| High | 5-7 | Significant concerns identified |
| Critical | 7-10 | Multiple high-risk factors |

## Example Output

```
# DeFi Risk Report: Aave

## Executive Summary

Aave is a Lending protocol with $10.5B in Total Value Locked across 8 blockchains.

**Risk Assessment:** LOW (Score: 3.2/10)

**Key Findings:**
- Strong TVL growth (+5.2% 30d)
- Well-diversified across 8 chains
- 5 security audit(s) on record

## Risk Score Breakdown

### TVL Risk: 2.5/10
Large TVL ($10.5B) indicates maturity. Low volatility (8.2%). Stable growth.

### Chain Concentration: 4.0/10
8 chains | Top: Ethereum: 65.0%, Polygon: 12.0%, Arbitrum: 10.0%

### Audit Status: 2.0/10
Multiple audits (5). Well-audited protocol with multiple security reviews.

### Oracle Risk: 2.0/10
Uses trusted oracle(s): Chainlink

---

_Data source: DefiLlama API_
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/analyze/{protocol}` | POST | Analyze single protocol |
| `/compare` | POST | Compare multiple protocols |
| `/query` | POST | Natural language query |
| `/protocols` | GET | List top protocols |

## Development

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=src

# Type checking
mypy src

# Linting
ruff check src tests
```

## Project Structure

```
defi-risk-agent/
├── src/
│   ├── agents/
│   │   ├── supervisor.py      # Main router agent
│   │   ├── data_agent.py      # DefiLlama integration
│   │   ├── risk_agent.py      # Risk analysis logic
│   │   └── report_agent.py    # Report generation
│   ├── graph/
│   │   └── workflow.py        # LangGraph workflow
│   ├── tools/
│   │   ├── defillama.py       # DefiLlama API client
│   │   └── risk_metrics.py    # Risk calculations
│   ├── models/
│   │   └── schemas.py         # Pydantic models
│   ├── api/
│   │   └── main.py            # FastAPI app
│   └── cli/
│       └── main.py            # Typer CLI
├── tests/
├── pyproject.toml
└── README.md
```

## Data Sources

- **DefiLlama API** - TVL, chain data, protocol metadata
  - `/protocols` - Protocol list with TVL
  - `/protocol/{name}` - Detailed protocol data
  - `/chains` - Chain-level TVL

## Limitations

- Risk scores are algorithmic and should not be sole investment criteria
- Data freshness depends on DefiLlama API update frequency
- Audit status may not reflect all security reviews
- Historical incidents are not currently tracked

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.
