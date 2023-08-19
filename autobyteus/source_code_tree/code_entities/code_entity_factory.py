
from src.source_code_tree.code_entities.base_entity import CodeEntity
from src.source_code_tree.code_entities.class_entity import ClassEntity
from src.source_code_tree.code_entities.code_entity_type import CodeEntityType
from src.source_code_tree.code_entities.function_entity import FunctionEntity
from src.source_code_tree.code_entities.method_entity import MethodEntity
from src.source_code_tree.code_entities.module_entity import ModuleEntity



class CodeEntityFactory:
    @staticmethod
    def create_entity(type: str, representation: str) -> CodeEntity:
        """
        Factory method to create and return the correct CodeEntity instance.
        
        Args:
            type (str): The type of the entity.
            representation (str): The JSON representation of the entity.
        
        Returns:
            CodeEntity: The created CodeEntity instance.
        """
        if CodeEntityType(type) == CodeEntityType.CLASS:
            return ClassEntity.from_json(representation)
        elif CodeEntityType(type) == CodeEntityType.FUNCTION:
            return FunctionEntity.from_json(representation)
        elif CodeEntityType(type) == CodeEntityType.MODULE:
            return ModuleEntity.from_json(representation)
        elif CodeEntityType(type) == CodeEntityType.METHOD:
            return MethodEntity.from_json(representation)
        else:
            raise ValueError(f"Invalid type: {type}")

