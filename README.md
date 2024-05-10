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

## Installation

DataFog can be installed via pip:

```bash
pip install datafog
```

## Examples - Updated for v3.1

### Base case: PII annotation of text-files

```
from datafog import OCRPIIAnnotator, TextPIIAnnotator
import json
import requests

response = requests.get('https://gist.githubusercontent.com/sidmohan0/1aa3ec38b4e6594d3c34b113f2e0962d/raw/42e57146197be0f85a5901cd1dcdd9ad15b31bab/sotu_2023.txt')
response.raise_for_status()  # Ensure the request was successful
text = response.text
# print(text)
text_annotator = TextPIIAnnotator()
annotated_text = text_annotator.run(text, output_path=f"sotu_2023_output.json")
print("Annotated Text:", annotated_text)
```

### OCR Reference Set (Images)

```
image_set = {
    "medical_invoice": "https://s3.amazonaws.com/thumbnails.venngage.com/template/dc377004-1c2d-49f2-8ddf-d63f11c8d9c2.png",
    "sales_receipt": "https://templates.invoicehome.com/sales-receipt-template-us-classic-white-750px.png",
    "press_release": "https://newsroom.cisco.com/c/dam/r/newsroom/en/us/assets/a/y2023/m09/cisco_splunk_1200x675_v3.png",
    "insurance_claim_scanned_form": "https://www.pdffiller.com/preview/101/35/101035394.png",
    "scanned_internal_record": "https://www.pdffiller.com/preview/435/972/435972694.png",
    "executive_email": "https://pbs.twimg.com/media/GM3-wpeWkAAP-cX.jpg"
}

```

### OCR text extraction from images + PII annotation

with this, you can then run the following steps:

```
from datafog import OCRPIIAnnotator, TextPIIAnnotator
import json

image_url = image_set["executive_email"]

annotator = OCRPIIAnnotator()
annotated_text = annotator.run(image_url, output_path=f"executive_email_output.json")
print("Annotated Text:", annotated_text)

```

and the output should look like this:

```
Annotated Text: {'DATE_TIME': ['Wednesday', 'June 12, 2019'], 'LOC': [], 'NRP': [], 'ORG': [], 'PER': ['Kevin Scott Sent', 'Satya Nadella', 'Bill Gates Subject', 'Thoughts']}

```

### With PySpark

Note: as of 3.1.0, you'll need to start the Spark session by instancing the DataFog class as shown below

```
from datafog import DataFog
from datafog.pii_annotation import ImageProcessor
datafog = DataFog()

# let's process the images that we shared above
processed_images = [(name, ImageProcessor().download_image(url=image_url)) for name, image_url in image_set.items()]

from datafog.pii_annotation import SparkProcessor
parsed_images = [(name, ImageProcessor().parse_image(img)) for name, img in processed_images]

df = SparkProcessor().spark.createDataFrame(parsed_images, ["image_name", "parsed_data"])

# Display DataFrame
df.show(truncate=False)

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
