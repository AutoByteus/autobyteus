class CodeEntity:
    def __init__(self, docstring):
        self.docstring = docstring

    def to_vector(self):
        pass  # TODO: Implement or delegate the vectorization logic


class ModuleEntity(CodeEntity):
    def __init__(self, file_path, docstring, classes=None, functions=None):
        super().__init__(docstring)
        self.file_path = file_path
        self.classes = classes or {}
        self.functions = functions or {}

    def add_class(self, class_entity):
        self.classes[class_entity.class_name] = class_entity

    def add_function(self, function_entity):
        self.functions[function_entity.name] = function_entity



class FunctionEntity(CodeEntity):
    def __init__(self, name, docstring, signature):
        super().__init__(docstring)
        self.name = name
        self.signature = signature

    # You may want to add methods to get the function signature.


class ClassEntity(CodeEntity):
    def __init__(self, docstring, class_name, methods=None):
        super().__init__(docstring)
        self.class_name = class_name
        self.methods = methods or {}

    def add_method(self, method_entity):
        self.methods[method_entity.name] = method_entity


class MethodEntity(CodeEntity):
    def __init__(self, name, docstring, signature):
        super().__init__(docstring)
        self.name = name
        self.signature = signature

    # You may want to add methods to get the method signature.
