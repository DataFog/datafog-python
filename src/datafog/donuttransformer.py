import re
import warnings
from io import BytesIO

from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel

from .config import OperationConfig, PipelineOperationType


class DonutImageProcessor:
    """
    A class to process images using the Donut model for different operations like classification, parsing, and question answering.

    Attributes:
        operation_type (PipelineOperationType): The type of operation to perform (e.g., READ_IMAGE, PARSE_IMAGE).
        processor (DonutProcessor): The processor associated with the specific Donut model.
        model (VisionEncoderDecoderModel): The model loaded based on the operation type.
        device (str): The device on which the model will run (default is 'cpu').

    Methods:
        read_image(file: bytes) -> Image.Image:
            Reads an image from bytes, converts it to RGB if necessary, and returns the PIL Image.

        classify_image(image: Image.Image) -> dict:
            Processes the image for classification using the Donut model.

        parse_image(image: Image.Image) -> dict:
            Processes the image for parsing key information using the Donut model.

        question_image(image: Image.Image, question: str) -> dict:
            Processes the image to answer a question about the image using the Donut model.

        _process_image(image: Image.Image, operation_type_prompt: str) -> dict:
            A helper method to process the image with the model using a specific operation type prompt.
    """

    def __init__(self, operation_type: PipelineOperationType):
        self.operation_type = operation_type
        model_config = OperationConfig.model_validator(
            None, {"operation_type": operation_type}
        )
        self.processor = DonutProcessor.from_pretrained(model_config.processor)
        self.model = VisionEncoderDecoderModel.from_pretrained(model_config.model)
        self.device = "cpu"
        self.model.to(self.device)

    @staticmethod
    def read_image(file: bytes) -> Image.Image:
        try:
            image = Image.open(BytesIO(file))
            if image.mode != "RGB":
                warnings.warn("Image mode is not RGB. Converting to RGB.")
                image = image.convert("RGB")
            return image
        except IOError as e:
            raise ValueError(
                f"Unable to read the image file: {e}. Ensure it is a valid image."
            )

    def classify_image(self, image: Image.Image) -> dict:
        return self._process_image(image, operation_type_prompt="<s_rvlcdip>")

    def parse_image(self, image: Image.Image) -> dict:
        return self._process_image(image, operation_type_prompt="<s_cord-v2>")

    def question_image(
        self, image: Image.Image, question: str = "what is shown in this image?"
    ) -> dict:
        operation_type_prompt = (
            f"<s_docvqa><s_question>{question}</s_question><s_answer>"
        )
        return self._process_image(image, operation_type_prompt=operation_type_prompt)

    def _process_image(self, image: Image.Image, operation_type_prompt: str) -> dict:
        decoder_input_ids = self.processor.tokenizer(
            operation_type_prompt, add_special_tokens=False, return_tensors="pt"
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
        sequence = re.sub(
            r"<.*?>", "", sequence, count=1
        ).strip()  # remove first operation_type start token

        return self.processor.token2json(sequence)
