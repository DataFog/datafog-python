from setuptools import find_packages, setup

# Read README for the long description
with open("README.md", "r") as f:
    long_description = f.read()

# Use a single source of truth for the version
__version__ = "3.2.2"

project_urls = {
    "Homepage": "https://datafog.ai",
    "Documentation": "https://docs.datafog.ai",
    "Discord": "https://discord.gg/bzDth394R4",
    "Twitter": "https://twitter.com/datafoginc",
    "GitHub": "https://github.com/datafog/datafog-python",
}

setup(
    name="datafog",
    version=__version__,
    author="Sid Mohan",
    author_email="sid@datafog.ai",
    description="Scan, redact, and manage PII in your documents before they get uploaded to a Retrieval Augmented Generation (RAG) system.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=[
        "pandas",
        "Requests==2.31.0",
        "spacy==3.4.4",
        "en_spacy_pii_fast @ https://huggingface.co/beki/en_spacy_pii_fast/resolve/main/en_spacy_pii_fast-any-py3-none-any.whl",
        "pydantic==1.10.15",
        "Pillow",
        "sentencepiece",
        "protobuf",
        "pytesseract",
        "aiohttp",
        "pytest-asyncio",
        "numpy==1.24.1",
        "fastapi",
        "asyncio",
        "setuptools==70.0.0",
    ],
    python_requires=">=3.10",
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
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
        ],
    },
)
