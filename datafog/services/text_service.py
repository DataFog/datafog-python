import asyncio

from datafog.processing.text_processing.spacy_pii_annotator import SpacyPIIAnnotator


class TextService:
    def __init__(self):
        self.annotator = SpacyPIIAnnotator.create()

    def annotate_text_sync(self, text):
        """Synchronously Annotate a text string."""
        print(f"Starting on {text.split()[0]}")
        res = self.annotator.annotate(text)
        print(f"Done processing {text.split()[0]}")
        return res

    def batch_annotate_text_sync(self, texts: list):
        """Synchronously annotate a list of text input."""
        results = [self.annotate_text_sync(text) for text in texts]
        return dict(zip(texts, results, strict=True))

    async def annotate_text_async(self, text):
        """Asynchronously annotate a text string."""
        return await asyncio.to_thread(self.annotator.annotate, text)

    async def batch_annotate_text_async(self, text: list):
        """Asynchronously annotate a list of text input."""
        tasks = [self.annotate_text_async(txt) for txt in text]
        results = await asyncio.gather(*tasks)
        return dict(zip(texts, results, strict=True))
