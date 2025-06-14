#!/bin/bash
# Script to run the Google Slides MCP client with correct environment variables

# Set the path to the MCP script
export TEST_GOOGLE_SLIDES_MCP_SCRIPT_PATH="$(pwd)/test_google_slides_mcp_script.py"

# Check if Google credentials are set
if [ -z "$GOOGLE_CLIENT_ID" ] || [ -z "$GOOGLE_CLIENT_SECRET" ] || [ -z "$GOOGLE_REFRESH_TOKEN" ]; then
  echo "Warning: Google OAuth credentials are not set. You'll need to set these environment variables:"
  echo "  - GOOGLE_CLIENT_ID"
  echo "  - GOOGLE_CLIENT_SECRET"
  echo "  - GOOGLE_REFRESH_TOKEN"
fi

# Run the client
python run_mcp_google_slides_client.py "$@" 