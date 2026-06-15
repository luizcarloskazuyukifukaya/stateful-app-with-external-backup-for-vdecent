#!/bin/bash

# Default port candidates (priority order)
PORT_CANDIDATES=(80 8081 8082 8083 8084 8085)

# Exit on error
set -e

# Detect Local IP Address
LOCAL_IP=$(hostname -I | awk '{print $1}')

echo "===================================================="
echo "   Stateful Activity Log - Local Deployment"
echo "===================================================="

# Function to check if a port is in use
is_port_in_use() {
    ss -tuln | grep -q ":$1 "
}

# Find available port
for p in "${PORT_CANDIDATES[@]}"; do
    if ! is_port_in_use "$p"; then
        PORT=$p
        break
    fi
done

# If no port found
if [ -z "$PORT" ]; then
    echo "Error: No available ports (80, 8081, 8082, 8083, 8084, 8085)."
    exit 1
fi

echo "-> Using port: $PORT"

# Check for Docker Compose (plugin or standalone)
if docker compose version >/dev/null 2>&1; then
    DOCKER_CMD="docker compose"
elif docker-compose version >/dev/null 2>&1; then
    DOCKER_CMD="docker-compose"
else
    echo "Error: Docker Compose is not installed."
    echo "This script requires Docker to run the App and PostgreSQL database together."
    exit 1
fi

echo "Step 1: Setting up environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "-> Created .env from .env.example"
fi

# Function to ensure python3 and venv are available
ensure_python_and_venv() {
    if ! command -v python3 >/dev/null 2>&1; then
        echo "-> python3 not found."
        read -p "Would you like to try installing python3? (y/N): " install_py
        if [[ $install_py == [yY] || $install_py == [yY][eE][sS] ]]; then
            if command -v apt-get >/dev/null 2>&1; then
                sudo apt-get update && sudo apt-get install -y python3
            else
                echo "Error: Automated installation only supported for apt-based systems."
                echo "Please install python3 manually."
                return 1
            fi
        else
            return 1
        fi
    fi

    if ! python3 -m venv --help >/dev/null 2>&1; then
        echo "-> python3-venv module not found."
        read -p "Would you like to try installing python3-venv? (y/N): " install_venv
        if [[ $install_venv == [yY] || $install_venv == [yY][eE][sS] ]]; then
            if command -v apt-get >/dev/null 2>&1; then
                sudo apt-get update && sudo apt-get install -y python3-venv
            else
                echo "Error: Automated installation only supported for apt-based systems."
                echo "Please install python3-venv manually."
                return 1
            fi
        else
            return 1
        fi
    fi
    return 0
}

# Step 2: Google Drive Token Check
TOKEN_FILE="./sidecar/token.json"
CREDS_FILE="./sidecar/credentials.json"

if [ ! -f "$TOKEN_FILE" ] || [ ! -s "$TOKEN_FILE" ]; then
    echo "----------------------------------------------------"
    echo "Warning: Google Drive token.json not found or empty."
    echo "The sidecar requires this to perform backups."
    echo "----------------------------------------------------"
    
    if [ -f "$CREDS_FILE" ]; then
        read -p "Would you like to generate token.json now? (y/N): " confirm
        if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
            echo "-> Setting up temporary Python environment for token generation..."
            
            if ensure_python_and_venv; then
                # Setup venv if not exists
                if [ ! -d "sidecar/venv" ]; then
                    python3 -m venv sidecar/venv
                fi
                # Install requirements in venv
                sidecar/venv/bin/pip install --quiet google-auth-oauthlib google-api-python-client
                
                echo "-> Starting token generation. Please follow the instructions in your browser."
                # Run the generation script using venv python
                if (cd sidecar && ./venv/bin/python3 generate_token.py); then
                    echo "-> token.json generated successfully."
                    # Update .env to point to the new token if it was using placeholder
                    if grep -q "GOOGLE_TOKEN_PATH=token.json" .env; then
                        echo "-> .env is already configured for token.json"
                    else
                        # Ensure GOOGLE_TOKEN_PATH is set in .env
                        if grep -q "GOOGLE_TOKEN_PATH=" .env; then
                            sed -i 's|GOOGLE_TOKEN_PATH=.*|GOOGLE_TOKEN_PATH=token.json|' .env
                        else
                            echo "GOOGLE_TOKEN_PATH=token.json" >> .env
                        fi
                        echo "-> Updated GOOGLE_TOKEN_PATH in .env"
                    fi
                else
                    echo "Error: Token generation failed."
                    exit 1
                fi
            else
                echo "Error: Required Python dependencies missing on host."
                echo "Please follow the manual guide: ./token_json_generation_flow.md"
                exit 1
            fi
        else
            echo "-> Skipping token generation. Sidecar may fail to start."
        fi
    else
        echo "Error: sidecar/credentials.json not found."
        echo "Please place your Google API credentials.json in the sidecar/ directory first."
        exit 1
    fi
fi

if command -v npm >/dev/null 2>&1; then
    echo "Step 2: Installing host-side dependencies (Optional, for IDE support)..."
    npm install --silent
    echo "-> Done."
else
    echo "Step 2: Skipping host-side npm install (Not found). Docker will handle all dependencies internally."
fi

echo "Step 3: Starting App + Database via Docker..."

# Ensure vdecent-ingress network exists (required by docker-compose.yaml)
if ! docker network ls | grep -q "vdecent-ingress"; then
    echo "-> Creating external network 'vdecent-ingress'..."
    docker network create vdecent-ingress
fi

# Create local override file with selected port and local volume mounts
cat <<OVERRIDE > docker-compose.local.yaml
services:
  app:
    ports:
      - "$PORT:80"
  sidecar:
    ports:
      - "8000:8000"
    volumes:
      - ./sidecar/credentials.json:/app/credentials.json
      - ./sidecar/token.json:/app/token.json
OVERRIDE

echo "-> Building and launching containers..."
$DOCKER_CMD -f docker-compose.yaml -f docker-compose.local.yaml up --build -d

# Build URLs depending on port
if [ "$PORT" -eq 80 ]; then
    LOCAL_URL="http://localhost"
    NETWORK_URL="http://$LOCAL_IP"
else
    LOCAL_URL="http://localhost:$PORT"
    NETWORK_URL="http://$LOCAL_IP:$PORT"
fi

echo ""
echo "Success! The application is starting up."
echo "Access the web page at:"
echo "1) Local:  $LOCAL_URL"

if [ ! -z "$LOCAL_IP" ]; then
    echo "2) Network: $NETWORK_URL"
    echo "   (Use this URL to access from other PCs in your network)"
fi

echo ""
echo "Useful Commands:"
echo " - View logs:   $DOCKER_CMD logs -f app"
echo " - Stop app:    $DOCKER_CMD down"
echo " - Full Reset:  $DOCKER_CMD down -v (Deletes database data)"
echo "===================================================="
