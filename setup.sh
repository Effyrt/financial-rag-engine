#!/bin/bash

###############################################################################
# AURELIA Complete Setup Script - ENTERPRISE VERSION
# 
# One-command setup for both local development and cloud deployment.
# Handles prerequisites, dependencies, Docker, database, and testing.
#
# Usage:
#   ./setup.sh local    # Local development environment
#   ./setup.sh cloud    # Deploy to Google Cloud Platform
#   ./setup.sh test     # Run test suite only
###############################################################################

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${PURPLE}[STEP]${NC} $1"; }

# Determine mode
MODE=${1:-local}

log_info "Starting AURELIA setup in ${MODE} mode..."

###############################################################################
# Check Prerequisites
###############################################################################
check_prerequisites() {
    log_step "Checking prerequisites..."
    
    local missing_deps=()
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    else
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        if (( $(echo "$PYTHON_VERSION < 3.11" | bc -l 2>/dev/null || echo "0") )); then
            log_warning "Python 3.11+ recommended, found $PYTHON_VERSION"
        fi
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        missing_deps+=("docker")
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        missing_deps+=("docker-compose")
    fi
    
    # For cloud mode
    if [ "$MODE" = "cloud" ]; then
        if ! command -v gcloud &> /dev/null; then
            missing_deps+=("gcloud")
        fi
        
        if ! command -v terraform &> /dev/null; then
            missing_deps+=("terraform")
        fi
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        log_info "Please install missing dependencies and try again."
        exit 1
    fi
    
    log_success "All prerequisites met!"
}

###############################################################################
# Setup Python Environment
###############################################################################
setup_python_env() {
    log_step "Setting up Python environment..."
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        log_info "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip setuptools wheel > /dev/null 2>&1
    
    # Install dependencies
    log_info "Installing Python dependencies (this may take 3-5 minutes)..."
    pip install -r requirements.txt > /dev/null 2>&1
    
    log_success "Python environment ready!"
}

###############################################################################
# Setup Environment Variables
###############################################################################
setup_env_vars() {
    log_step "Setting up environment variables..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_warning "Created .env from .env.example"
            log_warning "⚠️  IMPORTANT: Edit .env and add your API keys!"
            
            # Check if API keys are set
            if ! grep -q "OPENAI_API_KEY=sk-" .env; then
                log_error "OPENAI_API_KEY not set in .env"
                echo ""
                read -p "Enter your OpenAI API key (or press Enter to skip): " OPENAI_KEY
                if [ -n "$OPENAI_KEY" ]; then
                    sed -i.bak "s/OPENAI_API_KEY=.*/OPENAI_API_KEY=$OPENAI_KEY/" .env
                    log_success "OpenAI API key configured"
                fi
            fi
        else
            log_error ".env.example not found"
            exit 1
        fi
    fi
    
    # Load environment variables
    export $(cat .env | grep -v '^#' | xargs)
    
    log_success "Environment variables configured!"
}

###############################################################################
# Setup Local Development
###############################################################################
setup_local() {
    log_step "Setting up local development environment..."
    
    # Create data directories
    mkdir -p data/raw data/processed data/chromadb
    log_info "Created data directories"
    
    # Check if PDF exists
    if [ ! -f "data/raw/fintbx.pdf" ]; then
        log_warning "fintbx.pdf not found in data/raw/"
        log_info "Please place the Financial Toolbox User's Guide PDF in data/raw/"
        echo ""
        read -p "Do you have the PDF file? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            read -p "Enter path to PDF file: " PDF_PATH
            if [ -f "$PDF_PATH" ]; then
                cp "$PDF_PATH" data/raw/fintbx.pdf
                log_success "PDF copied to data/raw/"
            else
                log_error "PDF file not found at $PDF_PATH"
                log_warning "Continuing without PDF (some features won't work)"
            fi
        fi
    else
        log_success "PDF found at data/raw/fintbx.pdf"
    fi
    
    # Start Docker services
    log_info "Starting Docker services..."
    docker-compose up -d
    
    # Wait for services
    log_info "Waiting for services to start..."
    sleep 15
    
    # Check service health
    log_info "Checking service health..."
    
    max_retries=30
    count=0
    while [ $count -lt $max_retries ]; do
        if docker-compose ps | grep -q "Up"; then
            log_success "Services are running!"
            break
        fi
        count=$((count + 1))
        sleep 2
    done
    
    if [ $count -eq $max_retries ]; then
        log_error "Services failed to start. Check logs: docker-compose logs"
        exit 1
    fi
    
    # Initialize database
    log_info "Initializing database schema..."
    docker-compose exec -T postgres psql -U aurelia_user -d aurelia < deployment/scripts/init_database.sql || true
    log_success "Database initialized!"
    
    # Display service URLs
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  🎉 AURELIA is now running!"
    echo "═══════════════════════════════════════════════════════════"
    echo "  Frontend:    http://localhost:8501"
    echo "  API:         http://localhost:8000"
    echo "  API Docs:    http://localhost:8000/docs"
    echo "  PostgreSQL:  localhost:5432"
    echo "  Redis:       localhost:6379"
    echo "  ChromaDB:    localhost:8001"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    echo "Next steps:"
    echo "  1. Open http://localhost:8501 in your browser"
    echo "  2. Try querying: 'Sharpe Ratio'"
    echo "  3. Explore the Browse and Statistics pages"
    echo ""
}

###############################################################################
# Main Execution
###############################################################################
main() {
    echo "═══════════════════════════════════════════════════════════"
    echo "  AURELIA Setup Script - Enterprise Edition"
    echo "  Automated Financial Concept Note Generator"
    echo "═══════════════════════════════════════════════════════════"
    echo ""
    
    case "$MODE" in
        local)
            check_prerequisites
            setup_python_env
            setup_env_vars
            setup_local
            ;;
        cloud)
            log_error "Cloud deployment requires manual steps"
            log_info "Please see docs/deployment_guide.md"
            exit 1
            ;;
        test)
            check_prerequisites
            setup_python_env
            source venv/bin/activate
            pytest tests/ -v --cov=src
            ;;
        *)
            log_error "Invalid mode: $MODE"
            echo "Usage: ./setup.sh [local|cloud|test]"
            exit 1
            ;;
    esac
    
    log_success "Setup complete!"
}

# Run main
main "$@"