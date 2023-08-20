from abc import ABCMeta


class SingletonMeta(type):
    """
    SingletonMeta is a metaclass that implements the Singleton design pattern.
    It ensures that a class using this metaclass can have only one instance.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
    

class ABCSingletonMeta(SingletonMeta, ABCMeta):
    pass