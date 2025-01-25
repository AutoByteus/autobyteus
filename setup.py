from setuptools import setup, find_packages
# Common dependencies
common_dependencies = [
    "beautifulsoup4>=4.12.2",
    "openai",
    "playsound==1.2.2",
    "requests",
    "tiktoken==0.7.0",
    "google-api-python-client",
    "google-generativeai",
    "redis",
    "weaviate-client",
    "sentence-transformers",
    "pymilvus==2.5.2",
    "Pillow",
    "toml",
    "python-dotenv",
    "mistralai",
    "boto3",
    "botocore",
    "anthropic==0.37.1",
    "Jinja2",
    "ollama==0.4.5",
    "mistral_common",
    "aiohttp",
    "autobyteus-llm-client==1.0.3",
    "brui-core==1.0.4",
]
setup(
    name="autobyteus",
    version="0.1.0",
    packages=find_packages(),
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
