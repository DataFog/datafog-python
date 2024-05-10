import json
import re
import warnings
from io import BytesIO
from typing import Any, Dict, List, Optional

import en_spacy_pii_fast
import requests
import spacy
import torch
from PIL import Image
from pydantic import BaseModel
from pyspark import SparkContext
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf
from pyspark.sql.types import ArrayType, StringType
from transformers import DonutProcessor, VisionEncoderDecoderModel

warnings.filterwarnings("ignore")
PII_ANNOTATION_LABELS = ["DATE_TIME", "LOC", "NRP", "ORG", "PER"]
MAXIMAL_STRING_SIZE = 1000000


from typing import Dict, List

import en_spacy_pii_fast
from pydantic import BaseModel


class SpacyPIIAnnotator(BaseModel):
    nlp: Any

    @classmethod
    def create(cls) -> "SpacyPIIAnnotator":
        """Factory method to load the spaCy model once when the class is instantiated."""
        nlp = en_spacy_pii_fast.load()
        return cls(nlp=nlp)

    def annotate(self, text: str) -> Dict[str, List[str]]:
        """Extract PII annotations from text."""
        if not text:
            return {label: [] for label in PII_ANNOTATION_LABELS}
        if len(text) > MAXIMAL_STRING_SIZE:
            text = text[:MAXIMAL_STRING_SIZE]

        doc = self.nlp(text)
        classified_entities = {label: [] for label in PII_ANNOTATION_LABELS}
        for ent in doc.ents:
            if ent.label_ in classified_entities:
                classified_entities[ent.label_].append(ent.text)

        return classified_entities

    class Config:
        arbitrary_types_allowed = True


from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import udf
from pyspark.sql.types import ArrayType, StringType


class SparkProcessor:
    def __init__(self):
        self.spark = self.create_spark_session()

    @staticmethod
    def create_spark_session() -> SparkSession:
        """Create and configure a Spark session."""
        return (
            SparkSession.builder.appName("DataFog")
            .config("spark.driver.memory", "8g")
            .config("spark.executor.memory", "8g")
            .getOrCreate()
        )

    def create_dataframe(self, data: List[tuple], schema: List[str]) -> DataFrame:
        """Convert a list of tuples to a Spark DataFrame with the specified schema."""
        return self.spark.createDataFrame(data, schema)

    def add_pii_annotations(self, df: DataFrame, annotation_udf: udf) -> DataFrame:
        """Add a new column to DataFrame with PII annotations."""
        return df.withColumn("pii_annotations", annotation_udf(df["text"]))

    def write_to_json(self, data: Any, output_path: str):
        """Write data to a JSON file."""
        with open(output_path, "w") as f:
            json.dump(data, f)

    def stop(self):
        """Stop the Spark session."""
        self.spark.stop()


import json
import re
from io import BytesIO

import requests
import torch
from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel


class ImageProcessor:
    def __init__(self, model_path="naver-clova-ix/donut-base-finetuned-cord-v2"):
        self.processor = DonutProcessor.from_pretrained(model_path)
        self.model = VisionEncoderDecoderModel.from_pretrained(model_path)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        self.model.eval()

    def download_image(self, url: str) -> Image:
        """Download an image from the specified URL and return a PIL Image."""
        response = requests.get(url)
        response.raise_for_status()  # This will raise an HTTPError for bad requests
        return Image.open(BytesIO(response.content)).convert("RGB")

    def parse_image(self, image: Image) -> str:
        """Process the image using DonutProcessor and VisionEncoderDecoderModel and extract text."""
        task_prompt = "<s_cord-v2>"
        decoder_input_ids = self.processor.tokenizer(
            task_prompt, add_special_tokens=False, return_tensors="pt"
        ).input_ids
        pixel_values = self.processor(image, return_tensors="pt").pixel_values

        outputs = self.model.generate(
            pixel_values.to(self.device),
            decoder_input_ids=decoder_input_ids.to(self.device),
            max_length=self.model.decoder.config.max_position_embeddings,
            early_stopping=True,
            pad_token_id=self.processor.tokenizer.pad_token_id,
            eos_token_id=self.processor.tokenizer.eos_token_id,
            use_cache=True,
            num_beams=1,
            bad_words_ids=[[self.processor.tokenizer.unk_token_id]],
            return_dict_in_generate=True,
        )

        sequence = self.processor.batch_decode(outputs.sequences)[0]
        sequence = sequence.replace(self.processor.tokenizer.eos_token, "").replace(
            self.processor.tokenizer.pad_token, ""
        )
        sequence = re.sub(r"<.*?>", "", sequence, count=1).strip()

        result = self.processor.token2json(sequence)
        return json.dumps(result)
