# Using Azure Openai + Chromadb + Fastapi
Document Processing and Querying

This repository contains code for an AI-powered PDF query system built using FastAPI. The system allows users to upload PDF files, convert them into text, and perform queries to retrieve relevant information from the documents. Additionally, users can upload Excel files, which are converted to PDFs for processing.

## Features

- **PDF Upload**: Users can upload PDF files containing text documents.
- **Excel Upload**: Users can upload Excel files, which are converted to PDF format for processing.
- **Text Extraction**: The system extracts text from uploaded PDF files for indexing and querying.
- **Query Engine**: Utilizes a query engine powered by Azure OpenAI (GPT-35 Turbo) for answering user queries.
- **Database Integration**: Stores user queries in an Azure SQL database for future reference and analysis.

## Technologies Used

- **FastAPI**: FastAPI is used as the web framework for building the RESTful API.
- **Azure OpenAI**: Azure OpenAI provides the underlying AI model (GPT-35 Turbo) for generating responses to user queries.
- **ChromaDB**: ChromaDB is used for vector storage and indexing of document data.
- **PyODBC**: PyODBC is used for connecting to and interacting with the Azure SQL database.
- **Requests**: The Requests library is used for making HTTP requests to external services.
- **Hugging Face Transformers**: Hugging Face Transformers is used for text embedding and processing.
- **PDFKit**: PDFKit is used for converting Excel files to PDF format.
- **Base64**: Base64 encoding is used for converting PDF files to a format suitable for storage and transmission.

## Setup Instructions

1. Clone this repository to your local machine.
2. Install the required dependencies by running `pip install -r requirements.txt`.
3. Set up Azure services (Azure OpenAI, Azure SQL Database) and obtain the necessary credentials and endpoints.
4. Configure the application settings by modifying the appropriate configuration files (`config.py`, `.env`).
5. Start the FastAPI server by running `uvicorn main:app --reload`.
6. Access the API endpoints using a web browser or API client.

## API Endpoints

- `POST /finfunc/upload/pdf`: Upload a PDF file for indexing and querying.
- `POST /finfunc/techexcel`: Upload an Excel file for conversion to PDF format.
- `GET /finfunc/query-pdf/{index_number}`: Perform a query on an uploaded PDF file.
- `GET /finfunc/list-pdf`: List all uploaded PDF files and Excel files.

## Contributors

- Haritha M

## Issues

If you encounter any issues or have suggestions for improvements, please open an issue on the GitHub repository.
