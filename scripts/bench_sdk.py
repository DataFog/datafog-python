import json
import os
import sys
import timeit
from typing import Any, List

# Ensure the project root is in the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from datafog.models.anonymizer import Anonymizer, AnonymizerType
    from datafog.models.spacy_nlp import SpacyAnnotator
except ImportError:
    print("Error: Could not import SpacyAnnotator or Anonymizer.")
    print("Make sure datafog-python is installed in your environment.")
    print(f"Project root added to path: {project_root}")
    sys.exit(1)

# --- Configuration ---
NUM_RUNS = 1  # Run the full file processing once per timeit loop
NUM_LOOPS = 10  # Number of times to repeat the timeit measurement
JSON_FILE_PATH = os.path.join(project_root, "scripts", "sample_otel_log.json")


# --- Helper Function to Extract Strings ---
def extract_strings_from_json(data: Any) -> List[str]:
    """Recursively extract all string values from a JSON object/list."""
    strings = []
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(key, str):
                strings.append(key)
            strings.extend(extract_strings_from_json(value))
    elif isinstance(data, list):
        for item in data:
            strings.extend(extract_strings_from_json(item))
    elif isinstance(data, str):
        strings.append(data)
    return strings


print(f"Starting SDK Benchmark for {os.path.basename(JSON_FILE_PATH)}...")
print(
    f"Timing {NUM_RUNS} full file processing execution(s) per loop, repeated {NUM_LOOPS} times."
)
print("---")

# --- Setup Code for timeit ---
# This code runs once before each timing loop (NUM_LOOPS)
setup_code = """
import os
import sys
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
from datafog.models.spacy_nlp import SpacyAnnotator
from datafog.models.anonymizer import Anonymizer, AnonymizerType

# Instantiate the services
# Model loading happens here or on first call
annotator = SpacyAnnotator()
anonymizer = Anonymizer(anonymizer_type=AnonymizerType.REDACT)
"""

# --- Get Sample Data ---
try:
    with open(JSON_FILE_PATH, "r", encoding="utf-8") as f:
        json_data = json.load(f)
    sample_texts = extract_strings_from_json(json_data)
    if not sample_texts:
        print(f"Error: No strings found in {JSON_FILE_PATH}")
        sys.exit(1)
except FileNotFoundError:
    print(f"Error: JSON file not found at {JSON_FILE_PATH}")
    sys.exit(1)
except json.JSONDecodeError as e:
    print(f"Error decoding JSON {JSON_FILE_PATH}: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error reading or processing JSON file: {e}")
    sys.exit(1)

# --- Statement to Time ---
stmt_to_time = f"""
for text in {sample_texts}:
    if text:
        annotations = annotator.annotate_text(text)
        anonymizer.anonymize(text, annotations)
"""

# --- Running the Benchmark ---
try:
    print(f"Benchmarking processing of {len(sample_texts)} strings from the file:")
    # timeit runs the setup code, then runs stmt_to_time 'number' times,
    # and repeats this process 'repeat' times (if repeat is used).
    # It returns a list of times for each repetition.
    # We use number=NUM_RUNS here.
    times = timeit.repeat(
        stmt=stmt_to_time,
        setup=setup_code,
        number=NUM_RUNS,  # Number of executions per timing loop
        repeat=NUM_LOOPS,  # Number of timing loops
    )

    # Calculate average time per execution across all loops
    min_time_per_loop = min(times)
    avg_time_per_run = min_time_per_loop / NUM_RUNS

    print("---")
    print(f"Fastest loop time ({NUM_RUNS} runs): {min_time_per_loop:.6f} seconds")
    print(
        f"Average time per single full file processing (in fastest loop): {avg_time_per_run:.6f} seconds"
    )
    print("==================================")

except Exception as e:
    print(f"An error occurred during benchmarking: {e}")

print("Benchmark complete.")
