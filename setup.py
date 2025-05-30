from setuptools import find_packages, setup

# Read README for the long description
with open("README.md", "r") as f:
    long_description = f.read()

# Use a single source of truth for the version
version = "4.2.0"

project_urls = {
    "Homepage": "https://datafog.ai",
    "Documentation": "https://docs.datafog.ai",
    "Discord": "https://discord.gg/bzDth394R4",
    "Twitter": "https://twitter.com/datafoginc",
    "GitHub": "https://github.com/datafog/datafog-python",
}

# Core lightweight dependencies only
core_deps = [
    "pydantic>=2.0,<3.0",
    "pydantic-settings>=2.0.0",
    "typing-extensions>=4.0",
]

# Optional heavy dependencies
extras_require = {
    "nlp": [
        "spacy>=3.7.0,<4.0",
    ],
    "nlp-advanced": [
        "gliner>=0.2.5",
        "torch>=2.1.0,<2.7",
        "transformers>=4.20.0",
        "huggingface-hub>=0.16.0",
    ],
    "ocr": [
        "pytesseract>=0.3.0",
        "Pillow>=10.0.0",
        "sentencepiece>=0.2.0",
        "protobuf>=4.0.0",
    ],
    "distributed": [
        "pandas>=2.0.0",
        "numpy>=1.24.0",
    ],
    "web": [
        "fastapi>=0.100.0",
        "aiohttp>=3.8.0",
        "requests>=2.30.0",
    ],
    "cli": [
        "typer>=0.12.0",
        "pydantic-settings>=2.0.0",
    ],
    "crypto": [
        "cryptography>=40.0.0",
    ],
    "dev": [
        "pytest>=7.0.0",
        "pytest-asyncio>=0.21.0",
        "pytest-cov>=4.0.0",
        "sphinx>=7.0.0",
    ],
    # Convenience bundles
    "all": [
        "spacy>=3.7.0,<4.0",
        "gliner>=0.2.5",
        "torch>=2.1.0,<2.7",
        "transformers>=4.20.0",
        "huggingface-hub>=0.16.0",
        "pytesseract>=0.3.0",
        "Pillow>=10.0.0",
        "sentencepiece>=0.2.0",
        "protobuf>=4.0.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "fastapi>=0.100.0",
        "aiohttp>=3.8.0",
        "requests>=2.30.0",
        "typer>=0.12.0",
        "pydantic-settings>=2.0.0",
        "cryptography>=40.0.0",
    ],
}

setup(
    name="datafog",
    version=version,
    author="Sid Mohan",
    author_email="sid@datafog.ai",
    description="Lightning-fast PII detection and anonymization library with 190x performance advantage",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=core_deps,
    extras_require=extras_require,
    python_requires=">=3.10,<3.13",
    entry_points={
        "console_scripts": [
            "datafog=datafog.client:app [cli]",  # Requires cli extra
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing",
        "Topic :: Security",
    ],
    project_urls=project_urls,
    keywords="pii detection anonymization privacy regex performance",
)
