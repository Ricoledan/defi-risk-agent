#!/usr/bin/env bash
# Setup script for Ollama integration

set -e

echo "=== DeFi Risk Agent - Ollama Setup ==="
echo ""

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "Ollama not found. Installing..."

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install ollama
        else
            echo "Please install Homebrew first: https://brew.sh"
            echo "Or download Ollama from: https://ollama.ai/download"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        curl -fsSL https://ollama.ai/install.sh | sh
    else
        echo "Unsupported OS. Please install Ollama manually from: https://ollama.ai/download"
        exit 1
    fi
fi

echo "Ollama installed: $(ollama --version)"
echo ""

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "Starting Ollama server..."
    ollama serve &
    sleep 3
fi

# Check available models
echo "Checking installed models..."
MODELS=$(curl -s http://localhost:11434/api/tags | grep -o '"name":"[^"]*"' | cut -d'"' -f4)

if [ -z "$MODELS" ]; then
    echo "No models installed."
else
    echo "Installed models:"
    echo "$MODELS" | while read -r model; do
        echo "  - $model"
    done
fi
echo ""

# Pull default model if not present
DEFAULT_MODEL="llama3.2"

if ! echo "$MODELS" | grep -q "$DEFAULT_MODEL"; then
    echo "Pulling default model: $DEFAULT_MODEL"
    echo "This may take a few minutes depending on your connection..."
    ollama pull $DEFAULT_MODEL
else
    echo "Default model ($DEFAULT_MODEL) already installed."
fi

echo ""
echo "=== Setup Complete ==="
echo ""
echo "You can now run:"
echo "  defi-risk analyze aave --llm       # With LLM insights"
echo "  defi-risk analyze aave             # Without LLM (faster)"
echo ""
echo "To use a different model:"
echo "  export OLLAMA_MODEL=mistral"
echo "  defi-risk analyze aave --llm"
echo ""
