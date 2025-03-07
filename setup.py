from setuptools import setup, find_packages

# Common dependencies
common_dependencies = [
    "beautifulsoup4>=4.12.2",
    "openai",
    "requests",
    "tiktoken==0.7.0",
    "google-api-python-client",
    "google-generativeai",
    "mistralai",
    "boto3",
    "botocore",
    "anthropic==0.37.1",
    "Jinja2",
    "ollama==0.4.5",
    "mistral_common",
    "aiohttp",
    "autobyteus-llm-client==1.0.8",
    "brui-core==1.0.4",
]

setup(
    name="autobyteus",
    version="1.0.0",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    install_requires=[
        *common_dependencies,
    ],
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
            "load_dotenv",
        ],
    },
    python_requires=">=3.8",
    author="Ryan Zheng",
    author_email="ryan.zheng.work@gmail.com",
    description="Multi-Agent framework",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/AutoByteus/autobyteus",
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
    },
)
