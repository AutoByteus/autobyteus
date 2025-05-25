import pytest
from typing import Dict, Optional, Any

from autobyteus.tools.base_tool import BaseTool
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterDefinition, ParameterType

class MockTool(BaseTool):
    """A configurable mock tool for testing system prompt processing."""
    
    _class_level_name = "MockToolClassDefaultName"
    _class_level_description = "Mock tool class default description."

    def __init__(self, 
                 name: str, 
                 description: str, 
                 args_schema: Optional[ParameterSchema] = None, 
                 xml_output: Optional[str] = None,
                 execute_should_raise: Optional[Exception] = None,
                 xml_should_raise: Optional[Exception] = None):
        # Initialize instance attributes BEFORE calling super().__init__()
        self._instance_name = name
        self._instance_description = description
        self._instance_args_schema = args_schema
        self._xml_output = xml_output
        self._execute_should_raise = execute_should_raise
        self._xml_should_raise = xml_should_raise
        
        super().__init__() # Call superclass __init__ after instance attributes are set.

    @classmethod
    def get_name(cls) -> str:
        return cls._class_level_name
    
    @property
    def name(self) -> str: # type: ignore[override]
        return self._instance_name

    @classmethod
    def get_description(cls) -> str:
        return cls._class_level_description

    @classmethod
    def get_argument_schema(cls) -> Optional[ParameterSchema]:
        default_schema = ParameterSchema() # No description argument here
        default_schema.add_parameter(ParameterDefinition(
            name="mock_arg_class",
            param_type=ParameterType.STRING,
            description="A class-level mock argument.",
            required=False
        ))
        return default_schema

    def tool_usage_xml(self) -> str: # Instance method override
        if self._xml_should_raise:
            raise self._xml_should_raise
        if self._xml_output is not None:
            return self._xml_output
        
        schema_to_use = self._instance_args_schema
        
        xml_parts = [f'<command name="{self._instance_name}" description="{self._instance_description}">']
        if schema_to_use:
            for param_name, param_def in schema_to_use.parameters.items():
                xml_parts.append(f'  <arg name="{param_name}" type="{param_def.param_type.value}" required="{str(param_def.required).lower()}">{param_def.description}</arg>')
        xml_parts.append('</command>')
        return "\n".join(xml_parts)

    async def _execute(self, context: Optional[Any] = None, **kwargs: Any) -> Any: # pragma: no cover
        if self._execute_should_raise:
            raise self._execute_should_raise
        return f"MockTool '{self._instance_name}' executed with {kwargs}"


@pytest.fixture
def mock_tool_alpha() -> MockTool:
    """Provides a simple mock tool named 'AlphaTool'."""
    return MockTool(
        name="AlphaTool", 
        description="Description for Alpha.",
        xml_output="<command name=\"AlphaTool\" description=\"Description for Alpha.\"></command>"
    )

@pytest.fixture
def mock_tool_beta() -> MockTool:
    """Provides another mock tool named 'BetaTool' with arguments."""
    # THIS IS THE CORRECTED LINE: ParameterSchema() is called without 'description'
    beta_schema = ParameterSchema() 
    beta_schema.add_parameter(ParameterDefinition(name="param1", param_type=ParameterType.STRING, description="First param for Beta.", required=True))
    return MockTool(
        name="BetaTool", 
        description="Description for Beta.",
        args_schema=beta_schema,
        xml_output='<command name="BetaTool" description="Description for Beta.">\n  <arg name="param1" type="string" required="true">First param for Beta.</arg>\n</command>'
    )

@pytest.fixture
def mock_tool_empty_xml() -> MockTool:
    """A mock tool that returns an empty string for its XML representation."""
    return MockTool(
        name="EmptyXmlTool", 
        description="This tool returns empty XML.", 
        xml_output=""
    )

@pytest.fixture
def mock_tool_xml_error() -> MockTool:
    """A mock tool whose tool_usage_xml() method raises an error."""
    return MockTool(
        name="XmlErrorTool", 
        description="This tool errors on XML generation.", 
        xml_should_raise=RuntimeError("Simulated XML generation failure")
    )
