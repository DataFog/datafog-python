import json

from .pii_annotation import ImageProcessor, SpacyPIIAnnotator, SparkProcessor
from .pyspark_udfs import (
    MAXIMAL_STRING_SIZE,
    PII_ANNOTATION_LABELS,
    broadcast_pii_annotator_udf,
    pii_annotator,
)


class DataFog:
    def __init__(self, use_spark=True, use_ocr=False, use_pii=True):
        self.spark_processor: SparkProcessor = SparkProcessor() if use_spark else None
        self.ocr_annotator: OCRPIIAnnotator = OCRPIIAnnotator() if use_ocr else None
        self.pii_annotator = SpacyPIIAnnotator.create() if use_pii else None

    # def run_ocr_to_pii(self, image_url: str, output_path: str = None):
    #     ocr_pii_annotator = OCRPIIAnnotator().run(image_url, output_path)
    #     return ocr_pii_annotator.run()

    # def run_text_to_pii(self, text: str):
    #     text_pii_annotator = TextPIIAnnotator(text)
    #     return text_pii_annotator()


class OCRPIIAnnotator:
    def __init__(self):
        self.spark_processor: SparkProcessor = None
        self.image_processor = ImageProcessor()
        self.text_annotator = SpacyPIIAnnotator.create()

    def run(self, image_url, output_path=None):
        try:
            # Download and process the image to extract text
            downloaded_image = self.image_processor.download_image(image_url)
            extracted_text = self.image_processor.parse_image(downloaded_image)

            # Annotate the extracted text for PII
            annotated_text = self.text_annotator.annotate(extracted_text)

            # Optionally, output the results to a JSON file
            if output_path:
                with open(output_path, "w") as f:
                    json.dump(annotated_text, f)

            return annotated_text

        finally:
            # Ensure Spark resources are released
            # self.spark_processor.spark.stop()
            pass


class TextPIIAnnotator:
    def __init__(self):
        self.text_annotator = SpacyPIIAnnotator.create()
        self.spark_processor: SparkProcessor = None

    def run(self, text, output_path=None):
        try:
            annotated_text = self.text_annotator.annotate(text)

            # Optionally, output the results to a JSON file
            if output_path:
                with open(output_path, "w") as f:
                    json.dump(annotated_text, f)

            return annotated_text

        finally:
            # Ensure Spark resources are released
            pass
