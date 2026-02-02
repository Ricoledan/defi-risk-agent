"""CLI interface for DeFi risk analysis."""

import asyncio
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.graph.workflow import DeFiRiskWorkflow

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


def get_llm_analysis(protocol_data, assessment, compare_mode=False, all_data=None):
    """Get LLM-powered analysis if available."""
    try:
        from src.agents.llm_analyst import LLMAnalyst

        analyst = LLMAnalyst()

        if compare_mode and all_data:
            protocols, assessments = all_data
            return analyst.compare(protocols, assessments)
        else:
            return analyst.analyze(protocol_data, assessment)
    except RuntimeError as e:
        return f"[LLM analysis unavailable: {e}]"
    except Exception as e:
        return f"[LLM analysis failed: {e}]"


@app.command()
def analyze(
    protocol: Annotated[
        str, typer.Argument(help="Protocol name to analyze (e.g., aave, compound)")
    ],
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")] = False,
    llm: Annotated[
        bool, typer.Option("--llm", "-l", help="Include LLM-powered insights (requires Ollama)")
    ] = False,
) -> None:
    """
    Analyze risk for a single DeFi protocol.

    Example:
        defi-risk analyze aave
        defi-risk analyze aave --llm      # With AI insights
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
        formatted = workflow.format_report(report)
        console.print(Markdown(formatted))

        if llm:
            console.print()
            console.print(Panel("AI Analysis", style="cyan"))
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Generating AI insights...", total=None)
                llm_output = get_llm_analysis(report.protocol, report.assessment)
                progress.update(task, completed=True)

            console.print(Markdown(llm_output))


@app.command()
def compare(
    protocols: Annotated[
        list[str],
        typer.Argument(help="Protocol names to compare (2-5 protocols)"),
    ],
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")] = False,
    llm: Annotated[
        bool, typer.Option("--llm", "-l", help="Include LLM-powered insights (requires Ollama)")
    ] = False,
) -> None:
    """
    Compare risk between multiple DeFi protocols.

    Example:
        defi-risk compare aave compound
        defi-risk compare aave compound --llm  # With AI insights
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

        if llm:
            console.print()
            console.print(Panel("AI Comparison Analysis", style="cyan"))
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Generating AI insights...", total=None)
                llm_output = get_llm_analysis(
                    None,
                    None,
                    compare_mode=True,
                    all_data=(report.protocols, report.assessments),
                )
                progress.update(task, completed=True)

            console.print(Markdown(llm_output))


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
def setup_llm() -> None:
    """
    Check Ollama status and setup for LLM features.

    Example:
        defi-risk setup-llm
    """
    from src.llm.provider import check_ollama_available, get_available_ollama_models

    console.print(Panel("Ollama Setup Check", style="blue"))
    console.print()

    if check_ollama_available():
        console.print("[green]✓[/green] Ollama server is running")

        models = get_available_ollama_models()
        if models:
            console.print(f"[green]✓[/green] Models installed: {', '.join(models)}")
        else:
            console.print("[yellow]![/yellow] No models installed")
            console.print("  Run: ollama pull llama3.2")
    else:
        console.print("[red]✗[/red] Ollama server not running")
        console.print()
        console.print("To setup Ollama:")
        console.print("  1. Install: brew install ollama")
        console.print("  2. Start:   ollama serve")
        console.print("  3. Pull:    ollama pull llama3.2")
        console.print()
        console.print("Or run: ./scripts/setup-ollama.sh")


@app.command()
def version() -> None:
    """Show version information."""
    console.print(Panel("DeFi Risk Analysis Agent v0.1.0", style="green"))
    console.print("Built with LangGraph, FastAPI, and Typer")
    console.print("Data source: DefiLlama API")
    console.print("LLM support: Ollama (optional)")


if __name__ == "__main__":
    app()
