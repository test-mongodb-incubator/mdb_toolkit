from setuptools import setup, find_packages

setup(
    name="mdb-toolkit",  # Your package name (must be unique on PyPI)
    version="0.5.0",  # Initial release version
    description="Custom MongoDB client with vector search capabilities, embeddings management, and more.",
    long_description=open("README.md", "r", encoding="utf-8").read(),
    long_description_content_type="text/markdown",  # Use Markdown for PyPI description
    author="Fabian Valle",  # Replace with your name
    author_email="oblivio.company@gmail.com",  # Replace with your email
    license="MIT",  # Your project license
    url="https://github.com/ranfysvalle02/mdb_toolkit",  # GitHub repository URL
    packages=['mdb_toolkit'],  # Automatically find your packages
    install_requires=[
        "pymongo",  # MongoDB driver
    ],
    python_requires=">=3.7",  # Specify the Python versions your package supports
    classifiers=[
        "Development Status :: 3 - Alpha",  # Change to Beta or Production/Stable as appropriate
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
    ],
    keywords="mongodb vector-search embeddings pymongo openai",  # Keywords for PyPI search
    project_urls={
        "Documentation": "https://github.com/ranfysvalle02/mdb_toolkit#readme",  # Link to your README
        "Source": "https://github.com/ranfysvalle02/mdb_toolkit",  # Link to source code
        "Bug Tracker": "https://github.com/ranfysvalle02/mdb_toolkit/issues"  # Issue tracker
    },
)
