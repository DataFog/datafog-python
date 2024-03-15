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

### What problem are we solving?

**Context**

The primary use case today is Retrieval Augmented Generation (RAG) systems. As a refresher, RAG systems operate by retrieving information from a custom knowledge base—constructed by you or your team—and leverage this information, either by directly citing the files in a response or inferred through the model's responses. This knowledge base is assembled through a deliberate process, which involves uploading files into a workflow. These files are then segmented into logical information blocks and tagged according to their contextual significance. There are a thousand ways to add nuance to this characterization, but this suffices for the vast majority of cases!

**Problem**

How do you keep:

- Customer PII
- Employee PII
- Sensitive company information pertaining to org changes or restructurings
- Pending M&A activity
- Conversations with external counsel on material corporate matters (i.e. product recall, etc)
- and more

from entering a Generative AI environment in the first place? What you need is a tool to scan and redact your RAG-bound documents based on your organization or team needs.

That's where DataFog comes in. Our solution to this problem is through two major approaches:

**PII Observability** Take in your batch/streaming data and return a scan indicating character-level detection of entities
**Privacy Filter** DataFog can slot in as a pre-processor that redacts PII from your files before they get uploaded to a RAG database

With this SDK, you can import it into a Python environment (like a Google Colab notebook, check out our [Getting Started](examples/getting-started.ipynb)) and within a few lines of code you're up and running.

### How it works

<img src="https://www.datafog.ai/hero.png" alt="DataFog Overview" style="width:50%;">

### There's lots of PII tools out there; why DataFog?

If you look at the landscape of PII detection tools, their very existence was in many cases driven by regulatory requirements (i.e. 'comply with CCPA/GDPR/HIPAA').
In this scenario, there's a very defined problem, a specific set of immutable entities to look for, and a relatively static universe of document schema to work with. What that means as an end-result is that the products
are purpose-built for the problem that they are solving.

However, Generative AI changes how we think about privacy. There's now a changing set of privacy requirements (new M&A deals, internal discussions means new terms to scan/redact) as well as different and varying document sources to contend with. PII detection is no longer just about compliance, it's an active - and for some, new - internal security threat for CISOs and Eng Leaders to contend with. We want DataFog to be built and driven to meet the needs of the open-source community as they tackle this challenge.

## Installation

DataFog can be installed via pip:

```bash
pip install datafog
```

and in your python environment:

```
from datafog import PresidioEngine as presidio
```

## Examples

Here are some examples of datafog being used to redact information in business contexts. Please see '/examples' for our [Getting Started](examples/getting-started.ipynb) notebook. We'll be regularly updating content and providing comprehensive guides to using DataFog in production contexts. If you have any ideas for a tutorial or guide that you would like to see, please let us know!

```
  ceo_email_chunk = "I'm announcing on Friday that Jeff is going to be CTO."

  scan_results1 = presidio.scan(ceo_email_chunk)
  print("PII Detected - base case:", scan_results1)
  # PII Detected - base case: [type: PERSON, start: 30, end: 34, score: 0.85]


  scan_results2 = presidio.scan(ceo_email_chunk, deny_list=['CTO'])
  print("PII Detected with deny list:", scan_results2)
  # PII Detected with deny list: [type: CUSTOM_PII, start: 50, end: 53, score: 1.0, type: PERSON, start: 30, end: 34, score: 0.85]

```

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
