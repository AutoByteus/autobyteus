#!/usr/bin/env python3
"""
Minimal CLI test script to demonstrate proper input prompt handling.
This script shows how to correctly display the "You: " prompt and read user input.
"""
import sys
import asyncio

def print_with_flush(text, file=sys.stdout):
    """Print text and flush the file descriptor."""
    file.write(text)
    file.flush()

async def main():
    """Main function that demonstrates proper input prompting."""
    print("\n=== MINIMAL CLI TEST ===")
    print("This script demonstrates proper input prompt handling.")
    print("Type 'exit' to quit.\n")
    
    while True:
        # Method 1: Using sys.stdout directly (recommended)
        print_with_flush("You: ")
        
        # Read input using asyncio to simulate how the agent CLI would do it
        loop = asyncio.get_event_loop()
        user_input = await loop.run_in_executor(None, input)
        
        if user_input.lower() == 'exit':
            print("Exiting...")
            break
        
        # Echo back what the user typed
        print(f"\nYou typed: {user_input}\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScript interrupted by user.")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1) 