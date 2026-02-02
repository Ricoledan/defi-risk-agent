{
  description = "DeFi Risk Analysis Agent - Multi-agent system for protocol risk assessment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        # Use Python 3.11 for best compatibility with LangGraph
        python = pkgs.python311;

        # Check if Ollama is available for this system
        hasOllama = pkgs ? ollama;

        # Development shell with all tools
        devShell = pkgs.mkShell {
          name = "defi-risk-agent";

          buildInputs = [
            python
            pkgs.git
            pkgs.curl
          ] ++ pkgs.lib.optionals hasOllama [
            pkgs.ollama
          ];

          shellHook = ''
            echo "╔══════════════════════════════════════════════════════════════╗"
            echo "║     DeFi Risk Analysis Agent Development Environment         ║"
            echo "╚══════════════════════════════════════════════════════════════╝"
            echo ""
            echo "Python: $(python --version)"
            ${if hasOllama then ''
            if command -v ollama &> /dev/null; then
              echo "Ollama: $(ollama --version 2>/dev/null || echo 'installed')"
            fi
            '' else ''
            echo "Ollama: not available in nixpkgs for this system"
            echo "        Install via: brew install ollama (macOS) or https://ollama.ai"
            ''}
            echo ""

            # Create virtual environment if it doesn't exist
            if [ ! -d ".venv" ]; then
              echo "Creating virtual environment..."
              python -m venv .venv
            fi

            # Activate virtual environment
            source .venv/bin/activate

            # Install package in editable mode if not installed
            if ! python -c "import src" 2>/dev/null; then
              echo "Installing package and dependencies..."
              pip install -e . --quiet
            fi

            echo ""
            echo "Available commands:"
            echo "  defi-risk analyze <protocol>      - Analyze a protocol"
            echo "  defi-risk analyze <proto> --llm   - With AI insights"
            echo "  defi-risk compare <p1> <p2>       - Compare protocols"
            echo "  defi-risk protocols               - List top protocols"
            echo "  defi-risk setup-llm               - Check Ollama status"
            echo "  pytest                            - Run tests"
            echo ""
            echo "API server:"
            echo "  uvicorn src.api.main:app --reload"
            echo ""
            echo "LLM setup (optional):"
            echo "  ollama serve                      - Start Ollama server"
            echo "  ollama pull llama3.2              - Download model"
            echo "  ./scripts/setup-ollama.sh         - Automated setup"
            echo ""
          '';
        };

      in
      {
        devShells.default = devShell;

        # Provide a way to run the CLI
        apps.default = {
          type = "app";
          program = toString (pkgs.writeShellScript "defi-risk" ''
            cd ${toString ./.}
            if [ ! -d ".venv" ]; then
              ${python}/bin/python -m venv .venv
              source .venv/bin/activate
              pip install -e . --quiet
            else
              source .venv/bin/activate
            fi
            defi-risk "$@"
          '');
        };

        # API server app
        apps.server = {
          type = "app";
          program = toString (pkgs.writeShellScript "defi-risk-server" ''
            cd ${toString ./.}
            if [ ! -d ".venv" ]; then
              ${python}/bin/python -m venv .venv
              source .venv/bin/activate
              pip install -e . --quiet
            else
              source .venv/bin/activate
            fi
            uvicorn src.api.main:app --host 0.0.0.0 --port 8000 "$@"
          '');
        };
      }
    );
}
