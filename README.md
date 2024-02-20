<p align="center">
  <a href="https://www.datafog.ai"><img src="public/colorlogo.png" alt="DataFog logo"></a>
</p>

<p align="center">
    <b>Open-source PII Detection for Retrieval Systems</b>. <br />
    Scan, redact, and manage PII in your documents before they get uploaded to a Retrieval Augmented Generation (RAG) system. 
</p>

[![PyPi Version](https://img.shields.io/pypi/v/datafog.svg?style=flat-square)](https://pypi.org/project/datafog/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/datafog.svg?style=flat-square)](https://pypi.org/project/datafog/)
[![GitHub stars](https://img.shields.io/github/stars/datafog/datafog-python.svg?style=flat-square&logo=github&label=Stars&logoColor=white)](https://github.com/datafog/datafog-python)
[![PyPi downloads](https://img.shields.io/pypi/dm/datafog.svg?style=flat-square)](https://pypistats.org/packages/datafog)

<!-- [![gh-actions](https://img.shields.io/github/workflow/status/datafog/datafog-python/ci?style=flat-square)](https://github.com/datafog/datafog-python/actions?query=workflow%3Aci) -->

[![codecov](https://img.shields.io/codecov/c/github/datafog/datafog-python.svg?style=flat-square)](https://codecov.io/gh/datafog/datafog-python)

<!-- [![LGTM](https://img.shields.io/lgtm/grade/python/github/datafog/datafog-python.svg?style=flat-square)](https://lgtm.com/projects/g/datafog/datafog-python) -->

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square)](https://github.com/psf/black)

## Overview

DataFog works by scanning and redacting-out PII in files **before** are uploaded to a RAG system.

## How it works

<img src="https://www.datafog.ai/hero.png" alt="DataFog Overview">

## Installation

DataFog can be installed via pip:

```bash
pip install datafog # python client
```

## Dev Notes

- Clone repo
- Run 'poetry install' to install dependencies (recommend entering poetry shell for preserving dependencies)
- Justfile commands:
  - `just format` to apply formatting.
  - `just lint` to check formatting and style.
  - `just tag` to tag your project on git
  - `just upload` to publish to PyPi.

### Testing

To run the datafog unit tests, check out this repository and do

```
tox
```

### License

This software is published under the [MIT
license](https://en.wikipedia.org/wiki/MIT_License).
