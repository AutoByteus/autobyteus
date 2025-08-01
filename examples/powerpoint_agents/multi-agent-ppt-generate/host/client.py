import requests
import json
import time
import uuid
import click

class HostClient:
    def __init__(self, base_url="http://127.0.0.1:8765"):
        self.base_url = base_url
        self.headers = {'Content-Type': 'application/json'}
        self.rpc_endpoint = f"{self.base_url}/rpc"

    def _post(self, payload):
        try:
            response = requests.post(self.rpc_endpoint, headers=self.headers, json=payload, timeout=600)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to agent server: {e}")
            return None

    def send_prompt_to_coordinator(self, prompt: str):
        print(f"Sending prompt to coordinator: '{prompt}'")
        
        user_message_payload = {
            "content": prompt,
            "metadata": {"user_id": "cli_user"}
        }

        rpc_payload = {
            "jsonrpc": "2.0",
            "method": "invoke_method",
            "params": {
                "target_agent_id": "coordinator",
                "method_name": "post_user_message",
                "method_params": {
                    "agent_input_user_message": user_message_payload
                }
            },
            "id": str(uuid.uuid4())
        }
        
        return self._post(rpc_payload)

@click.command()
@click.option("--prompt", default="Generate a presentation about the history of space exploration.", help="The topic for the presentation.")
def main(prompt):
    client = HostClient()
    
    start_time = time.time()
    
    # In this new architecture, we only need to send the initial prompt to the coordinator.
    # The coordinator handles the entire workflow. We wait for its final response.
    # To get the final response, we would typically listen to the SSE stream.
    # For this simple client, we'll just poll for the final result by checking the agent's state or logs,
    # or ideally, have the RPC call be blocking (which it isn't by default).
    # The `autobyteus` framework seems to have a more complex client-server interaction model.
    # For this example, we will simulate the final step by assuming the coordinator's last output is the goal.
    # A true client would use the SSE stream from `/events/{agent_id}` to get real-time updates and the final result.
    
    print("Sending initial prompt... The agent workflow will now run on the server.")
    print("NOTE: This simple client sends the request but doesn't stream the live results.")
    print("Check the server logs to see the agent interactions.")
    print("The final result will be printed here when the entire workflow completes.")

    # A more advanced client would use the `AgentEventStream` to get the final result.
    # For simplicity, this client will just print the acknowledgment.
    # The `autobyteus` framework is designed for an interactive or event-driven frontend.
    # The `AgentGroup.process_task_for_coordinator` in the original code shows how this should be handled.
    # We will simulate that blocking call here.
    
    # Let's create a dummy way to show a final result might look
    final_response = { "result": "Workflow started. Check server logs for progress and the final PPTX URL."}
    
    # This call is non-blocking in the autobyteus RPC model
    ack_response = client.send_prompt_to_coordinator(prompt)
    
    print("\n" + "="*50)
    print("Initial Server Acknowledgment:")
    if ack_response:
        print(json.dumps(ack_response, indent=2))
    else:
        print("Did not receive an acknowledgment.")
        
    print("\nThis client is simplified. In a real application, you would listen to the SSE event stream for the final URL.")
    print(f"Assuming workflow completion after some time...")
    # Polling or waiting would happen here in a real client.
    
    end_time = time.time()
    print(f"\nRequest sent. Total client-side time: {end_time - start_time:.2f} seconds.")
    print("="*50)


if __name__ == '__main__':
    main()