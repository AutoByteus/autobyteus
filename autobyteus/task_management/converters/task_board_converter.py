# file: autobyteus/autobyteus/task_management/converters/task_board_converter.py
"""
Contains converters for translating internal task management objects into
LLM-friendly Pydantic schemas.
"""
import logging
from typing import Optional

from autobyteus.task_management.base_task_board import BaseTaskBoard
from autobyteus.task_management.schemas import TaskStatusReportSchema, TaskStatusReportItemSchema

logger = logging.getLogger(__name__)

class TaskBoardConverter:
    """A converter to transform TaskBoard state into LLM-friendly schemas."""

    @staticmethod
    def to_schema(task_board: BaseTaskBoard) -> Optional[TaskStatusReportSchema]:
        """
        Converts the current state of a TaskBoard into a TaskStatusReportSchema.

        Args:
            task_board: The task board instance to convert.

        Returns:
            A TaskStatusReportSchema object if there are tasks, otherwise None.
        """
        if not task_board.tasks:
            logger.debug(f"TaskBoard for team '{task_board.team_id}' has no tasks. Cannot generate report.")
            return None

        internal_status = task_board.get_status_overview()
        
        id_to_name_map = {task.task_id: task.task_name for task in task_board.tasks}
        
        report_items = []
        for task in task_board.tasks:
            dep_names = [id_to_name_map.get(dep_id, str(dep_id)) for dep_id in task.dependencies]
            
            report_item = TaskStatusReportItemSchema(
                task_name=task.task_name,
                assignee_name=task.assignee_name,
                description=task.description,
                dependencies=dep_names,
                status=internal_status["task_statuses"].get(task.task_id),
                file_deliverables=task.file_deliverables
            )
            report_items.append(report_item)

        status_report = TaskStatusReportSchema(
            tasks=report_items
        )
        
        logger.debug(f"Successfully converted TaskBoard state to TaskStatusReportSchema for team '{task_board.team_id}'.")
        return status_report
