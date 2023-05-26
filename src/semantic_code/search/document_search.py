# search_engine.py

class DocumentSearcher:
    def accept_query(self, query):
        """
        Accept a natural language query.
        """
        pass

    def query_to_vector(self):
        """
        Convert the query into a vector using the Vectorizer.
        """
        pass

    def get_relevant_methods(self):
        """
        Retrieve vectors from the VectorDBManager that are similar to the query vector,
        decode these vectors into methods using the Vectorizer, and return the methods.
        """
        pass
