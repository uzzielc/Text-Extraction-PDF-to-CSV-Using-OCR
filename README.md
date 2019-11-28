# Text Extraction with Convert.py
This is a project developed for Premeir Management & Review Solutions (PM&R).
The purpose of this project is to semi-automate a data entry process for PM&R.

This project uses Optical Character Recognition to extract and restructure text from PDF files and writes to CSV files. 
Prior to the creation of this algorithm, a PM&R employee was tasked with copying text from the input document and pasting into the PM&R online database, one field at a time & one document at a time. Hundreds of these documents are processed every month and a large amount of time is spent on this low-level task.
By leveraging OCR, we can extract, process, and restructure the text found in the input document and create a structured CSV file which is then used to upload into the PM&R online database cutting the labor costs spent on this task by over 50%.

## Dependencies
This python script relies on:
    [Wand](http://docs.wand-py.org/en/0.5.7/) (for reading PDF files and converting to image format)
