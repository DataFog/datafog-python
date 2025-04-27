#!/bin/bash
# Simple CLI benchmark for DataFog text service

# --- Configuration ---
NUM_LOOPS=5
# SAMPLE_TEXT="Redact my name, John Doe, and my organization, Acme Inc."
JSON_FILE="scripts/sample_otel_log.json" # Added
VENV_PATH="./venv_4.0.1" # Assuming venv is in the project root
TIME_CMD="/usr/bin/time" # Use full path for `time` to avoid shell built-in

# Get project root directory (assuming the script is run from the project root)
PROJECT_DIR=$(pwd)

# Check if venv exists
if [ ! -d "$VENV_PATH" ]; then
    echo "Error: Virtual environment not found at $VENV_PATH"
    exit 1
fi

# Construct absolute paths
DATAFOG_CLI="$VENV_PATH/bin/datafog"
JSON_FILE_PATH="$PROJECT_DIR/$JSON_FILE" # Added

# Check if files/commands exist
if [ ! -x "$DATAFOG_CLI" ]; then
    echo "Error: DataFog CLI not found or not executable at $DATAFOG_CLI"
    exit 1
fi

# Check if jq is installed
if ! command -v jq &> /dev/null
then
    echo "Error: jq is not installed. Please install jq (e.g., 'brew install jq' or 'sudo apt-get install jq')."
    exit 1
fi

# Check if JSON file exists
if [ ! -f "$JSON_FILE_PATH" ]; then
    echo "Error: JSON file not found at $JSON_FILE_PATH"
    exit 1
fi




# Function to extract strings using jq
get_json_strings() { # Added
    jq -r '.. | strings?' "$JSON_FILE_PATH"
}


echo "Starting CLI Benchmark for $JSON_FILE..." # Modified
echo "Working Directory: $(pwd)"
echo "Using DataFog CLI: $DATAFOG_CLI"
echo "Timing $NUM_LOOPS executions."
echo "---"

# --- Warm-up Run ---
echo "Performing warm-up run..."
# Pipe extracted strings to xargs and then to datafog
get_json_strings | xargs -I {} "$DATAFOG_CLI" redact-text "{}" > /dev/null # Modified
exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo "Error: Warm-up run failed with exit code $exit_code."
    exit 1
fi
echo "Warm-up complete."

# --- Timed Runs ---
echo "Starting timed benchmark loops..."
total_real_time=0
total_user_time=0
total_sys_time=0

for i in $(seq 1 $NUM_LOOPS)
do
    echo "Running loop $i/$NUM_LOOPS..."

    # Execute the command using time and capture stderr (which contains time output)
    # Pipe extracted strings to xargs and then to datafog
    time_output=$({ $TIME_CMD -p bash -c "jq -r '.. | strings?' \"$JSON_FILE_PATH\" | xargs -I {} \"$DATAFOG_CLI\" redact-text \"{}\" > /dev/null"; } 2>&1) # Modified
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo "Error: Benchmark loop $i failed with exit code $exit_code."
        # Decide if you want to exit or continue
        # exit 1
        continue # Skipping this loop's result
    fi

    # Extract real, user, sys times using awk
    real_time=$(echo "$time_output" | awk '/real/ {print $2}')
    user_time=$(echo "$time_output" | awk '/user/ {print $2}')
    sys_time=$(echo "$time_output" | awk '/sys/ {print $2}')

    # Add to totals using awk for floating point arithmetic
    total_real_time=$(awk "BEGIN {print $total_real_time + $real_time}")
    total_user_time=$(awk "BEGIN {print $total_user_time + $user_time}")
    total_sys_time=$(awk "BEGIN {print $total_sys_time + $sys_time}")

    echo "Loop $i time: Real=${real_time}s User=${user_time}s Sys=${sys_time}s"
done

# Calculate averages
avg_real_time=$(awk "BEGIN {print $total_real_time / $NUM_LOOPS}")
avg_user_time=$(awk "BEGIN {print $total_user_time / $NUM_LOOPS}")
avg_sys_time=$(awk "BEGIN {print $total_sys_time / $NUM_LOOPS}")

echo ""
echo "Average Execution Time (over $NUM_LOOPS runs):"
echo "  Real: ${avg_real_time}s"
echo "  User: ${avg_user_time}s"
echo "  Sys:  ${avg_sys_time}s"
echo "(Execution = extracting strings from $JSON_FILE with jq, piping each via xargs to 'datafog redact-text')" # Modified

echo "=================================="
echo "Benchmark complete."