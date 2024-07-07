# autobyteus/semantic_code/search/search_result.py

import json
from typing import List

from autobyteus.source_code_tree.code_entities.base_entity import CodeEntity

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

    def to_dict(self) -> dict:
        """
        Convert the scored entity to dictionary representation.

        :return: A dictionary representation of the scored entity.
        :rtype: dict
        """
        return {
            "entity": json.loads(self.entity.to_json()), # Convert entity JSON string to dict
            "score": self.score
        }

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

    def to_json(self) -> str:
        """
        Convert the search result to json representation.

        :return: A json representation of the search result.
        :rtype: str
        """
        result_dict = {
            "total": self.total,
            "entities": [entity.to_dict() for entity in self.entities]
        }
        return json.dumps(result_dict)
