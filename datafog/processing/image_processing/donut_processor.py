"""
Provides functionality for processing images using the Donut model.

This module implements a DonutProcessor class that uses the Donut model
for document understanding tasks, particularly OCR and information extraction
from images of documents.
"""

import importlib
import json
import logging
import re
import subprocess
import sys
from io import BytesIO

import numpy as np
import requests
from PIL import Image

from .image_downloader import ImageDownloader


class DonutProcessor:
    """
    Handles image processing using the Donut model.

    Provides methods for loading models, preprocessing images, parsing images
    for text extraction, and managing dependencies. Supports processing both
    local images and images from URLs.
    """

    def __init__(self, model_path="naver-clova-ix/donut-base-finetuned-cord-v2"):
        # Store model path for lazy loading
        self.model_path = model_path
        self.downloader = ImageDownloader()

    def ensure_installed(self, package_name):
        try:
            importlib.import_module(package_name)
        except ImportError:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", package_name]
            )

    def preprocess_image(self, image: Image.Image) -> np.ndarray:
        # Convert to RGB if the image is not already in RGB mode
        if image.mode != "RGB":
            image = image.convert("RGB")

        # Convert to numpy array
        image_np = np.array(image)

        # Ensure the image is 3D (height, width, channels)
        if image_np.ndim == 2:
            image_np = np.expand_dims(image_np, axis=-1)
            image_np = np.repeat(image_np, 3, axis=-1)

        return image_np

    async def extract_text_from_image(self, image: Image.Image) -> str:
        """Extract text from an image using the Donut model"""
        # This is where we would normally call the model, but for now
        # we'll just return a placeholder since we're guarding the imports
        logging.info("DonutProcessor.extract_text_from_image called")

        # Only import torch and transformers when actually needed
        try:
            # Ensure dependencies are installed
            self.ensure_installed("torch")
            self.ensure_installed("transformers")

            # Import dependencies only when needed
            import torch
            from transformers import DonutProcessor as TransformersDonutProcessor
            from transformers import VisionEncoderDecoderModel

            # Preprocess the image
            image_np = self.preprocess_image(image)

            # Initialize model components
            processor = TransformersDonutProcessor.from_pretrained(self.model_path)
            model = VisionEncoderDecoderModel.from_pretrained(self.model_path)
            device = "cuda" if torch.cuda.is_available() else "cpu"
            model.to(device)
            model.eval()

            # Process the image
            task_prompt = "<s_cord-v2>"
            decoder_input_ids = processor.tokenizer(
                task_prompt, add_special_tokens=False, return_tensors="pt"
            ).input_ids
            pixel_values = processor(images=image_np, return_tensors="pt").pixel_values

            outputs = model.generate(
                pixel_values.to(device),
                decoder_input_ids=decoder_input_ids.to(device),
                max_length=model.decoder.config.max_position_embeddings,
                early_stopping=True,
                pad_token_id=processor.tokenizer.pad_token_id,
                eos_token_id=processor.tokenizer.eos_token_id,
                use_cache=True,
                num_beams=1,
                bad_words_ids=[[processor.tokenizer.unk_token_id]],
                return_dict_in_generate=True,
            )

            sequence = processor.batch_decode(outputs.sequences)[0]
            sequence = sequence.replace(processor.tokenizer.eos_token, "").replace(
                processor.tokenizer.pad_token, ""
            )
            sequence = re.sub(r"<.*?>", "", sequence, count=1).strip()

            result = processor.token2json(sequence)
            return json.dumps(result)

        except Exception as e:
            logging.error(f"Error in extract_text_from_image: {e}")
            # Return a placeholder in case of error
            return "Error processing image with Donut model"

    async def process_url(self, url: str) -> str:
        """Download an image from URL and process it to extract text."""
        image = await self.downloader.download_image(url)
        return await self.extract_text_from_image(image)

    async def download_image(self, url: str) -> Image.Image:
        """Download an image from URL."""
        return await self.downloader.download_image(url)
