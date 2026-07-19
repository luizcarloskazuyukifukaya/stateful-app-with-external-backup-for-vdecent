#!/bin/bash

# ====================================================
# Stateful Activity Log - Sidecar API Utility
# ----------------------------------------------------
# This script provides a convenient way to interact with 
# the sidecar's REST API for manual operations.
# It automatically loads the auth token from .env.
# ====================================================

set -e

# ----------------------------
# User Specific Definition (depends on the user's environment)
# ----------------------------
# Load environment variables from .env if it exists
if [ -f .env ]; then
    # We use grep/sed to extract the value to avoid side effects of sourcing the whole file
    ENV_TOKEN=$(grep '^RESTORE_AUTH_TOKEN=' .env | cut -d '=' -f2- | tr -d '"'\'' ')
    if [ ! -z "$ENV_TOKEN" ]; then
        RESTORE_AUTH_TOKEN="$ENV_TOKEN"
    fi
fi

# Fallback or default if not in .env
RESTORE_AUTH_TOKEN="${RESTORE_AUTH_TOKEN:-YOUR_OWN_AUTH_TOKEN_IF_NO_DEFINED_IN_ENV_FILE}"
# Define port number
PORT=8000
if [ -f docker-compose.local.yaml ]; then
    DETECTED_PORT=$(grep -A 2 "sidecar:" docker-compose.local.yaml | grep -oE '[0-9]+:8000' | cut -d: -f1 || true)
    if [ ! -z "$DETECTED_PORT" ]; then
        PORT="$DETECTED_PORT"
    fi
fi

# ----------------------------
# Configuration
# ----------------------------
# Detect Local IP Address
LOCAL_IP=$(hostname -I | awk '{print $1}')

# API Base URL
API_BASE_URL="http://$LOCAL_IP:$PORT"

# ----------------------------
# Dependency Check
# ----------------------------

check_dependencies() {

    if ! command -v jq >/dev/null 2>&1; then
        echo "===================================================="
        echo "jq is not installed."
        echo "Installing jq..."
        echo "===================================================="

        sudo apt update
        sudo apt install -y jq

        echo ""
        echo "jq installation completed."
        echo ""
    fi
}

# ----------------------------
# Functions
# ----------------------------

show_help() {
    echo ""
    echo "Usage:"
    echo "  $0 -b                    Trigger backup"
    echo "  $0 -l                    List backups (human readable)"
    echo "  $0 -ld                   List backups (raw JSON)"
    echo "  $0 -p                    Trigger purge"
    echo "  $0 -r <file_id>          Restore backup"
    echo ""
    echo "Examples:"
    echo "  $0 -b"
    echo "  $0 -l"
    echo "  $0 -ld"
    echo "  $0 -p"
    echo "  $0 -r 1AbCdEfGhIjKlMn"
    echo ""
    exit 1
}

trigger_backup() {

    echo "===================================================="
    echo "Triggering Manual Backup..."
    echo "===================================================="

    curl -s -X POST "${API_BASE_URL}/api/backup" \
        -H "X-Auth-Token: ${RESTORE_AUTH_TOKEN}" \
        -H "Content-Type: application/json"

    echo ""
    echo "Backup request completed."
    echo ""
}

list_backups() {

    RAW_MODE="$1"

    echo "===================================================="
    echo "Listing Backups..."
    echo "===================================================="

    RESPONSE=$(curl -s -X GET "${API_BASE_URL}/api/list" \
        -H "X-Auth-Token: ${RESTORE_AUTH_TOKEN}" \
        -H "Content-Type: application/json")

    # Raw JSON output (-ld)
    if [ "$RAW_MODE" = "raw" ]; then
        echo "$RESPONSE"
        echo ""
        return
    fi

    # Human-readable output (-l)

    STATUS=$(echo "$RESPONSE" | jq -r '.status')

    if [ "$STATUS" != "success" ]; then
        echo "ERROR:"
        echo "$RESPONSE"
        exit 1
    fi

    echo ""

    echo "$RESPONSE" | jq -r '
        .backups[] |
        "Name: \(.name) | ID: \(.id) | Size: \(.size) bytes | Created: \(.createdTime)"
    '

    echo ""
}

trigger_purge() {

    echo "===================================================="
    echo "Triggering Manual Purge..."
    echo "===================================================="

    curl -s -X POST "${API_BASE_URL}/api/purge" \
        -H "X-Auth-Token: ${RESTORE_AUTH_TOKEN}" \
        -H "Content-Type: application/json"

    echo ""
    echo "Purge request completed."
    echo ""
}

restore_backup() {

    FILE_ID="$1"

    if [ -z "$FILE_ID" ]; then
        echo "ERROR: Missing Google Drive file_id."
        echo ""
        show_help
    fi

    echo "===================================================="
    echo "Restoring Backup..."
    echo "===================================================="
    echo "File ID: ${FILE_ID}"
    echo ""

    curl -s -X POST "${API_BASE_URL}/api/restore" \
        -H "Content-Type: application/json" \
        -H "X-Auth-Token: ${RESTORE_AUTH_TOKEN}" \
        -d "{
            \"file_id\": \"${FILE_ID}\"
        }"

    echo ""
    echo "Restore request completed."
    echo ""
}

# ----------------------------
# Main
# ----------------------------

check_dependencies

if [ $# -eq 0 ]; then
    show_help
fi

# Special handling for -ld
if [ "$1" = "-ld" ]; then
    list_backups "raw"
    exit 0
fi

while getopts ":blpr:" opt; do
    case ${opt} in
        b)
            trigger_backup
            exit 0
            ;;
        l)
            list_backups
            exit 0
            ;;
        p)
            trigger_purge
            exit 0
            ;;
        r)
            restore_backup "$OPTARG"
            exit 0
            ;;
        *)
            show_help
            ;;
    esac
done

show_help
