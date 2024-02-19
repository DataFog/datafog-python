from datafog.datafog import DataFog

# Create a DataFog instance
datafog = DataFog()

# Define the input file and output directory
input_file = "examples/files/sample.csv"
output_dir = "examples/"  # current directory

# Run the swap method
datafog.swap(input_file, output_dir)

datafog.redact(input_file)