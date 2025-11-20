#!/bin/bash
# Quick script to run SEC to Box E2E test

echo "=================================================="
echo "SEC to Box E2E Test Runner"
echo "=================================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Please copy .env.example to .env and configure it"
    exit 1
fi

# Source .env to check configuration
source .env

# Check required variables
MISSING_VARS=()

if [ -z "$BOX_MCP_SERVER_PATH" ] && [ -z "$BOX_MCP_SERVER_URL" ]; then
    MISSING_VARS+=("BOX_MCP_SERVER_PATH or BOX_MCP_SERVER_URL")
fi

if [ -z "$BOX_RATINGS_FOLDER_ID" ]; then
    MISSING_VARS+=("BOX_RATINGS_FOLDER_ID")
fi

if [ -z "$SEC_USER_AGENT" ]; then
    MISSING_VARS+=("SEC_USER_AGENT")
fi

if [ ${#MISSING_VARS[@]} -gt 0 ]; then
    echo "❌ Missing required environment variables:"
    for var in "${MISSING_VARS[@]}"; do
        echo "   - $var"
    done
    echo ""
    echo "Please configure these in your .env file"
    exit 1
fi

echo "✅ Environment configuration verified"
echo ""

# Check if Box MCP server is running (if using SSE)
if [ -n "$BOX_MCP_SERVER_URL" ]; then
    echo "🔍 Checking Box MCP server at $BOX_MCP_SERVER_URL..."
    if curl -s -f "$BOX_MCP_SERVER_URL" > /dev/null 2>&1; then
        echo "✅ Box MCP server is responding"
    else
        echo "⚠️  Warning: Could not reach Box MCP server"
        echo "   Make sure it's running before proceeding"
        echo ""
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    echo ""
fi

# Run the test
echo "🚀 Running SEC to Box E2E test..."
echo ""

pytest tests/integration/test_sec_to_box_e2e.py::TestSECToBoxE2E::test_download_sec_and_upload_to_box -v -s

TEST_EXIT_CODE=$?

echo ""
echo "=================================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ Test completed successfully!"
else
    echo "❌ Test failed with exit code $TEST_EXIT_CODE"
fi
echo "=================================================="

exit $TEST_EXIT_CODE
