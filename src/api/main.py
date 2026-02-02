"""FastAPI application for DeFi risk analysis."""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.graph.workflow import DeFiRiskWorkflow
from src.models.schemas import (
    AnalyzeRequest,
    CompareRequest,
    ComparisonReport,
    HealthResponse,
    RiskReport,
)


# Global workflow instance
workflow: DeFiRiskWorkflow | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global workflow
    workflow = DeFiRiskWorkflow()
    yield
    workflow = None


app = FastAPI(
    title="DeFi Risk Analysis API",
    description="Multi-agent system for analyzing DeFi protocol risk",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.utcnow(),
    )


@app.post("/analyze/{protocol}", response_model=RiskReport)
async def analyze_protocol(protocol: str) -> RiskReport:
    """
    Analyze risk for a single DeFi protocol.

    Args:
        protocol: Protocol name or slug (e.g., "aave", "compound")

    Returns:
        Complete risk report with executive summary and detailed analysis
    """
    if workflow is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        report = await workflow.analyze(protocol)
        if report is None:
            raise HTTPException(status_code=500, detail="Failed to generate report")
        return report
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")


@app.post("/analyze")
async def analyze_protocol_body(request: AnalyzeRequest) -> RiskReport:
    """
    Analyze risk for a single DeFi protocol (request body version).

    Args:
        request: Request containing protocol name

    Returns:
        Complete risk report
    """
    return await analyze_protocol(request.protocol)


@app.post("/compare", response_model=ComparisonReport)
async def compare_protocols(request: CompareRequest) -> ComparisonReport:
    """
    Compare risk between multiple DeFi protocols.

    Args:
        request: Request containing list of protocol names (2-5 protocols)

    Returns:
        Comparison report with rankings and recommendations
    """
    if workflow is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    if len(request.protocols) < 2:
        raise HTTPException(status_code=400, detail="At least 2 protocols required")

    if len(request.protocols) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 protocols allowed")

    try:
        report = await workflow.compare(request.protocols)
        if report is None:
            raise HTTPException(status_code=500, detail="Failed to generate comparison")
        return report
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison failed: {e}")


@app.post("/query")
async def run_query(query: str) -> dict[str, Any]:
    """
    Run a natural language query about DeFi protocol risk.

    Args:
        query: Natural language query

    Returns:
        Workflow result including report if applicable
    """
    if workflow is None:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        result = await workflow.run_query(query)

        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])

        # Serialize the response
        response: dict[str, Any] = {
            "query": result.get("query"),
            "protocols_analyzed": result.get("protocol_names", []),
            "error": result.get("error"),
        }

        # Include report if available
        report = result.get("report")
        if report:
            if isinstance(report, RiskReport):
                response["report_type"] = "risk_report"
                response["report"] = report.model_dump()
            elif isinstance(report, ComparisonReport):
                response["report_type"] = "comparison_report"
                response["report"] = report.model_dump()

        # Include agent messages
        messages = result.get("messages", [])
        response["agent_messages"] = [
            {"agent": m.get("agent"), "content": m.get("content")}
            for m in messages
        ]

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")


@app.get("/protocols")
async def list_protocols(limit: int = 50) -> list[dict[str, Any]]:
    """
    List top DeFi protocols by TVL.

    Args:
        limit: Number of protocols to return (default 50, max 200)

    Returns:
        List of protocols with basic info
    """
    from src.tools.defillama import get_client

    limit = min(limit, 200)
    client = get_client()

    try:
        all_protocols = await client.get_protocols()

        # Sort by TVL
        sorted_protocols = sorted(
            all_protocols,
            key=lambda p: p.get("tvl", 0) or 0,
            reverse=True,
        )[:limit]

        # Return simplified data
        return [
            {
                "name": p.get("name"),
                "slug": p.get("slug"),
                "category": p.get("category"),
                "tvl": p.get("tvl"),
                "chains": p.get("chains", []),
            }
            for p in sorted_protocols
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch protocols: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
