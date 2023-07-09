from typing import List

from src.source_code_tree.code_entities.base_entity import CodeEntity

class ScoredEntity:
    """
    Represents a code entity with an associated score.

    Args:
        entity (CodeEntity): The code entity.
        score (float): The score of the entity.
    """
    def __init__(self, entity: CodeEntity, score: float):
        self.entity = entity
        self.score = score

class SearchResult:
    """
    Represents a search result, containing the total count of results, 
    and a list of ScoredEntity objects.

    Args:
        total (int): The total count of results.
        entities (List[ScoredEntity]): A list of scored entities.
    """

    def __init__(self, total: int, entities: List[ScoredEntity]):
        self.total = total
        self.entities = entities


