# Autobyteus

Autobyteus is an open-source coding assistance tool designed to enhance the software development workflow by making it context-aware. Each step in the workflow is interactive through a user-friendly interface, incorporating the entire software development lifecycle into each stage.

## Features

- **Context-Aware Workflows**: Each step in the development process interacts with large language models to provide relevant assistance.
- **Lifecycle Integration**: Supports the entire software development lifecycle, starting from requirement engineering.
- **Memory Management**: Custom memory management system supporting different memory providers and embeddings.

## Knowledge Base

A significant part of Autobytus is our custom-designed knowledge base focused on software and application development. The knowledge base is structured to support the entire development process, with particular emphasis on requirement engineering, which is crucial for successful project outcomes.

## Getting Started

### Installation

1. **For users:**
   To install Autobyteus, run:
   ```
   pip install .
   ```

2. **For developers:**
   To install Autobyteus with development dependencies, run:
   ```
   pip install -r requirements-dev.txt
   ```

3. **Platform-specific dependencies:**
   To install platform-specific dependencies, run:
   ```
   python setup.py install_platform_deps
   ```

### Building the Library

To build Autobyteus as a distributable package, follow these steps:

1. Ensure you have the latest version of `setuptools` and `wheel` installed:
   ```
   pip install --upgrade setuptools wheel
   ```

2. Build the distribution packages:
   ```
   python setup.py sdist bdist_wheel
   ```

   This will create a `dist` directory containing the built distributions.

3. (Optional) To create a source distribution only:
   ```
   python setup.py sdist
   ```

4. (Optional) To create a wheel distribution only:
   ```
   python setup.py bdist_wheel
   ```

The built packages will be in the `dist` directory and can be installed using pip or distributed as needed.

### Usage

(Add basic commands and examples to get users started)

### Contributing

(Add guidelines for contributing to the project)

## License

This project is licensed under the MIT License.
