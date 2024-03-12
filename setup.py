#  package using pip, navigate to the directory that contains the setup.py file and type pip install .

from setuptools import setup

# Read README for the long description
with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="datafog",
    version="2.3.0b3",
    author="Sid Mohan",
    author_email="sid@datafog.ai",
    description="Scan, redact, and manage PII in your documents before they get uploaded to a Retrieval Augmented Generation (RAG) system.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=[
        "pandas==2.2.1",
        "presidio_analyzer==2.2.353",
        "pytest==8.0.2",
        "Requests==2.31.0",
        "spacy==3.4.4",
        "en_spacy_pii_fast",
    ],
    python_requires=">=3.10",
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
