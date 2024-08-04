from setuptools import find_packages, setup

# Read README for the long description
with open("README.md", "r") as f:
    long_description = f.read()

# Use a single source of truth for the version
__version__ = "3.3.1b3"

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
        "Requests",
        "spacy==3.7.5",
        "pydantic",
        "Pillow",
        "sentencepiece",
        "protobuf",
        "pytesseract",
        "aiohttp",
        "pytest-asyncio",
        "numpy",
        "fastapi",
        "asyncio",
        "setuptools",
    ],
    python_requires=">=3.10,<3.13",
    classifiers=[
        "Programming Language :: Python :: 3.12",
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
        ],
    },
)
