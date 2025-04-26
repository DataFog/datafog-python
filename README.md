<p align="center">
  <a href="https://www.datafog.ai"><img src="public/colorlogo.png" alt="DataFog logo"></a>
</p>

<p align="center">
    <b>Open-source PII Detection & Anonymization</b>. <br />
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

## Installation

DataFog can be installed via pip:

```bash
pip install datafog
```

### Optional Features (Extras)

DataFog uses `extras` to manage dependencies for optional features like specific OCR engines or Apache Spark integration. You can install these as needed:

*   **OCR (Tesseract):** For image scanning using Tesseract. Requires Tesseract OCR engine to be installed on your system separately.
    ```bash
    pip install "datafog[ocr]"
    ```
*   **OCR (Donut):** For image scanning using the Donut document understanding model.
    ```bash
    pip install "datafog[donut]"
    ```
*   **Spark:** For processing data using PySpark.
    ```bash
    pip install "datafog[spark]"
    ```
*   **All:** To install all optional features at once.
    ```bash
    pip install "datafog[all]"
    ```

# CLI

## 📚 Quick Reference

| Command             | Description                          |
| ------------------- | ------------------------------------ |
| `scan-text`         | Analyze text for PII                 |
| `scan-image`        | Extract and analyze text from images |
| `redact-text`       | Redact PII in text                   |
| `replace-text`      | Replace PII with anonymized values   |
| `hash-text`         | Hash PII in text                     |
| `health`            | Check service status                 |
| `show-config`       | Display current settings             |
| `download-model`    | Get a specific spaCy model           |
| `list-spacy-models` | Show available models                |
| `list-entities`     | View supported PII entities          |

---

## 🔍 Detailed Usage

### Scanning Text

To scan and annotate text for PII entities:

```bash
datafog scan-text "Your text here"
```

**Example:**

```bash
datafog scan-text "Tim Cook is the CEO of Apple and is based out of Cupertino, California"
```

### Scanning Images

To extract text from images and optionally perform PII annotation:

```bash
datafog scan-image "path/to/image.png" --operations extract
```

**Example:**

```bash
datafog scan-image "nokia-statement.png" --operations extract
```

To extract text and annotate PII:

```bash
datafog scan-image "nokia-statement.png" --operations scan
```

### Redacting Text

To redact PII in text:

```bash
datafog redact-text "Tim Cook is the CEO of Apple and is based out of Cupertino, California"
```

which should output:

```bash
[REDACTED] is the CEO of [REDACTED] and is based out of [REDACTED], [REDACTED]
```

### Replacing Text

To replace detected PII:

```bash
datafog replace-text "Tim Cook is the CEO of Apple and is based out of Cupertino, California"
```

which should return something like:

```bash
[PERSON_B86CACE6] is the CEO of [UNKNOWN_445944D7] and is based out of [UNKNOWN_32BA5DCA], [UNKNOWN_B7DF4969]
```

Note: a unique randomly generated identifier is created for each detected entity

### Hashing Text

You can select from SHA256, SHA3-256, and MD5 hashing algorithms to hash detected PII. Currently the hashed output does not match the length of the original entity, for privacy-preserving purposes. The default is SHA256.

```bash
datafog hash-text "Tim Cook is the CEO of Apple and is based out of Cupertino, California"
```

generating an output which looks like this:

```bash
5738a37f0af81594b8a8fd677e31b5e2cabd6d7791c89b9f0a1c233bb563ae39 is the CEO of f223faa96f22916294922b171a2696d868fd1f9129302eb41a45b2a2ea2ebbfd and is based out of ab5f41f04096cf7cd314357c4be26993eeebc0c094ca668506020017c35b7a9c, cad0535decc38b248b40e7aef9a1cfd91ce386fa5c46f05ea622649e7faf18fb
```

### Utility Commands

#### 🏥 Health Check

```bash
datafog health
```

#### ⚙️ Show Configuration

```bash
datafog show-config
```

#### 📥 Download Model

```bash
datafog download-model en_core_web_sm
```

#### 📂 Show Model Directory

```bash
datafog show-spacy-model-directory en_core_web_sm
```

#### 📋 List Models

```bash
datafog list-spacy-models
```

#### 🏷️ List Entities

```bash
datafog list-entities
```

---

## ⚠️ Important Notes

- For `scan-image` and `scan-text` commands, use `--operations` to specify different operations. Default is `scan`.
- Process multiple images or text strings in a single command by providing multiple arguments.
- Ensure proper permissions and configuration of the DataFog service before running commands.

---

💡 **Tip:** For more detailed information on each command, use the `--help` option, e.g., `datafog scan-text --help`.

# Python SDK

## Getting Started

To use DataFog, you'll need to create a DataFog client with the desired operations. Here's a basic setup:

```python
from datafog import DataFog

# For text annotation
client = DataFog(operations="scan")

# For OCR (Optical Character Recognition)
ocr_client = DataFog(operations="extract")
```

## Text PII Annotation

Here's an example of how to annotate PII in a text document:

```
import requests

# Fetch sample medical record
doc_url = "https://gist.githubusercontent.com/sidmohan0/b43b72693226422bac5f083c941ecfdb/raw/b819affb51796204d59987893f89dee18428ed5d/note1.txt"
response = requests.get(doc_url)
text_lines = [line for line in response.text.splitlines() if line.strip()]

# Run annotation
annotations = client.run_text_pipeline_sync(str_list=text_lines)
print(annotations)
```

## OCR PII Annotation

For OCR capabilities, you can use the following:

```
import asyncio
import nest_asyncio

nest_asyncio.apply()


async def run_ocr_pipeline_demo():
    image_url = "https://s3.amazonaws.com/thumbnails.venngage.com/template/dc377004-1c2d-49f2-8ddf-d63f11c8d9c2.png"
    results = await ocr_client.run_ocr_pipeline(image_urls=[image_url])
    print("OCR Pipeline Results:", results)


loop = asyncio.get_event_loop()
loop.run_until_complete(run_ocr_pipeline_demo())
```

Note: The DataFog library uses asynchronous programming for OCR, so make sure to use the `async`/`await` syntax when calling the appropriate methods.

## Text Anonymization

DataFog provides various anonymization techniques to protect sensitive information. Here are examples of how to use them:

### Redacting Text

To redact PII in text:

```python
from datafog import DataFog
from datafog.config import OperationType

client = DataFog(operations=[OperationType.SCAN, OperationType.REDACT])

text = "Tim Cook is the CEO of Apple and is based out of Cupertino, California"
redacted_text = client.run_text_pipeline_sync([text])[0]
print(redacted_text)
```

Output:

```
[REDACTED] is the CEO of [REDACTED] and is based out of [REDACTED], [REDACTED]
```

### Replacing Text

To replace detected PII with unique identifiers:

```python
from datafog import DataFog
from datafog.config import OperationType

client = DataFog(operations=[OperationType.SCAN, OperationType.REPLACE])

text = "Tim Cook is the CEO of Apple and is based out of Cupertino, California"
replaced_text = client.run_text_pipeline_sync([text])[0]
print(replaced_text)
```

Output:

```
[PERSON_B86CACE6] is the CEO of [UNKNOWN_445944D7] and is based out of [UNKNOWN_32BA5DCA], [UNKNOWN_B7DF4969]
```

### Hashing Text

To hash detected PII:

```python
from datafog import DataFog
from datafog.config import OperationType
from datafog.models.anonymizer import HashType

client = DataFog(operations=[OperationType.SCAN, OperationType.HASH], hash_type=HashType.SHA256)

text = "Tim Cook is the CEO of Apple and is based out of Cupertino, California"
hashed_text = client.run_text_pipeline_sync([text])[0]
print(hashed_text)
```

Output:

```
5738a37f0af81594b8a8fd677e31b5e2cabd6d7791c89b9f0a1c233bb563ae39 is the CEO of f223faa96f22916294922b171a2696d868fd1f9129302eb41a45b2a2ea2ebbfd and is based out of ab5f41f04096cf7cd314357c4be26993eeebc0c094ca668506020017c35b7a9c, cad0535decc38b248b40e7aef9a1cfd91ce386fa5c46f05ea622649e7faf18fb
```

You can choose from SHA256 (default), SHA3-256, and MD5 hashing algorithms by specifying the `hash_type` parameter

## Examples

For more detailed examples, check out our Jupyter notebooks in the `examples/` directory:

- `text_annotation_example.ipynb`: Demonstrates text PII annotation
- `image_processing.ipynb`: Shows OCR capabilities and text extraction from images

These notebooks provide step-by-step guides on how to use DataFog for various tasks.

### Dev Notes

For local development:

1. Clone the repository.
2. Navigate to the project directory:
   ```
   cd datafog-python
   ```
3. Create a new virtual environment (using `.venv` is recommended as it is hardcoded in the justfile):
   ```
   python -m venv .venv
   ```
4. Activate the virtual environment:
   - On Windows:
     ```
     .venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```
     source .venv/bin/activate
     ```
5. Install the package in editable mode:
   ```
   pip install -r requirements-dev.txt
   ```
6. Set up the project:
   ```
   just setup
   ```

Now, you can develop and run the project locally.

#### Important Actions:

- **Format the code**:
  ```
  just format
  ```
  This runs `isort` to sort imports.
- **Lint the code**:
  ```
  just lint
  ```
  This runs `flake8` to check for linting errors.
- **Generate coverage report**:
  ```
  just coverage-html
  ```
  This runs `pytest` and generates a coverage report in the `htmlcov/` directory.

We use [pre-commit](https://marketplace.visualstudio.com/items?itemName=elagil.pre-commit-helper) to run checks locally before committing changes. Once installed, you can run:

```
pre-commit run --all-files
```

#### Dependencies

For OCR, we use Tesseract, which is incorporated into the build step. You can find the relevant configurations under `.github/workflows/` in the following files:

- `dev-cicd.yml`
- `feature-cicd.yml`
- `main-cicd.yml`

### Testing

- Python 3.10

## License

This software is published under the [MIT
license](https://en.wikipedia.org/wiki/MIT_License).
