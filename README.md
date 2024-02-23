<p align="center">
  <a href="https://www.datafog.ai"><img src="public/colorlogo.png" alt="DataFog logo"></a>
</p>

<p align="center">
    <b>Open-source PII Detection for Retrieval Systems</b>. <br />
    Scan, redact, and manage PII in your documents before they get uploaded to a Retrieval Augmented Generation (RAG) system. 
</p>

<p align="center">
  <a href="https://pypi.org/project/datafog/"><img src="https://img.shields.io/pypi/v/datafog.svg?style=flat-square" alt="PyPi Version"></a>
  <a href="https://pypi.org/project/datafog/"><img src="https://img.shields.io/pypi/pyversions/datafog.svg?style=flat-square" alt="PyPI pyversions"></a>
  <a href="https://github.com/datafog/datafog-python"><img src="https://img.shields.io/github/stars/datafog/datafog-python.svg?style=flat-square&logo=github&label=Stars&logoColor=white" alt="GitHub stars"></a>
  <a href="https://pypistats.org/packages/datafog"><img src="https://img.shields.io/pypi/dm/datafog.svg?style=flat-square" alt="PyPi downloads"></a>
</p>

<p align="center">
  <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square" alt="Code style: black"></a>
</p>

<p align="center">
  <a href="https://codecov.io/gh/datafog/datafog-python"><img src="https://img.shields.io/codecov/c/github/datafog/datafog-python.svg?style=flat-square" alt="codecov"></a>
</p>

## Overview

DataFog works by scanning and redacting-out PII in files **before** are uploaded to a RAG system.

## How it works

<img src="https://www.datafog.ai/hero.png" alt="DataFog Overview">

## Installation

DataFog can be installed via pip:

```bash
pip install datafog # python client
```

## Usage

We're going to build up functionality starting with support for the Microsoft Presidio library. If you have any custom requests that would be of benefit to the community, please let us know!

```
  import requests
  from datafog import PresidioEngine as presidio

  # Example: Detecting PII in a String
  pii_detected = presidio.scan("My name is John Doe and my email is johndoe@genai.com")
  print("PII Detected:", pii_detected)

  # Example: Detecting PII in a File
  sample_filepath = "/Users/sidmohan/Desktop/v2.0.0/datafog-python/tests/files/input_files/sample.csv"
  with open(sample_filepath, "r") as f:
      original_value = f.read()
  pii_detected = presidio.scan(original_value)
  print("PII Detected in File:", pii_detected)

  # Example: Detecting PII in a URL
  sample_url = "https://gist.githubusercontent.com/sidmohan0/1aa3ec38b4e6594d3c34b113f2e0962d/raw/42e57146197be0f85a5901cd1dcdd9ad15b31bab/sotu_2023.txt"
  response = requests.get(sample_url)
  original_value = response.text
  pii_detected = presidio.scan(original_value)
  print("PII Detected in URL Content:", pii_detected)

```

Depending on your input, the output will be a list of detected PII entities:

```
PII Detected: [type: EMAIL_ADDRESS, start: 36, end: 53, score: 1.0, type: PERSON, start: 11, end: 19, score: 0.85, type: URL, start: 44, end: 53, score: 0.5]
```

## Contributing

This is an open-source project and we welcome contributions. If you have any questions, please feel free to reach out to us, join our Discord or email me directly at sid@datafog.ai.

### Dev Notes

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
