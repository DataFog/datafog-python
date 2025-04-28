import os

import os

from setuptools import find_packages, setup

# Read README for the long description
with open("README.md", "r") as f:
    long_description = f.read()

# Get version from __about__.py
about = {}
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, "datafog", "__about__.py"), "r") as f:
    exec(f.read(), about)

project_urls = {
    "Homepage": "https://datafog.ai",
    "Documentation": "https://docs.datafog.ai",
    "Discord": "https://discord.gg/bzDth394R4",
    "Twitter": "https://twitter.com/datafoginc",
    "GitHub": "https://github.com/datafog/datafog-python",
}

setup(
    name="datafog",
    version=about["__version__"],
    author="Sid Mohan",
    author_email="sid@datafog.ai",
    description="Scan, redact, and manage PII in your documents before they get uploaded to a Retrieval Augmented Generation (RAG) system.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=[
        # Core dependencies
        "pandas",
        "requests==2.32.3",
        "pydantic",
        "Pillow",  # Image processing
        "protobuf",
        "aiohttp",
        "numpy",
        "fastapi",
        "asyncio",
        "setuptools",
        "pydantic-settings==2.3.4",
        "typer==0.12.3",
        "sphinx",  # Documentation
        "cryptography",
        # Spacy dependencies
        "spacy==3.7.5",
        # Tesseract dependencies
        "pytesseract",
        # Donut dependencies (requires transformers, torch)
        "sentencepiece",
        "torch",  # Add torch for Donut model support
        # Development/Testing dependencies (moved to extras_require ideally)
        "pytest-asyncio",
    ],
    python_requires=">=3.10,<3.13",
    entry_points={
        "console_scripts": [
            "datafog=datafog.client:app",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Framework :: tox",
        "Framework :: Pytest",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Information Technology",
        "Intended Audience :: System Administrators",
    ],
    keywords="pii, redaction, nlp, rag, retrieval augmented generation",
    maintainer="DataFog",
    maintainer_email="hi@datafog.ai",
    url="https://datafog.ai",
    project_urls=project_urls,
    license="MIT",
    extras_require={
        "dev": [
            "just",
            "isort",
            "black",
            "blacken-docs",
            "flake8",
            "tox",
            "pytest",
            "pytest-codeblocks",
            "pytest-cov",
            "build",
            "twine",
            "ipykernel",
        ],
        "spark": [
            "pyspark>=3.0.0",
        ],
        "ocr": [
            "pytesseract>=0.3.10",
            "Pillow>=9.0.0",
        ],
        "donut": [
            "torch>=1.8.0",
            "transformers[torch]>=4.10.0",
            "sentencepiece",
            "protobuf",
        ],
        "all": [
            "pyspark>=3.0.0",
            "pytesseract>=0.3.10",
            "Pillow>=9.0.0",
            "torch>=1.8.0",
            "transformers[torch]>=4.10.0",
            "sentencepiece",
            "protobuf",
        ],
    },
)
