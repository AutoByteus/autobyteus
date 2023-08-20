"""
unique_id_generator.py: Provides a UniqueIDGenerator class to generate universally unique identifiers (UUIDs).

The UniqueIDGenerator class enables the generation of UUIDs using the uuid module. It offers a static method to generate a UUID and return it as a string.

Features:
- Define a static method to generate a UUID using the uuid.uuid4() function.
- Return the generated UUID as a string.
"""

import uuid


class UniqueIDGenerator:
    """
    A class to generate unique IDs using the uuid module.
    """

    @staticmethod
    def generate_id() -> str:
        """
        Generate a UUID using the uuid.uuid4() function and return it as a string.

        Returns:
            str: A string representation of the generated UUID.
        """
        return str(uuid.uuid4())

