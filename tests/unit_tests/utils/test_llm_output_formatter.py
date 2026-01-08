import pytest
from dataclasses import dataclass
from typing import List, Dict
try:
    from pydantic import BaseModel
except ImportError:
    BaseModel = None

from autobyteus.utils.llm_output_formatter import format_to_clean_string

def test_format_simple_dict():
    data = {"key": "value", "foo": "bar"}
    expected = "key: value\nfoo: bar"
    assert format_to_clean_string(data) == expected

def test_format_list():
    data = ["item1", "item2"]
    expected = "- item1\n- item2"
    assert format_to_clean_string(data) == expected

def test_format_nested_dict():
    data = {"parent": {"child": "value"}}
    expected = "parent:\n  child: value"
    assert format_to_clean_string(data) == expected

def test_format_list_of_dicts():
    data = [
        {"name": "A", "val": 1},
        {"name": "B", "val": 2}
    ]
    expected = "- \n  name: A\n  val: 1\n- \n  name: B\n  val: 2"
    assert format_to_clean_string(data) == expected

def test_format_multiline_string():
    data = {"code": "def foo():\n    return True"}
    # Multiline strings now appear on a new line for better readability
    expected = "code:\n  def foo():\n      return True"
    assert format_to_clean_string(data) == expected

@dataclass
class MyDataClass:
    name: str
    value: int

def test_format_dataclass():
    obj = MyDataClass(name="Test", value=10)
    # Expected behavior: treated as a dict
    # name: Test
    # value: 10
    expected = "name: Test\nvalue: 10"
    assert format_to_clean_string(obj) == expected

def test_format_dataclass_nested():
    @dataclass
    class Container:
        inner: MyDataClass
    
    obj = Container(inner=MyDataClass(name="Inner", value=99))
    expected = "inner:\n  name: Inner\n  value: 99"
    assert format_to_clean_string(obj) == expected

if BaseModel:
    class MyPydanticModel(BaseModel):
        field: str
        count: int

    def test_format_pydantic_model():
        obj = MyPydanticModel(field="hello", count=5)
        expected = "field: hello\ncount: 5"
        assert format_to_clean_string(obj) == expected
