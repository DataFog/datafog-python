from setuptools import find_packages, setup

# Read README for the long description
with open("README.md", "r") as f:
    long_description = f.read()

# Use a single source of truth for the version from __about__.py
exec(open("datafog/__about__.py").read())
version = __version__  # noqa: F821

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
nlp_deps = [
    "click>=8.0,<9.0",
    "spacy>=3.7.0,<4.0",
]

nlp_advanced_deps = [
    "gliner>=0.2.5",
    "torch>=2.1.0,<2.7",
    "transformers>=4.20.0",
    "huggingface-hub>=0.16.0",
]

ocr_deps = [
    "numpy>=1.24.0",
    "pytesseract>=0.3.0",
    "Pillow>=12.2.0",
    "sentencepiece>=0.2.0",
    "protobuf>=4.0.0",
]

distributed_deps = [
    "pandas>=2.0.0",
    "numpy>=1.24.0",
    "pyspark>=3.5.0",
]

web_deps = [
    "fastapi>=0.100.0",
    "aiohttp>=3.13.4",
    "certifi>=2025.4.26",
    "requests>=2.33.0",
]

cli_deps = [
    "click>=8.0,<9.0",
    "typer>=0.12.0",
    "pydantic-settings>=2.0.0",
]

crypto_deps = [
    "cryptography>=46.0.7",
]

test_deps = [
    "pytest>=9.0.3",
    "pytest-asyncio>=1.3.0",
    "pytest-cov>=7.1.0",
]

docs_deps = [
    "sphinx>=7.2.6",
]

benchmark_deps = [
    "pytest-benchmark>=4.0.0",
]

extras_require = {
    "nlp": nlp_deps,
    "nlp-advanced": nlp_advanced_deps,
    "ocr": ocr_deps,
    "distributed": distributed_deps,
    "web": web_deps,
    "cli": cli_deps,
    "crypto": crypto_deps,
    "test": test_deps,
    "docs": docs_deps,
    "benchmark": benchmark_deps,
    "dev": test_deps + docs_deps,
    # Convenience bundles
    "all": (
        nlp_deps
        + nlp_advanced_deps
        + ocr_deps
        + distributed_deps
        + web_deps
        + cli_deps
        + crypto_deps
    ),
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
    python_requires=">=3.10,<3.14",
    entry_points={
        "console_scripts": [
            "datafog=datafog.client:app [cli]",  # Requires cli extra
            "datafog-hook=datafog.integrations.claude_code:main",  # Core only
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
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing",
        "Topic :: Security",
    ],
    project_urls=project_urls,
    keywords="pii detection anonymization privacy regex performance",
)
