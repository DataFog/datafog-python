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

How do you keep:

- Customer PII
- Employee PII
- Sensitive company information pertaining to org changes or restructurings
- Pending M&A activity
- Conversations with external counsel on material corporate matters (i.e. product recall, etc)
- and more

from entering a Generative AI environment in the first place? What you need is a tool to scan and redact your RAG-bound documents based on your organization or team needs.

**That's where DataFog comes in.**

### How it works

![image](https://github.com/DataFog/datafog-python/assets/61345237/91f4634a-8a9f-4621-81bc-09930feda78a)

### There's lots of PII tools out there; why DataFog?

If you look at the landscape of PII detection tools, their very existence was in many cases driven by regulatory requirements (i.e. 'comply with CCPA/GDPR/HIPAA').
In this scenario, there's a very defined problem, a specific set of immutable entities to look for, and a relatively static universe of document schema to work with. What that means as an end-result is that the products
are purpose-built for the problem that they are solving.

However, Generative AI changes how we think about privacy. There's now a changing set of privacy requirements (new M&A deals, internal discussions means new terms to scan/redact) as well as different and varying document sources to contend with. PII detection is no longer just about compliance, it's an active - and for some, new - internal security threat for CISOs and Eng Leaders to contend with. We want DataFog to be built and driven to meet the needs of the open-source community as they tackle this challenge.

### Roadmap

DataFog is an active project with regular weekly releases to production (typically on/around Monday evenings US PT). Here's a snapshot of our coming roadmap; if you have questions or would like to weigh in, join our discord and let us know what we can do to make the product better!

![image](https://github.com/DataFog/datafog-python/assets/61345237/62964d22-a221-4f1d-a0e6-0cc99de2ba92)

## Installation

DataFog can be installed via pip:

```bash
pip install datafog
```

and in your python environment:

```
from datafog import PresidioEngine as presidio
datafog = datafog.DataFog()

```

## Examples

Here are some examples of datafog being used to redact information in business contexts. Please see '/examples' for our [Getting Started](examples/getting-started.ipynb) notebook. We'll be regularly updating content and providing comprehensive guides to using DataFog in production contexts. If you have any ideas for a tutorial or guide that you would like to see, please let us know!

### Scanning a single string

```
  ceo_email_chunk = "I'm announcing on Friday that Jeff is going to be CTO."

  scan_results1 = presidio.scan(ceo_email_chunk)
  print("PII Detected - base case:", scan_results1)
  # PII Detected - base case: [type: PERSON, start: 30, end: 34, score: 0.85]


  scan_results2 = presidio.scan(ceo_email_chunk, deny_list=['CTO'])
  print("PII Detected with deny list:", scan_results2)
  # PII Detected with deny list: [type: CUSTOM_PII, start: 50, end: 53, score: 1.0, type: PERSON, start: 30, end: 34, score: 0.85]

```

### Scanning a list of PDFs

```
file_dir = ["/Users/sidmohan/Desktop/datafog-v2.4.0/datafog-python/tests/files/input_files/agi-builder-meetup.pdf",
           "/Users/sidmohan/Desktop/datafog-v2.4.0/datafog-python/tests/files/input_files/pypdf-readthedocs-io-en-stable.pdf"]
datafog = datafog.DataFog()
result = datafog.upload_files(uploaded_files=file_dir)
print(result)
```

The output here will be a dictionary where the keys are the file names and the values are the scan results for that file.
for ex:
`{'agi-builder-meetup.pdf': "2/26/24, 2:16 PM\nAGI Builders Meetup SF · Luma\nContact the HostReport Event29\nEvent FullIf youʼd like"}`

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
