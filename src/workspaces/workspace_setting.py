class WorkspaceSetting:
    """
    Class to store the parsed workspace structure and other related objects.
    """
    def __init__(self, root_path: str):
        self.root_path = root_path
        self.structure = None

    def parse_structure(self):
        """
        Parses and stores the workspace structure.
        """