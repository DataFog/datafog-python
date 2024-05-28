# # Pytest test cases for the image_service.py module
# # The test cases are written to test the image_service.py module
# # The test cases will test the ImageService class
# # The ImageService class is responsible for downloading images and extracting text from the images
# # The ImageService class uses the ImageDownloader, DonutProcessor, and PytesseractProcessor classes
# # The ImageService class has two methods: download_images and ocr_extract
# # The download_images method is responsible for downloading the images from the given URLs
# # The ocr_extract method is responsible for extracting the text from the images
# # The ocr_extract method has two optional parameters: use_donut and use_tesseract
# # The use_donut parameter is used to select the donut processor for the OCR
# # The use_tesseract parameter is used to select the pytesseract processor for the OCR


# import pytest
# from PIL import Image

# from datafog.services.image_service import ImageService

# urls = [
#     "https://www.pdffiller.com/preview/101/35/101035394.png",
#     "https://www.pdffiller.com/preview/435/972/435972694.png",
# ]


# @pytest.mark.asyncio
# async def test_download_images():
#     image_service1 = ImageService()
#     images = await image_service1.download_images(urls)
#     assert len(images) == 2
#     assert all(isinstance(image, Image.Image) for image in images)


# @pytest.mark.asyncio
# async def test_ocr_extract_with_tesseract():
#     image_service2 = ImageService(use_tesseract=True, use_donut=False)
#     texts = await image_service2.ocr_extract(urls)
#     assert isinstance(texts, list)
#     assert all(isinstance(text, str) for text in texts)


# @pytest.mark.asyncio
# async def test_ocr_extract_with_both():
#     image_service3 = ImageService(use_tesseract=True, use_donut=True)
#     with pytest.raises(
#         ValueError, match="Both OCR processors cannot be selected simultaneously"
#     ):
#         await image_service3.ocr_extract(urls)


# @pytest.mark.asyncio
# async def test_ocr_extract_with_donut():
#     image_service4 = ImageService(use_donut=True, use_tesseract=False)
#     texts = await image_service4.ocr_extract(urls)
#     assert isinstance(texts, list)
#     assert all(isinstance(text, str) for text in texts)


# @pytest.mark.asyncio
# async def test_ocr_extract_no_processor_selected():
#     image_service5 = ImageService(use_tesseract=False, use_donut=False)
#     with pytest.raises(ValueError, match="No OCR processor selected"):
#         await image_service5.ocr_extract(urls)
