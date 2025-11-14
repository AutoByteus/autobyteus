# file: autobyteus/autobyteus/tools/bash/types.py
from dataclasses import dataclass

@dataclass(frozen=True)
class BashExecutionResult:
    """
    Represents the complete result of a bash command execution.
    """
    exit_code: int
    stdout: str
    stderr: str

    def __str__(self) -> str:
        """
        Provides a clean, multi-line string representation suitable for an LLM.
        """
        output_parts = []
        if self.stdout:
            output_parts.append(f"STDOUT:\n{self.stdout}")
        if self.stderr:
            output_parts.append(f"STDERR:\n{self.stderr}")

        if not output_parts:
            output_parts.append("Command produced no output on stdout or stderr.")

        return (
            f"COMMAND EXECUTION COMPLETED\n"
            f"Exit Code: {self.exit_code}\n"
            f"-----------------------------\n"
            f"\n\n".join(output_parts)
        )
