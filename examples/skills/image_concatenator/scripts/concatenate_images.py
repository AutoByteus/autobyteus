#!/usr/bin/env python3
import sys
import os

def concatenate_images(output_path, input_paths):
    print(f"--- Image Concatenator Tool ---")
    print(f"Output: {output_path}")
    print(f"Inputs: {input_paths}")
    
    # Check if input files exist
    for path in input_paths:
        if not os.path.exists(path):
            print(f"Error: Input file not found: {path}")
            sys.exit(1)

    print(f"Simulating vertical concatenation of {len(input_paths)} images...")
    
    # Create a dummy output file to satisfy the agent's expectation of a result
    with open(output_path, "w") as f:
        f.write(f"Dummy image content created from: {', '.join(input_paths)}")
        
    print(f"Success! Created {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python concatenate_images.py <output_path> <input_path1> [input_path2 ...]")
        sys.exit(1)
        
    output = sys.argv[1]
    inputs = sys.argv[2:]
    concatenate_images(output, inputs)
