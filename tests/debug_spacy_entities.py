from datafog.services.text_service import TextService

# Create a TextService with spaCy engine
service = TextService(engine="spacy")

# Sample text with named entities
text = """John Smith works at Microsoft Corporation in Seattle.
He previously worked for Apple Inc. in California on January 15, 2020."""

# Get annotations
result = service.annotate_text_sync(text)

# Print all entity types
print("Entity types:", list(result.keys()))

# Print non-empty entities
print("Non-empty entities:")
for entity_type, values in result.items():
    if values:  # Only print non-empty lists
        print(f"  {entity_type}: {values}")
