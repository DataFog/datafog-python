<p align="center">
  <a href="https://www.datafog.ai"><img src="public/colorlogo.png" alt="DataFog logo"></a>
</p>

<p align="center">
    <b>Open-source DevSecOps for Generative AI Systems</b>. <br />
</p>

<p align="center">
  <a href="https://pypi.org/project/datafog/"><img src="https://img.shields.io/pypi/v/datafog.svg?style=flat-square" alt="PyPi Version"></a>
  <a href="https://pypi.org/project/datafog/"><img src="https://img.shields.io/pypi/pyversions/datafog.svg?style=flat-square" alt="PyPI pyversions"></a>
  <a href="https://github.com/datafog/datafog-python"><img src="https://img.shields.io/github/stars/datafog/datafog-python.svg?style=flat-square&logo=github&label=Stars&logoColor=white" alt="GitHub stars"></a>
  <a href="https://pypistats.org/packages/datafog"><img src="https://img.shields.io/pypi/dm/datafog.svg?style=flat-square" alt="PyPi downloads"></a>
  <a href="https://discord.gg/bzDth394R4"><img src="https://img.shields.io/discord/1173803135341449227?style=flat" alt="Discord"></a>
  <a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square" alt="Code style: black"></a>
  <a href="https://codecov.io/gh/datafog/datafog-python"><img src="https://img.shields.io/codecov/c/github/datafog/datafog-python.svg?style=flat-square" alt="codecov"></a>
  <a href="https://github.com/datafog/datafog-python/issues"><img src="https://img.shields.io/github/issues/datafog/datafog-python.svg?style=flat-square" alt="GitHub Issues"></a>
</p>

## Overview

### What is DataFog?

DataFog is an open-source DevSecOps platform that lets you scan and redact Personally Identifiable Information (PII) out of your Generative AI applications.

### Core Problem

![image](https://github.com/DataFog/datafog-python/assets/61345237/57fba4e5-21cc-458f-ac6a-6fbbb70a8de1)

### How it works

![image](https://github.com/DataFog/datafog-python/assets/61345237/91f4634a-8a9f-4621-81bc-09930feda78a)

## Installation

DataFog can be installed via pip:

```bash
pip install datafog
```


## Getting Started

The DataFog library provides functionality for text and image processing, including PII (Personally Identifiable Information) annotation and OCR (Optical Character Recognition) capabilities.

### Installation

To install the DataFog library, use the following command:

```
pip install datafog
```

### Usage

The [Getting Started notebook](/datafog-python/examples/getting_started.ipynb)  features a standalone Colab notebook that lets you get up and running in no time. 


#### Text PII Annotation

To annotate PII in a given text, lets start with a set of clinical notes:

```
!git clone https://gist.github.com/b43b72693226422bac5f083c941ecfdb.git
```

```python
from datafog import TextPIIAnnotator

text = "John Doe lives at 1234 Elm St, Springfield."
text_annotator = TextPIIAnnotator()
annotated_text = text_annotator.run(text)
print(annotated_text)
```

This will output the annotated text with PII labeled, such as `{"LOC": ["Springfield"]}`.

#### Image Text Extraction and Annotation

To extract text from an image and perform PII annotation, you can use the `DataFog` class:

```python
from datafog import DataFog

image_url = "https://pbs.twimg.com/media/GM3-wpeWkAAP-cX.jpg"
datafog = DataFog()
annotated_text = await datafog.run_ocr_pipeline([image_url])
print(annotated_text)
```

This will download the image, extract the text using OCR, and annotate any PII found in the extracted text.

#### Text Processing

To process and annotate text using the DataFog pipeline, you can use the `DataFog` class:

```python
from datafog import DataFog

text = ["Tokyo is the capital of Japan"]
datafog = DataFog()
annotated_text = await datafog.run_text_pipeline(text)
print(annotated_text)
```

This will process the given text and annotate entities such as person names and locations.

For more detailed usage and examples, please refer to the API documentation.

Note: The DataFog library uses asynchronous programming, so make sure to use the `async`/`await` syntax when calling the appropriate methods.



## Contributing

DataFog is a community-driven **open-source** platform and we've been fortunate to have a small and growing contributor base. We'd love to hear ideas, feedback, suggestions for improvement - anything on your mind about what you think can be done to make DataFog better! Join our [Discord](https://discord.gg/bzDth394R4) and join our growing community.

### Dev Notes

- Justfile commands:
  - `just format` to apply formatting.
  - `just lint` to check formatting and style.

### Testing

To run the datafog unit tests, check out this repository and do

```

tox

```

## License

This software is published under the [MIT
license](https://en.wikipedia.org/wiki/MIT_License).
