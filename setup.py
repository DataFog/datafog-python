#  package using pip, navigate to the directory that contains the setup.py file and type pip install .

from setuptools import setup

# Read README for the long description
with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="datafog",
    version="2.3.1",
    author="DataFog",
    author_email="hi@datafog.ai",
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
        "Programming Language :: Python :: 3.10, 3.11",
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
    url="https://github.com/datafog/datafog-python",
    download_url="https://github.com/datafog/datafog-python/archive/refs/tags/2.3.1.tar.gz",
    packages=["datafog"],
    package_dir={"datafog": "datafog"},
    include_package_data=True,
    license="MIT",
)
