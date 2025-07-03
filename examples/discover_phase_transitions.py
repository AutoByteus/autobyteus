# file: autobyteus/examples/discover_phase_transitions.py
"""
This example script demonstrates how to use the PhaseTransitionDiscoverer
to programmatically find all valid phase transitions within the agent lifecycle.

This is useful for developers who want to create their own BasePhaseHook
subclasses, as it provides a definitive list of the source and target phases
they can hook into.
"""
import sys
from pathlib import Path
from typing import List, Dict, Any

# --- Boilerplate to make the script runnable from the project root ---
SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

try:
    from autobyteus.agent.phases import PhaseTransitionDiscoverer, PhaseTransitionInfo
except ImportError as e:
    print(f"Error importing autobyteus components: {e}", file=sys.stderr)
    print("Please ensure that the autobyteus library is installed and accessible.", file=sys.stderr)
    sys.exit(1)


def _prepare_table_data(transitions: List[PhaseTransitionInfo]) -> List[Dict[str, str]]:
    """Transforms transition info objects into a list of dictionaries for printing."""
    table_data = []
    for t in transitions:
        from_str = "\n".join([p.value for p in t.source_phases])
        table_data.append({
            "From": from_str,
            "To": t.target_phase.value,
            "Trigger": f"AgentPhaseManager.{t.triggering_method}()",
            "Description": t.description,
        })
    return table_data

def _print_as_table(data: List[Dict[str, str]]):
    """Calculates column widths and prints the data in a formatted table."""
    if not data:
        return

    headers = list(data[0].keys())
    
    # Calculate max widths for each column
    widths = {h: len(h) for h in headers}
    for row in data:
        for h in headers:
            # Check max width line-by-line for multiline content
            max_line_width = max(len(line) for line in row[h].split('\n')) if row[h] else 0
            widths[h] = max(widths[h], max_line_width)

    # --- Print Header ---
    header_line = " | ".join(h.ljust(widths[h]) for h in headers)
    separator_line = "-+-".join("-" * widths[h] for h in headers)
    print(header_line)
    print(separator_line)

    # --- Print Rows ---
    for row in data:
        # Split multiline content to handle rowspan alignment
        split_rows = [
            {h: row[h].split('\n') for h in headers}
        ]
        
        num_lines = max(len(split_rows[0][h]) for h in headers)
        
        for i in range(num_lines):
            line_parts = []
            for h in headers:
                cell_lines = split_rows[0][h]
                part = cell_lines[i] if i < len(cell_lines) else ""
                line_parts.append(part.ljust(widths[h]))
            print(" | ".join(line_parts))
        
        # Print a thin separator between table rows for readability
        print("-+-".join("-" * (w) for w in widths.values()))


def main():
    """
    Discovers and prints all available agent phase transitions.
    """
    print("--- Discovering all available agent phase transitions ---")
    print("This table shows every possible transition you can create a custom hook for.\n")

    all_transitions = PhaseTransitionDiscoverer.discover()

    if not all_transitions:
        print("No transitions were discovered. This is unexpected.")
        return

    # Prepare and print the data
    table_data = _prepare_table_data(all_transitions)
    _print_as_table(table_data)

    print(f"\nTotal of {len(all_transitions)} unique transitions discovered.")


if __name__ == "__main__":
    main()
