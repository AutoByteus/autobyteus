# file: autobyteus/tests/unit_tests/task_management/converters/test_task_plan_converter.py
import pytest
from autobyteus.task_management import (
    TaskPlanConverter,
    TaskPlanDefinitionSchema,
    TaskDefinitionSchema,
    TaskPlan,
    Task,
)

@pytest.fixture
def sample_plan_definition_schema() -> TaskPlanDefinitionSchema:
    """Provides a sample TaskPlanDefinitionSchema as if it came from an LLM."""
    return TaskPlanDefinitionSchema(
        overall_goal="Create a simple web app.",
        tasks=[
            TaskDefinitionSchema(
                task_name="setup_backend",
                assignee_name="BackendDev",
                description="Set up the Flask server.",
                dependencies=[]
            ),
            TaskDefinitionSchema(
                task_name="create_frontend",
                assignee_name="FrontendDev",
                description="Create the React frontend.",
                dependencies=[]
            ),
            TaskDefinitionSchema(
                task_name="connect_api",
                assignee_name="BackendDev",
                description="Connect frontend to backend.",
                dependencies=["setup_backend", "create_frontend"]
            ),
        ]
    )

def test_from_schema_creates_task_plan(sample_plan_definition_schema: TaskPlanDefinitionSchema):
    """Tests that the converter returns a TaskPlan instance."""
    # Act
    result = TaskPlanConverter.from_schema(sample_plan_definition_schema)
    
    # Assert
    assert isinstance(result, TaskPlan)
    assert result.overall_goal == sample_plan_definition_schema.overall_goal
    assert len(result.tasks) == len(sample_plan_definition_schema.tasks)

def test_from_schema_generates_ids(sample_plan_definition_schema: TaskPlanDefinitionSchema):
    """Tests that system IDs are generated for the plan and tasks."""
    # Act
    result = TaskPlanConverter.from_schema(sample_plan_definition_schema)

    # Assert
    assert result.plan_id.startswith("plan_")
    for task in result.tasks:
        assert task.task_id.startswith("task_")

def test_from_schema_hydrates_dependencies(sample_plan_definition_schema: TaskPlanDefinitionSchema):
    """Tests that task_name dependencies are correctly converted to task_id dependencies."""
    # Act
    result = TaskPlanConverter.from_schema(sample_plan_definition_schema)

    # Assert
    backend_task = next(t for t in result.tasks if t.task_name == "setup_backend")
    frontend_task = next(t for t in result.tasks if t.task_name == "create_frontend")
    connect_task = next(t for t in result.tasks if t.task_name == "connect_api")

    # The dependencies list should contain the system-generated task_ids
    assert len(connect_task.dependencies) == 2
    assert backend_task.task_id in connect_task.dependencies
    assert frontend_task.task_id in connect_task.dependencies
    
    # The original task_names should not be in the final dependency list
    assert "setup_backend" not in connect_task.dependencies

def test_from_schema_handles_invalid_dependency(sample_plan_definition_schema: TaskPlanDefinitionSchema):
    """Tests that the converter raises an error for a dependency that doesn't exist."""
    # Arrange
    sample_plan_definition_schema.tasks[2].dependencies.append("non_existent_task")

    # Act & Assert
    with pytest.raises(ValueError, match="invalid dependency"):
        TaskPlanConverter.from_schema(sample_plan_definition_schema)
