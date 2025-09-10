# file: autobyteus/tests/unit_tests/tools/test_pydantic_schema_converter.py
import pytest
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

from autobyteus.tools.pydantic_schema_converter import pydantic_to_parameter_schema
from autobyteus.tools.parameter_schema import ParameterSchema, ParameterType

# --- Pydantic Models for Testing ---

class Address(BaseModel):
    """A nested address model."""
    street: str = Field(..., description="Street name and number.")
    city: str = Field(..., description="City name.")

class Person(BaseModel):
    """A complex model for testing conversion."""
    name: str = Field(..., description="The person's full name.")
    age: Optional[int] = Field(None, description="The person's age.")
    tags: List[str] = Field(default_factory=list, description="A list of tags.")
    address: Address = Field(..., description="The person's primary address.")
    prior_addresses: List[Address] = Field(default_factory=list, description="List of prior addresses.")

# --- Tests ---

@pytest.fixture
def converted_schema() -> ParameterSchema:
    """Provides a converted schema for all test functions."""
    return pydantic_to_parameter_schema(Person)

def test_pydantic_conversion_basic_types(converted_schema: ParameterSchema):
    """Tests conversion of basic Pydantic types (str, Optional[int], etc.)."""
    assert len(converted_schema.parameters) == 5

    # Test 'name' (required str)
    name_param = converted_schema.get_parameter("name")
    assert name_param is not None
    assert name_param.param_type == ParameterType.STRING
    assert name_param.required is True
    assert name_param.description == "The person's full name."

    # Test 'age' (Optional[int])
    age_param = converted_schema.get_parameter("age")
    assert age_param is not None
    assert age_param.param_type == ParameterType.INTEGER
    assert age_param.required is False
    assert age_param.description == "The person's age."

def test_pydantic_conversion_array_of_primitives(converted_schema: ParameterSchema):
    """Tests conversion of a list of primitive types (List[str])."""
    tags_param = converted_schema.get_parameter("tags")
    assert tags_param is not None
    assert tags_param.param_type == ParameterType.ARRAY
    assert tags_param.required is False
    assert tags_param.description == "A list of tags."
    assert tags_param.array_item_schema == {"type": "string"}

def test_pydantic_conversion_nested_object(converted_schema: ParameterSchema):
    """Tests conversion of a nested Pydantic model."""
    address_param = converted_schema.get_parameter("address")
    assert address_param is not None
    assert address_param.param_type == ParameterType.OBJECT
    assert address_param.required is True
    assert address_param.object_schema is not None
    
    nested_addr_schema = address_param.object_schema
    assert isinstance(nested_addr_schema, ParameterSchema)
    assert len(nested_addr_schema.parameters) == 2
    
    street_param = nested_addr_schema.get_parameter("street")
    assert street_param is not None
    assert street_param.param_type == ParameterType.STRING
    assert street_param.required is True
    assert street_param.description == "Street name and number."

def test_pydantic_conversion_array_of_objects(converted_schema: ParameterSchema):
    """
    Tests the corrected conversion of a list of nested Pydantic models.
    This is the key test to validate the fix.
    """
    prior_addr_param = converted_schema.get_parameter("prior_addresses")
    assert prior_addr_param is not None
    assert prior_addr_param.param_type == ParameterType.ARRAY
    assert prior_addr_param.required is False
    
    # Assert that the item schema is a ParameterSchema instance, NOT a dict
    item_schema = prior_addr_param.array_item_schema
    assert isinstance(item_schema, ParameterSchema)
    
    # Assert the structure of the nested item schema
    assert len(item_schema.parameters) == 2
    
    street_param = item_schema.get_parameter("street")
    assert street_param is not None
    assert street_param.param_type == ParameterType.STRING
    assert street_param.required is True
    
    city_param = item_schema.get_parameter("city")
    assert city_param is not None
    assert city_param.param_type == ParameterType.STRING
    assert city_param.required is True
