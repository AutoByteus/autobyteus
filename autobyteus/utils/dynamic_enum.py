from enum import Enum, EnumMeta
from typing import Any

class DynamicEnumMeta(EnumMeta):
    def __new__(metacls, cls, bases, classdict):
        enum_class = super().__new__(metacls, cls, bases, classdict)
        enum_class._additional_members = {}
        return enum_class

    def __getattr__(cls, name):
        if name in cls._additional_members:
            return cls._additional_members[name]
        raise AttributeError(f"{cls.__name__} has no attribute {name}")

class DynamicEnum(Enum, metaclass=DynamicEnumMeta):
    @classmethod
    def _add_member(cls, name: str, value: Any) -> None:
        if name in cls.__members__ or name in cls._additional_members:
            raise ValueError(f"Name {name} already exists in {cls.__name__}")
        if value in cls._value2member_map_:
            raise ValueError(f"Value {value} already exists in {cls.__name__}")
        
        # Create the new member
        member = object.__new__(cls)
        member._name_ = name
        member._value_ = value
        
        # Add the new member to the additional members dictionary
        cls._additional_members[name] = member
        cls._value2member_map_[value] = member

    @classmethod
    def add(cls, name: str, value: Any) -> 'DynamicEnum':
        cls._add_member(name, value)
        return cls._additional_members[name]