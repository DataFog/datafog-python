import asyncio
from typing import Dict, List

from datafog.processing.text_processing.spacy_pii_annotator import SpacyPIIAnnotator


class TextService:
    def __init__(self, text_chunk_length: int = 1000):
        self.annotator = SpacyPIIAnnotator.create()
        self.text_chunk_length = text_chunk_length

    def _chunk_text(self, text: str) -> List[str]:
        """Split the text into chunks of specified length."""
        return [
            text[i : i + self.text_chunk_length]
            for i in range(0, len(text), self.text_chunk_length)
        ]

    def _combine_annotations(self, annotations: List[Dict]) -> Dict:
        """Combine annotations from multiple chunks."""
        combined = {}
        for annotation in annotations:
            for key, value in annotation.items():
                if key not in combined:
                    combined[key] = []
                combined[key].extend(value)
        return combined

    def annotate_text_sync(self, text: str) -> Dict:
        """Synchronously annotate a text string."""
        if not text:
            return {}
        print(f"Starting on {text.split()[0]}")
        chunks = self._chunk_text(text)
        annotations = []
        for chunk in chunks:
            res = self.annotator.annotate(chunk)
            annotations.append(res)
        combined = self._combine_annotations(annotations)
        print(f"Done processing {text.split()[0]}")
        return combined

    def batch_annotate_text_sync(self, texts: List[str]) -> Dict[str, Dict]:
        """Synchronously annotate a list of text input."""
        results = [self.annotate_text_sync(text) for text in texts]
        return dict(zip(texts, results, strict=True))

    async def annotate_text_async(self, text: str) -> Dict:
        """Asynchronously annotate a text string."""
        if not text:
            return {}
        chunks = self._chunk_text(text)
        tasks = [asyncio.to_thread(self.annotator.annotate, chunk) for chunk in chunks]
        annotations = await asyncio.gather(*tasks)
        return self._combine_annotations(annotations)

    async def batch_annotate_text_async(self, texts: List[str]) -> Dict[str, Dict]:
        """Asynchronously annotate a list of text input."""
        tasks = [self.annotate_text_async(txt) for txt in texts]
        results = await asyncio.gather(*tasks)
        return dict(zip(texts, results, strict=True))
