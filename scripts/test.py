class MyMeta(type):
    def __new__(cls, name, bases, attrs):
        # Customizing class creation in __new__
        attrs['attribute'] = 'Added by __new__'
        return super().__new__(cls, name, bases, attrs)

    def __call__(cls, *args, **kwargs):
        # Customizing instance creation in __call__
        instance = super().__call__(*args, **kwargs)
        print(f'Creating instance of {cls.__name__}')
        return instance

class MyClass(metaclass=MyMeta):
    def __init__(self, value):
        self.value = value

obj = MyClass(42)
print(obj.attribute)  # Output: Added by __new__
