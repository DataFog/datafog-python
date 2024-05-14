import asyncio

from datafog.processing.text_processing.spacy_pii_annotator import SpacyPIIAnnotator


class TextService:
    def __init__(self):
        self.annotator = SpacyPIIAnnotator.create()

    async def annotate_text(self, text):
        """Asynchronously annotate a single piece of text."""
        return await asyncio.to_thread(self.annotator.annotate, text)

    async def batch_annotate_texts(self, texts: list):
        """Asynchronously annotate a batch of texts."""
        tasks = [self.annotate_text(text) for text in texts]
        results = await asyncio.gather(*tasks)
        return dict(zip(texts, results))
