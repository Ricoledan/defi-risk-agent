"""CLI interface for DeFi risk analysis."""

import asyncio
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.graph.workflow import DeFiRiskWorkflow
from src.models.schemas import ComparisonReport, RiskReport

app = typer.Typer(
    name="defi-risk",
    help="DeFi Protocol Risk Analysis Agent",
    add_completion=False,
)
console = Console()


def run_async(coro):
    """Run async function in sync context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is None:
        return asyncio.run(coro)
    else:
        return loop.run_until_complete(coro)


@app.command()
def analyze(
    protocol: Annotated[str, typer.Argument(help="Protocol name to analyze (e.g., aave, compound)")],
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")] = False,
) -> None:
    """
    Analyze risk for a single DeFi protocol.

    Example:
        defi-risk analyze aave
        defi-risk analyze compound --json
    """
    workflow = DeFiRiskWorkflow()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Analyzing {protocol}...", total=None)

        try:
            report = run_async(workflow.analyze(protocol))
        except RuntimeError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        progress.update(task, completed=True)

    if report is None:
        console.print("[red]Failed to generate report[/red]")
        raise typer.Exit(1)

    if json_output:
        console.print(report.model_dump_json(indent=2))
    else:
        # Render as markdown
        formatted = workflow.format_report(report)
        console.print(Markdown(formatted))


@app.command()
def compare(
    protocols: Annotated[
        list[str],
        typer.Argument(help="Protocol names to compare (2-5 protocols)"),
    ],
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")] = False,
) -> None:
    """
    Compare risk between multiple DeFi protocols.

    Example:
        defi-risk compare aave compound
        defi-risk compare uniswap sushiswap curve --json
    """
    if len(protocols) < 2:
        console.print("[red]Error:[/red] Please provide at least 2 protocols to compare")
        raise typer.Exit(1)

    if len(protocols) > 5:
        console.print("[red]Error:[/red] Maximum 5 protocols can be compared at once")
        raise typer.Exit(1)

    workflow = DeFiRiskWorkflow()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        protocol_list = ", ".join(protocols)
        task = progress.add_task(f"Comparing {protocol_list}...", total=None)

        try:
            report = run_async(workflow.compare(protocols))
        except RuntimeError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        progress.update(task, completed=True)

    if report is None:
        console.print("[red]Failed to generate comparison report[/red]")
        raise typer.Exit(1)

    if json_output:
        console.print(report.model_dump_json(indent=2))
    else:
        formatted = workflow.format_report(report)
        console.print(Markdown(formatted))


@app.command()
def query(
    text: Annotated[str, typer.Argument(help="Natural language query about DeFi protocols")],
) -> None:
    """
    Run a natural language query about DeFi protocol risk.

    Example:
        defi-risk query "What is the risk profile of Aave?"
        defi-risk query "Compare Uniswap and Curve"
    """
    workflow = DeFiRiskWorkflow()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Processing query...", total=None)

        try:
            result = run_async(workflow.run_query(text))
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        progress.update(task, completed=True)

    if result.get("error"):
        console.print(f"[red]Error:[/red] {result['error']}")
        raise typer.Exit(1)

    report = result.get("report")
    if report:
        formatted = workflow.format_report(report)
        console.print(Markdown(formatted))
    else:
        # Show messages from agents
        console.print(Panel("Agent Responses", style="blue"))
        for msg in result.get("messages", []):
            agent = msg.get("agent", "unknown")
            content = msg.get("content", "")
            console.print(f"[bold]{agent}:[/bold] {content}")


@app.command()
def protocols() -> None:
    """
    List supported protocols (fetched from DefiLlama).

    Example:
        defi-risk protocols
    """
    from src.tools.defillama import get_client

    client = get_client()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching protocols...", total=None)

        try:
            all_protocols = run_async(client.get_protocols())
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        progress.update(task, completed=True)

    # Sort by TVL and show top 50
    sorted_protocols = sorted(
        all_protocols,
        key=lambda p: p.get("tvl", 0) or 0,
        reverse=True,
    )[:50]

    console.print(Panel("Top 50 DeFi Protocols by TVL", style="blue"))
    console.print()

    for i, p in enumerate(sorted_protocols, 1):
        name = p.get("name", "Unknown")
        slug = p.get("slug", "")
        tvl = p.get("tvl", 0) or 0
        category = p.get("category", "")

        tvl_str = f"${tvl / 1e9:.2f}B" if tvl >= 1e9 else f"${tvl / 1e6:.0f}M"
        console.print(f"{i:3}. [bold]{name}[/bold] ({slug}) - {tvl_str} [{category}]")


@app.command()
def version() -> None:
    """Show version information."""
    console.print(Panel("DeFi Risk Analysis Agent v0.1.0", style="green"))
    console.print("Built with LangGraph, FastAPI, and Typer")
    console.print("Data source: DefiLlama API")


if __name__ == "__main__":
    app()
