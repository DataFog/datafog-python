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

The [Getting Started notebook](/datafog-python/examples/getting_started.ipynb) features a standalone Colab notebook.

#### Text PII Annotation

To annotate PII in a given text, lets start with a set of clinical notes:

```
!git clone https://gist.github.com/b43b72693226422bac5f083c941ecfdb.git
# Define the directory path
folder_path = 'clinical_notes/'

# List all files in the directory
file_list = os.listdir(folder_path)
text_files = sorted([file for file in file_list if file.endswith('.txt')])

with open(os.path.join(folder_path, text_files[0]), 'r') as file:
    clinical_note = file.read()

display(Markdown(clinical_note))
```

which looks like this:

```

**Date:** April 10, 2024

**Patient:** Emily Johnson, 35 years old

**MRN:** 00987654

**Chief Complaint:** "I've been experiencing severe back pain and numbness in my legs."

**History of Present Illness:** The patient is a 35-year-old who presents with a 2-month history of worsening back pain, numbness in both legs, and occasional tingling sensations. The patient reports working as a freelance writer and has been experiencing increased stress due to tight deadlines and financial struggles.

**Past Medical History:** Hypothyroidism

**Social History:**
The patient shares a small apartment with two roommates and relies on public transportation. They mention feeling overwhelmed with work and personal responsibilities, often sacrificing sleep to meet deadlines. The patient expresses concern over the high cost of healthcare and the need for affordable medication options.

**Review of Systems:** Denies fever, chest pain, or shortness of breath. Reports occasional headaches.

**Physical Examination:**
- General: Appears tired but is alert and oriented.
- Vitals: BP 128/80, HR 72, Temp 98.6°F, Resp 14/min

**Assessment/Plan:**
- Continue to monitor blood pressure and thyroid function.
- Discuss affordable medication options with a pharmacist.
- Refer to a social worker to address housing concerns and access to healthcare services.
- Encourage the patient to engage with community support groups for social support.
- Schedule a follow-up appointment in 4 weeks or sooner if symptoms worsen.

**Comments:** The patient's health concerns are compounded by socioeconomic factors, including employment status, housing stability, and access to healthcare. Addressing these social determinants of health is crucial for improving the patient's overall well-being.

```

we can then set up our pipeline to accept these files

```
async def run_text_pipeline_demo():
  results = await datafog.run_text_pipeline(texts)
  print("Text Pipeline Results:", results)
  return results


texts = [clinical_note]
loop = asyncio.get_event_loop()
results = loop.run_until_complete(run_text_pipeline_demo())
```

Note: The DataFog library uses asynchronous programming, so make sure to use the `async`/`await` syntax when calling the appropriate methods.

#### OCR PII Annotation

Let's use a image (which could easily be a converted or scanned PDF)

![Executive Email](https://pbs.twimg.com/media/GM3-wpeWkAAP-cX.jpg)

```
datafog = DataFog(operations='extract_text')
url_list = ['https://pbs.twimg.com/media/GM3-wpeWkAAP-cX.jpg']

async def run_ocr_pipeline_demo():
  results = await datafog.run_ocr_pipeline(url_list)
  print("OCR Pipeline Results:", results)

loop = asyncio.get_event_loop()
loop.run_until_complete(run_ocr_pipeline_demo())

```

You'll notice that we use async functions liberally throughout the SDK - given the nature of the functions we're providing and the extension of DataFog into API/other formats, this allows the functions to be more easily adapted for those uses.

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
