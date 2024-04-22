from datafog import DataFog

sotu_url = "https://gist.githubusercontent.com/sidmohan0/1aa3ec38b4e6594d3c34b113f2e0962d/raw/42e57146197be0f85a5901cd1dcdd9ad15b31bab/sotu_2023.txt"

# Initialize DataFog with PII detection enabled for the SOTU URL
datafog_instance = DataFog(source_url=sotu_url, pii_detection=True)

# Process the text to extract and detect PII
processed_result = datafog_instance.detect_pii()

# Display the extracted text and detected entities
print("Extracted Text:", processed_result.text)
print("Entities Detected:", processed_result.entities)


# # Instantiate a PIIDetectRequest with the URL for text extraction
# request = PIIDetectRequest(url=sotu_url)

# # Instantiate the workflow with the request
# workflow = PIIDetectWorkflow(request=request)

# # Run the workflow to process the request and get the response
# response = workflow.run()

# # Print the extracted text and the entities found
# print(response.text)
# print(response.entities)

# Test script for image processing capabilities using DataFog

# # Define the path to an image for testing
# image_path = "/Users/sidmohan/Desktop/datafog-fresh/datafog-python/src/datafog/test-invoice.png"

# # Test reading the image
# print("Testing image reading...")
# read_result = datafog_instance.process_image(image_path=image_path, operation_type="read")
# print("Read Result:", read_result)

# # Test classifying the image
# print("Testing image classification...")
# classify_result = datafog_instance.process_image(image_path=image_path, operation_type="read")
# print("Classification Result:", classify_result)

# # Test parsing the image
# print("Testing image parsing...")
# parse_result = datafog_instance.process_image(image_path=image_path, operation_type="parse")
# print("Parse Result:", parse_result)

# # Test questioning the image
# print("Testing image questioning...")
# question_result = datafog_instance.process_image(image_path=image_path, operation_type="vqa", question="What is shown in this image?")
# print("Question Result:", question_result)
