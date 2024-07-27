import sys
from setuptools import setup, find_packages, Command

# Common dependencies
common_dependencies = [
    "pymongo",
    "SQLAlchemy",
    "sqlalchemy-utils",
    "alembic",
    "psycopg2-binary",
    "repository-sqlalchemy",
    "repository-mongodb",
    "pytest-playwright",
    "beautifulsoup4>=4.12.2",
    "colorama==0.4.6",
    "distro==1.8.0",
    "openai",
    "playsound==1.2.2",
    "pyyaml==6.0",
    "readability-lxml==0.8.1",
    "requests",
    "tiktoken==0.3.3",
    "gTTS==2.3.1",
    "docker",
    "google-api-python-client",
    "redis",
    "weaviate-client",
    "sentence-transformers",
    "orjson",
    "Pillow",
    "jsonschema",
    "tweepy",
    "click",
    "grpcio",
    "grpcio-tools", 
    "toml",
    "python-dotenv",
    "uvicorn",
    "fastapi",
    "strawberry-graphql",
]

# Platform-specific dependencies
if sys.platform.startswith('linux'):
    platform_dependencies = [
        "python-xlib",
        "opencv-python",
        "pytesseract",
        "pyautogui",
    ]
elif sys.platform == 'darwin':
    platform_dependencies = [
        "pyobjc",
    ]
elif sys.platform == 'win32':
    platform_dependencies = [
        "pywin32",
        "pyautogui",
    ]
else:
    platform_dependencies = []

class InstallPlatformDependencies(Command):
    description = 'Install platform-specific dependencies'
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import subprocess

        if sys.platform.startswith('linux'):
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements-linux.txt'])
        elif sys.platform == 'darwin':
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements-mac.txt'])
        elif sys.platform == 'win32':
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements-windows.txt'])

setup(
    name="autobyteus",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=common_dependencies + platform_dependencies,
    extras_require={
        "dev": [
            "coverage",
            "flake8",
            "numpy",
            "pre-commit",
            "black",
            "isort",
            "gitpython==3.1.31",
            "auto-gpt-plugin-template",
            "mkdocs",
            "pytest",
            "asynctest",
            "pytest-asyncio",
            "pytest-benchmark",
            "pytest-cov",
            "pytest-integration",
            "pytest-mock",
            "vcrpy",
            "pytest-vcr",
            "llm_chatui_provider @ git+https://github.com/AFE-AI/llm_chatui_provider.git@main",
        ],
    },
    python_requires=">=3.8",
    author="Your Name",
    author_email="your.email@example.com",
    description="A library for automating software development tasks",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/autobyteus",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    package_data={
        "autobyteus": ["py.typed"],
        "autobyteus.tools.social_media_poster.weibo": 
            ["images/open_file_button_template.png",
             "images/downloads_folder_button.png"],
    },
    cmdclass={
        'install_platform_deps': InstallPlatformDependencies,
    },
)