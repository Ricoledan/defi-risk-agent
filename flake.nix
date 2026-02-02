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

        # Development shell with all tools
        devShell = pkgs.mkShell {
          name = "defi-risk-agent";

          buildInputs = [
            python
            pkgs.git
            pkgs.curl
          ];

          shellHook = ''
            echo "╔══════════════════════════════════════════════════════════════╗"
            echo "║     DeFi Risk Analysis Agent Development Environment         ║"
            echo "╚══════════════════════════════════════════════════════════════╝"
            echo ""
            echo "Python: $(python --version)"
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
            echo "  defi-risk analyze <protocol>  - Analyze a protocol"
            echo "  defi-risk compare <p1> <p2>   - Compare protocols"
            echo "  defi-risk protocols           - List top protocols"
            echo "  pytest                        - Run tests"
            echo ""
            echo "API server:"
            echo "  uvicorn src.api.main:app --reload"
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
