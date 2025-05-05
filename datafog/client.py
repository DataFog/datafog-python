"""
Client module for DataFog.

Provides CLI commands for scanning images and text using DataFog's OCR and PII detection capabilities.
"""

import asyncio
import logging
from typing import List

import typer

from .config import OperationType, get_config
from .main import DataFog
from .models.anonymizer import Anonymizer, AnonymizerType, HashType
from .models.spacy_nlp import SpacyAnnotator

app = typer.Typer()


@app.command()
def scan_image(
    image_urls: List[str] = typer.Argument(
        None, help="List of image URLs or file paths to extract text from"
    ),
    operations: str = typer.Option("scan", help="Operation to perform"),
):
    """
    Scan images for text and PII.

    Extracts text from images using OCR, then detects PII entities.
    Handles both remote URLs and local file paths.

    Args:
        image_urls: List of image URLs or file paths
        operations: Pipeline operations to run (default: scan)

    Prints results or exits with error on failure.
    """
    if not image_urls:
        typer.echo("No image URLs or file paths provided. Please provide at least one.")
        raise typer.Exit(code=1)

    logging.basicConfig(level=logging.INFO)
    # Convert comma-separated string operations to a list of OperationType objects
    operation_list = [OperationType(op.strip()) for op in operations.split(",")]
    ocr_client = DataFog(operations=operation_list)
    try:
        results = asyncio.run(ocr_client.run_ocr_pipeline(image_urls=image_urls))
        typer.echo(f"OCR Pipeline Results: {results}")
    except Exception as e:
        logging.exception("Error in run_ocr_pipeline")
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(code=1)


@app.command()
def scan_text(
    str_list: List[str] = typer.Argument(
        None, help="List of texts to extract text from"
    ),
    operations: str = typer.Option("scan", help="Operation to perform"),
):
    """
    Scan texts for PII.

    Detects PII entities in a list of input texts.

    Args:
        str_list: List of texts to analyze
        operations: Pipeline operations to run (default: scan)

    Prints results or exits with error on failure.
    """
    if not str_list:
        typer.echo("No texts provided.")
        raise typer.Exit(code=1)

    logging.basicConfig(level=logging.INFO)
    # Convert comma-separated string operations to a list of OperationType objects
    operation_list = [OperationType(op.strip()) for op in operations.split(",")]
    text_client = DataFog(operations=operation_list)
    try:
        results = asyncio.run(text_client.run_text_pipeline(str_list=str_list))
        typer.echo(f"Text Pipeline Results: {results}")
    except Exception as e:
        logging.exception("Text pipeline error")
        typer.echo(f"Error: {str(e)}", err=True)
        raise typer.Exit(code=1)


@app.command()
def health():
    """
    Check DataFog service health.

    Prints a message indicating that DataFog is running.
    """
    typer.echo("DataFog is running.")


@app.command()
def show_config():
    """
    Show current configuration.

    Prints the current DataFog configuration.
    """
    typer.echo(get_config())


@app.command()
def download_model(model_name: str = typer.Argument(..., help="Model to download")):
    """
    Download a spaCy model.

    Args:
        model_name: Name of the model to download.

    Prints a confirmation message after downloading.
    """
    SpacyAnnotator.download_model(model_name)
    typer.echo(f"Model {model_name} downloaded.")


@app.command()
def show_spacy_model_directory(
    model_name: str = typer.Argument(..., help="Model to check")
):
    """
    Show the directory path for a spaCy model.

    Args:
        model_name: Name of the model to check.

    Prints the directory path of the specified model.
    """
    annotator = SpacyAnnotator(model_name)
    typer.echo(annotator.show_model_path())


@app.command()
def list_spacy_models():
    """
    List available spaCy models.

    Prints a list of all available spaCy models.
    """
    annotator = SpacyAnnotator()
    typer.echo(annotator.list_models())


@app.command()
def list_entities():
    """
    List available entities.

    Prints a list of all available entities that can be recognized.
    """
    annotator = SpacyAnnotator()
    typer.echo(annotator.list_entities())


@app.command()
def redact_text(text: str = typer.Argument(..., help="Text to redact")):
    """
    Redact PII in text.

    Args:
        text: Text to redact.

    Prints the redacted text.
    """
    annotator = SpacyAnnotator()
    anonymizer = Anonymizer(anonymizer_type=AnonymizerType.REDACT)
    annotations = annotator.annotate_text(text)
    result = anonymizer.anonymize(text, annotations)
    typer.echo(result.anonymized_text)


@app.command()
def replace_text(text: str = typer.Argument(..., help="Text to replace PII")):
    """
    Replace PII in text with anonymized values.

    Args:
        text: Text to replace PII.

    Prints the text with PII replaced.
    """
    annotator = SpacyAnnotator()
    anonymizer = Anonymizer(anonymizer_type=AnonymizerType.REPLACE)
    annotations = annotator.annotate_text(text)
    result = anonymizer.anonymize(text, annotations)
    typer.echo(result.anonymized_text)


@app.command()
def hash_text(
    text: str = typer.Argument(..., help="Text to hash PII"),
    hash_type: HashType = typer.Option(HashType.SHA256, help="Hash algorithm to use"),
):
    """
    Choose from SHA256, MD5, or SHA3-256 algorithms to hash detected PII in text.

    Args:
        text: Text to hash PII.
        hash_type: Hash algorithm to use.

    Prints the text with PII hashed.
    """
    annotator = SpacyAnnotator()
    anonymizer = Anonymizer(anonymizer_type=AnonymizerType.HASH, hash_type=hash_type)
    annotations = annotator.annotate_text(text)
    result = anonymizer.anonymize(text, annotations)
    typer.echo(result.anonymized_text)


if __name__ == "__main__":
    app()
