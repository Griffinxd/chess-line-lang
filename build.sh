#!/usr/bin/env bash
# ============================================================================
# build.sh — Build script for ChessLineLang (CLL)
#
# Sets up the Python environment, installs dependencies, downloads and
# installs the Stockfish chess engine, and verifies everything works.
#
# Usage:
#   chmod +x build.sh
#   ./build.sh              # Full build (venv + deps + Stockfish + tests)
#   ./build.sh --no-engine  # Skip Stockfish installation
#   ./build.sh --clean      # Remove build artifacts and start fresh
# ============================================================================

set -euo pipefail

# ── Paths ───────────────────────────────────────────────────────────────────
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
ENGINE_DIR="$PROJECT_ROOT/engines"
SRC_DIR="$PROJECT_ROOT/src"
TESTS_DIR="$PROJECT_ROOT/tests"

# ── Colors & formatting ────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERR]${NC}   $*" >&2; }
header()  { echo -e "\n${BOLD}════════════════════════════════════════════════════${NC}"; echo -e "${BOLD}  $*${NC}"; echo -e "${BOLD}════════════════════════════════════════════════════${NC}"; }

# ── Argument parsing ────────────────────────────────────────────────────────
SKIP_ENGINE=false
CLEAN=false
RUN_TESTS=true

for arg in "$@"; do
    case "$arg" in
        --no-engine)  SKIP_ENGINE=true ;;
        --clean)      CLEAN=true ;;
        --no-tests)   RUN_TESTS=false ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-engine   Skip Stockfish engine installation"
            echo "  --no-tests    Skip running the test suite"
            echo "  --clean       Remove .venv and engines/ before building"
            echo "  -h, --help    Show this help message"
            exit 0
            ;;
        *)
            error "Unknown option: $arg"
            echo "Run '$0 --help' for usage."
            exit 1
            ;;
    esac
done

# ── Clean ───────────────────────────────────────────────────────────────────
if [ "$CLEAN" = true ]; then
    header "Cleaning build artifacts"
    [ -d "$VENV_DIR" ]   && { info "Removing $VENV_DIR";   rm -rf "$VENV_DIR";   }
    [ -d "$ENGINE_DIR" ] && { info "Removing $ENGINE_DIR"; rm -rf "$ENGINE_DIR"; }
    find "$SRC_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$TESTS_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    success "Clean complete."
fi

# ── Detect Python ───────────────────────────────────────────────────────────
header "Detecting Python"

PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        ver=$("$candidate" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
        major=$(echo "$ver" | cut -d. -f1)
        minor=$(echo "$ver" | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    error "Python 3.10+ is required but not found."
    error "Install it from https://www.python.org/downloads/"
    exit 1
fi

info "Using: $($PYTHON --version) ($PYTHON)"

# ── Virtual environment ─────────────────────────────────────────────────────
header "Setting up virtual environment"

if [ ! -d "$VENV_DIR" ]; then
    info "Creating virtual environment at $VENV_DIR"
    "$PYTHON" -m venv "$VENV_DIR"
    success "Virtual environment created."
else
    info "Virtual environment already exists at $VENV_DIR"
fi

# Activate
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
success "Activated virtual environment."

# ── Install Python dependencies ─────────────────────────────────────────────
header "Installing Python dependencies"

pip install --upgrade pip --quiet
pip install -r "$PROJECT_ROOT/requirements.txt" --quiet
success "Python dependencies installed."

# Verify python-chess
if python -c "import chess; print(f'python-chess {chess.__version__}')" 2>/dev/null; then
    success "python-chess verified."
else
    error "Failed to import python-chess."
    exit 1
fi

# ── Stockfish engine ────────────────────────────────────────────────────────
if [ "$SKIP_ENGINE" = true ]; then
    warn "Skipping Stockfish installation (--no-engine)."
    warn "eval() and eval.move() will not work without a Stockfish binary."
else
    header "Setting up Stockfish engine"

    STOCKFISH_BIN=""

    # Check if stockfish is already on PATH
    if command -v stockfish &>/dev/null; then
        STOCKFISH_BIN="$(command -v stockfish)"
        info "Stockfish already available on PATH: $STOCKFISH_BIN"
    fi

    # If not on PATH, check our local engines/ directory
    if [ -z "$STOCKFISH_BIN" ] && [ -f "$ENGINE_DIR/stockfish" ]; then
        STOCKFISH_BIN="$ENGINE_DIR/stockfish"
        info "Stockfish found in engines/: $STOCKFISH_BIN"
    fi

    # If still not found, download it
    if [ -z "$STOCKFISH_BIN" ]; then
        info "Stockfish not found. Attempting to download..."

        mkdir -p "$ENGINE_DIR"

        OS="$(uname -s)"
        ARCH="$(uname -m)"

        # Determine the correct Stockfish binary
        case "$OS" in
            Darwin)
                if [ "$ARCH" = "arm64" ]; then
                    SF_URL="https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-macos-m1-apple-silicon.tar"
                else
                    SF_URL="https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-macos-x86-64-modern.tar"
                fi
                ;;
            Linux)
                if [ "$ARCH" = "x86_64" ]; then
                    SF_URL="https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-ubuntu-x86-64-modern.tar"
                elif [ "$ARCH" = "aarch64" ]; then
                    SF_URL="https://github.com/official-stockfish/Stockfish/releases/latest/download/stockfish-android-armv8.tar"
                else
                    error "Unsupported Linux architecture: $ARCH"
                    error "Please install Stockfish manually and ensure 'stockfish' is on your PATH."
                    exit 1
                fi
                ;;
            *)
                error "Unsupported OS: $OS"
                error "Please install Stockfish manually and ensure 'stockfish' is on your PATH."
                exit 1
                ;;
        esac

        info "Downloading from: $SF_URL"
        DOWNLOAD_FILE="$ENGINE_DIR/stockfish-download.tar"

        if command -v curl &>/dev/null; then
            curl -fSL -o "$DOWNLOAD_FILE" "$SF_URL"
        elif command -v wget &>/dev/null; then
            wget -q -O "$DOWNLOAD_FILE" "$SF_URL"
        else
            error "Neither curl nor wget found. Please install one of them."
            exit 1
        fi

        # Extract — the archive contains a directory with the binary inside
        info "Extracting Stockfish..."
        tar -xf "$DOWNLOAD_FILE" -C "$ENGINE_DIR"
        rm -f "$DOWNLOAD_FILE"

        # Find the actual binary inside the extracted directory
        STOCKFISH_BIN="$(find "$ENGINE_DIR" -name "stockfish" -type f | head -n 1)"

        if [ -z "$STOCKFISH_BIN" ]; then
            error "Could not locate stockfish binary after extraction."
            error "Contents of $ENGINE_DIR:"
            ls -lR "$ENGINE_DIR" >&2
            exit 1
        fi

        chmod +x "$STOCKFISH_BIN"

        # Symlink to engines/stockfish for a consistent path
        if [ "$STOCKFISH_BIN" != "$ENGINE_DIR/stockfish" ]; then
            ln -sf "$STOCKFISH_BIN" "$ENGINE_DIR/stockfish"
            STOCKFISH_BIN="$ENGINE_DIR/stockfish"
        fi

        success "Stockfish downloaded and installed to $STOCKFISH_BIN"
    fi

    # Add engines/ to PATH for this session & verify
    export PATH="$ENGINE_DIR:$PATH"

    if "$STOCKFISH_BIN" <<< "quit" &>/dev/null; then
        SF_VER=$("$STOCKFISH_BIN" <<< "quit" 2>/dev/null | head -n 1 || echo "unknown version")
        success "Stockfish verified: $SF_VER"
    else
        warn "Stockfish binary found but failed quick test."
        warn "eval() and eval.move() may not work correctly."
    fi
fi

# ── Run tests ───────────────────────────────────────────────────────────────
if [ "$RUN_TESTS" = true ]; then
    header "Running test suite"

    cd "$PROJECT_ROOT"
    if python "$TESTS_DIR/run_all_tests.py"; then
        success "All tests passed."
    else
        warn "Some tests failed. See output above."
    fi
fi

# ── Create runner script ────────────────────────────────────────────────────
header "Creating runner script"

RUNNER="$PROJECT_ROOT/cll"
cat > "$RUNNER" << 'RUNNER_SCRIPT'
#!/usr/bin/env bash
# ── CLL runner — activates the venv and runs a .cll program ──
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Activate venv
source "$SCRIPT_DIR/.venv/bin/activate"

# Add local Stockfish to PATH if available
[ -d "$SCRIPT_DIR/engines" ] && export PATH="$SCRIPT_DIR/engines:$PATH"

# Run the CLL interpreter
exec python "$SCRIPT_DIR/src/main.py" "$@"
RUNNER_SCRIPT

chmod +x "$RUNNER"
success "Runner script created: $RUNNER"

# ── Summary ─────────────────────────────────────────────────────────────────
header "Build complete! 🎉"
echo ""
echo -e "  ${BOLD}Quick start:${NC}"
echo ""
echo -e "    ${CYAN}# Parse a .cll file${NC}"
echo -e "    ./cll sample-programs/valid/valid_01.cll"
echo ""
echo -e "    ${CYAN}# Dump tokens${NC}"
echo -e "    ./cll sample-programs/valid/valid_01.cll --dump-tokens"
echo ""
echo -e "    ${CYAN}# Dump AST${NC}"
echo -e "    ./cll sample-programs/valid/valid_01.cll --dump-ast"
echo ""
echo -e "    ${CYAN}# Type-check${NC}"
echo -e "    ./cll sample-programs/valid/valid_04.cll --type-check"
echo ""
echo -e "    ${CYAN}# Run (interpret with Stockfish)${NC}"
echo -e "    ./cll sample-programs/valid/valid_04.cll --run"
echo ""
echo -e "    ${CYAN}# Run tests${NC}"
echo -e "    source .venv/bin/activate && python tests/run_all_tests.py"
echo ""
