# file_entity.py

class FileEntity:
    def __init__(self, file_path, docstring):
        self.file_path = file_path
        self.docstring = docstring
        self.classes = {}

    def add_class(self, class_entity):
        self.classes[class_entity.class_name] = class_entity

    def get_class(self, class_name):
        return self.classes.get(class_name, None)

