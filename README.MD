<p align="center">
  <a href="https://www.datafog.ai"><img src="public/colorlogo.png" alt="DataFog logo"></a>
</p>

<p align="center">
    <b>Open-source PII Detection for Retrieval Systems</b>. <br />
    Scan, redact, and manage PII in your documents before they get uploaded to a Retrieval Augmented Generation (RAG) system. 
</p>

<p align="center">

  <a href="https://github.com/DataFog/datafog-python/blob/master/LICENSE" target="_blank">
      <img src="https://img.shields.io/static/v1?label=license&message=MIT&color=white" alt="License">
  </a>

  <a href="https://docs.datafog.ai/" target="_blank">
      Docs
  </a>

  <a href="https://www.datafog.ai/" target="_blank">
      Homepage
  </a>

</p>

## Overview

DataFog works by scanning and redacting-out PII in files **before** are uploaded to a RAG system. 

### How it works

<img src="https://www.datafog.ai/hero.png" alt="DataFog Overview">

## Installation

DataFog can be installed via pip:

```bash
pip install datafog # python client
```

## Getting Started

Once you've installed DataFog, you can import it into your Python scripts as follows:

```python
from datafog import DataFog
```

Now, you're ready to use DataFog to handle your PII anonymization needs. Here are some basic examples:

**Scan a dataset for PII:**

```python
datafog = DataFog()

# Scan a csv file for PII
contains_pii, pii_fields = datafog.scan("path_to_your_file.csv")

# Print the result
print(f"Contains PII: {contains_pii}")
print(f"PII Fields: {pii_fields}")
```

**Swap PII with synthetic data:**

```python
# Define the output path
output_path = "path_to_output_directory/"

# Swap PII in a csv file with synthetic data
datafog.swap("path_to_your_file.csv", output_path)
```

## Get involved

As an community open-source platform, We welcome PR contributors and ideas for how to improve the project.
- [Join us on Discord](https://discord.gg/K5ymm24aQh) - `#contributing` channel or say hello in the '#general' channel
- [**Coming Soon!** Roadmap to contribute your ideas](#)
 

## License

MIT License

