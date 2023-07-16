import os


class FileReader:
    @staticmethod
    def read_file(file_path):
        if not os.path.isfile(file_path) or not file_path.endswith('.py'):
            return None
        with open(file_path, 'r') as file:
            return file.read()
