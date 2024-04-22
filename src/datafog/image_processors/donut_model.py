

from transformers import DonutProcessor, VisionEncoderDecoderModel
from PIL import Image
import warnings
from io import BytesIO
import re
import torch


model_configs = {
    'read': {
        'model': "naver-clova-ix/donut-base-finetuned-rvlcdip",
        'processor': "naver-clova-ix/donut-base-finetuned-rvlcdip"
    },
    'parse': {
        'model': "naver-clova-ix/donut-base-finetuned-cord-v2",
        'processor': "naver-clova-ix/donut-base-finetuned-cord-v2"
    },
    'vqa': {
        'model': "naver-clova-ix/donut-base-finetuned-docvqa",
        'processor': "naver-clova-ix/donut-base-finetuned-docvqa"
    }
}

class DonutImageProcessor:
    def __init__(self, operation_type: str):
        self.processor = DonutProcessor.from_pretrained(model_configs[operation_type]['processor'])
        self.model = VisionEncoderDecoderModel.from_pretrained(model_configs[operation_type]['model'])
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
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
            raise ValueError(f"Unable to read the image file: {e}. Ensure it is a valid image.")

    def classify_image(self, image: Image.Image) -> dict:
        return self._process_image(image, operation_type_prompt="<s_rvlcdip>")

    def parse_image(self, image: Image.Image) -> dict:
        return self._process_image(image, operation_type_prompt="<s_cord-v2>")

    def question_image(self, image: Image.Image, question: str = "what is shown in this image?") -> dict:
        operation_type_prompt = f"<s_docvqa><s_question>{question}</s_question><s_answer>"
        return self._process_image(image, operation_type_prompt=operation_type_prompt)

    def _process_image(self, image: Image.Image, operation_type_prompt: str) -> dict:
        decoder_input_ids = self.processor.tokenizer(operation_type_prompt, add_special_tokens=False, return_tensors="pt").input_ids
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
        sequence = sequence.replace(self.processor.tokenizer.eos_token, "").replace(self.processor.tokenizer.pad_token, "")
        sequence = re.sub(r"<.*?>", "", sequence, count=1).strip()  # remove first operation_type start token

        return self.processor.token2json(sequence)
    
# image_path = "/Users/sidmohan/Desktop/datafog-fresh/datafog-python/src/datafog/test-invoice.png"

# # READ IMAGE
# try:
#     with open(image_path, "rb") as image_file:
#         image_bytes = image_file.read()
#     image = DonutImageProcessor.read_image(image_bytes)
#     print(image)
# except Exception as e:
#     print(f"Failed to process image: {e}")

# # CLASSIFY IMAGE
# try:
#     processor = DonutImageProcessor("read")
#     output = processor.classify_image(image)
#     print(output)
# except Exception as e:
#     print(f"Error during image classification: {e}")

# # PARSE IMAGE
# try:
#     processor = DonutImageProcessor("parse")
#     output = processor.parse_image(image)
#     print(output)
# except Exception as e:
#     print(f"Error during image parsing: {e}")

# # QUESTION IMAGE
# try:
#     processor = DonutImageProcessor("vqa")
#     output = processor.question_image(image)
#     print(output)
# except Exception as e:
#     print(f"Error during PII detection: {e}")

