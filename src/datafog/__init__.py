# datafog-python/src/datafog/__init__.py
import json

import pandas as pd
import requests
import spacy

from .__about__ import __version__
from .pii_tools import PresidioEngine

__all__ = [
    "__version__",
    "PresidioEngine",
]


class DataFog:
    def __init__(self):
        self.nlp = spacy.load("en_spacy_pii_fast")

    @staticmethod
    def client():
        return DataFog()

    def __call__(self, input_source, privacy_operation):
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
                # Add more privacy operations as needed

        return text
