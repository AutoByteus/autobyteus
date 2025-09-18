import logging
from typing import List, Optional, Dict, Union

from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from textual.widgets import Static

from autobyteus.task_management.task import Task
from autobyteus.task_management.base_task_board import TaskStatus
from .shared import TASK_STATUS_ICONS, LOG_ICON

logger = logging.getLogger(__name__)

class TaskBoardPanel(Static):
    """A widget to display the team's task board."""

    def __init__(self, tasks: Optional[List[Task]], statuses: Dict[str, TaskStatus], team_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.tasks = tasks or []
        self.statuses = statuses or {}
        self.team_name = team_name

    def compose(self) -> None:
        if not self.tasks:
            yield Static(Panel("No task plan has been published yet.", title="Task Board", border_style="yellow", title_align="left"))
            return

        table = Table(
            expand=True,
            show_header=True,
            header_style="bold magenta",
            show_lines=True
        )
        table.add_column("ID", justify="left", style="cyan", no_wrap=True, min_width=10)
        table.add_column("Name", style="white", min_width=15)
        table.add_column("Status", justify="left", style="white")
        table.add_column("Assigned To", justify="center", style="green")
        table.add_column("Deliverables", justify="left", style="cyan", min_width=30)
        table.add_column("Depends On", justify="center", style="dim")

        # Create a name-to-ID map to resolve dependency names
        id_to_name_map = {task.task_id: task.task_name for task in self.tasks}
        
        # Sort tasks by name for consistent ordering
        sorted_tasks = sorted(self.tasks, key=lambda t: t.task_name)

        for task in sorted_tasks:
            task_status = self.statuses.get(task.task_id, TaskStatus.NOT_STARTED)
            status_icon = TASK_STATUS_ICONS.get(task_status, "❓")
            status_text = f"{status_icon} {task_status.value.upper().replace('_', ' ')}"
            
            status_style = "default"
            if task_status == TaskStatus.COMPLETED:
                status_style = "strike dim green"
            elif task_status == TaskStatus.FAILED:
                status_style = "bold red"
            
            # Create a renderable for the deliverables column
            deliverables_renderable: Union[str, Text] = "N/A"
            if task.file_deliverables:
                text = Text()
                for i, d in enumerate(task.file_deliverables):
                    if i > 0:
                        text.append("\n") # Add a newline for spacing between deliverables
                    text.append(f"{LOG_ICON} {d.file_path}\n", style="bold")
                    text.append(f"   └─ {d.summary}", style="dim")
                deliverables_renderable = text

            # Resolve dependency IDs to names for display
            dep_names = [id_to_name_map.get(dep_id, dep_id) for dep_id in task.dependencies]

            table.add_row(
                task.task_id,
                task.task_name,
                Text(status_text, style=status_style),
                task.assignee_name or "N/A",
                deliverables_renderable,
                ", ".join(dep_names)
            )

        yield Static(Panel(table, title="Task Board", border_style="blue", title_align="left"))
