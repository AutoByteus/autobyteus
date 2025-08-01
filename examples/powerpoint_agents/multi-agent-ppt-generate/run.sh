#!/bin/bash
trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT

# Start the services in the background
echo "Starting Agent Server..."
python host/main.py &
AGENT_SERVER_PID=$!
sleep 5 # Give the server a moment to start up

echo "Agent Server started with PID $AGENT_SERVER_PID"
echo "To interact with the agent, run the client in another terminal:"
echo "python host/client.py --prompt \"Create a presentation about the impact of AI on the automotive industry.\""
echo ""
echo "Press Ctrl+C to stop all services."

# Wait for the agent server process to exit
wait $AGENT_SERVER_PID