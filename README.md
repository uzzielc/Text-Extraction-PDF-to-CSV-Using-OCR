# Text Extraction with Convert.py
This is a project developed for Premeir Management & Review Solutions (PM&R).
The purpose of this project is to semi-automate a data entry process for PM&R.

This project uses Optical Character Recognition to extract and restructure text from PDF files and writes to CSV files. 
Prior to the creation of this algorithm, a PM&R employee was tasked with copying text from the input document and pasting into the PM&R online database, one field at a time & one document at a time. Hundreds of these documents are processed every month and a large amount of time is spent on this low-level task.
By leveraging OCR, we can extract, process, and restructure the text found in the input document and create a structured CSV file which is then used to upload into the PM&R online database cutting the labor costs spent on this task by over 50%.

## Dependencies
This python script relies on:    
- [NumPy](https://numpy.org) (for some image manipulation and filtering data)  
- [Pandas](https://pandas.pydata.org) (for taking the tesseract output and displaying tabulated information)  
- [Wand](http://docs.wand-py.org/en/0.5.7/) (for reading PDF files and converting to image format)  
- [OpenCV](https://opencv-python-tutroals.readthedocs.io/en/latest/py_tutorials/py_gui/py_image_display/py_image_display.html) (for image manipulation)  
- [PIL](https://www.pythonware.com/products/pil/) (for image manipulation)
- [Tesseract](https://github.com/tesseract-ocr/tesseract) (OCR Engine)
- [PyTesseract](https://pypi.org/project/pytesseract/) (Python wrapper for Tesseract)

## Running the Script
##### Note: Currently, the script only supports conversion for one file at a time. Future version will support conversion for multiple pdf files without having to re-run the script.
First, Create a new folder that will hold the python script (convert.py)  
Second, move the document that is to be converted into the folder containing the python script.  
Third, run convert.py from the command line.

## Performance
##### Because of the nature of the document and patient privacy laws, I am not posting images of the documents or the results themselves. I hope to be able to provide a form that I have generated containing no real patient information along with performance results in the future.

## Discussion


