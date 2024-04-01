# datafog-python/src/datafog/__init__.py
import json
import logging
import tempfile
import pandas as pd
import requests
import spacy
from unstructured.partition.auto import partition
from io import BytesIO
from pathlib import Path

from .__about__ import __version__
from .pii_tools import PresidioEngine

logger = logging.getLogger(__name__).setLevel(logging.ERROR)

__all__ = [
    "__version__",
    "PresidioEngine",
]


class DataFog:
    """
    DataFog class for performing privacy operations on input data.

    This class uses the Spacy library to process and analyze input data for
    personally identifiable information (PII) and applies specified privacy
    operations to protect sensitive data.

    Attributes:
        nlp (spacy.lang): Spacy language model for PII detection.
    """

    def __init__(self):
        """
        Initialize the DataFog instance.

        Loads the Spacy language model for PII detection.
        """
        self.nlp = spacy.load("en_spacy_pii_fast")


    @staticmethod
    def client():
        """
        Create a new instance of the DataFog client.

        Returns:
            DataFog: A new instance of the DataFog client.
        """
        return DataFog()
    
    @staticmethod
    def upload_file(uploaded_file_path):
        uploaded_file_path = Path(uploaded_file_path)
        bytes_data = uploaded_file_path.read_bytes()
        texts = {}

        if not uploaded_file_path.exists():
            return "File not found."
        else:
            temp_file = tempfile.NamedTemporaryFile(delete=True, suffix=uploaded_file_path.suffix)
            temp_file.write(bytes_data)
            elements = partition(temp_file.name)
            text = ""
            for element in elements:
                text += element.text + "\n"
            texts[uploaded_file_path.name] = text

        return texts
    
    def __call__(self, input_source, privacy_operation):
        """
        Process the input data and apply the specified privacy operation.

        Args:
            input_source (Union[str, pd.DataFrame]): The input data source.
                Can be a URL, file path, or a string containing the data.
                Supported file formats: CSV, TXT, JSON, Parquet.
            privacy_operation (str): The privacy operation to apply.
                Supported operations: 'redact', 'annotate'.
        Returns:
            str: The processed text with the applied privacy operation.

        Raises:
            ValueError: If an unsupported input source type or privacy operation is provided.
        """
        if isinstance(input_source, str):
            if input_source.startswith(("http://", "https://")):
                print("Downloading file from URL")
                response = requests.get(input_source)
                text = response.text
            elif input_source.endswith((".csv", ".txt")):
                print("Reading  CSV/TXT from local path")
                with open(input_source, "r") as file:
                    text = file.read()
            elif input_source.endswith(".json"):
                print("Reading JSON from local path")
                with open(input_source, "r") as file:
                    data = json.load(file)
                    text = json.dumps(data)
            elif input_source.endswith(".parquet"):
                print("Reading Parquet from local path")
                df = pd.read_parquet(input_source)
                text = df.to_csv(index=False)
            else:
                text = input_source
        else:
            raise ValueError("Unsupported input source type")

        doc = self.nlp(text)

        # Chunk the text and perform privacy operation
        for ent in doc.ents:
            if ent.label_ in ["PERSON", "ORG", "GPE", "PHONE", "EMAIL", "URL"]:
                # Perform privacy operation based on the entity type
                if privacy_operation == "redact":
                    text = text.replace(ent.text, "[REDACTED]")
                elif privacy_operation == "annotate":
                    text = text.replace(ent.text, f"[{ent.label_}]")

                else:
                    raise ValueError(
                        f"Unsupported privacy operation: {privacy_operation}"
                    )

        return text
