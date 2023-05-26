
# class_entity.py

class ClassEntity:
    def __init__(self, class_name, docstring):
        self.class_name = class_name
        self.docstring = docstring
        self.methods = {}

    def add_method(self, method_entity):
        self.methods[method_entity.method_name] = method_entity

    def get_method(self, method_name):
        return self.methods.get(method_name, None)
