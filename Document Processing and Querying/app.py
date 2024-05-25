import logging, uuid, pyodbc, chromadb, os, requests, json, base64
from datetime import datetime
from fastapi import APIRouter, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from llama_index import ServiceContext, StorageContext, download_loader, GPTVectorStoreIndex
from llama_index.vector_stores import ChromaVectorStore
from llama_index.embeddings import HuggingFaceEmbedding
from llama_index.llms import AzureOpenAI
from tempfile import NamedTemporaryFile
from chromadb.config import Settings
from pathlib import Path
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

class QueryResponse(BaseModel):
    response: dict

router = APIRouter()

logging.basicConfig(level=logging.DEBUG)

llm = AzureOpenAI(
    model=os.getenv('AZURE_OPENAI_MODEL'),
    deployment_name=os.getenv('AZURE_OPENAI_DEPLOYMENT'),
    api_key=os.getenv('AZURE_OPENAI_API_KEY'),
    azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
    api_version=os.getenv('AZURE_OPENAI_API_VERSION'),
)

uploaded_pdf_data = {}
cache = {}
index_counter = 0
uploaded_excels = []

chroma_client = chromadb.PersistentClient(path="./storage/vector_storage/chromadb/", settings=Settings(allow_reset=True))
chroma_collection = chroma_client.get_or_create_collection("quickstart")

def excel_to_pdf(filename):
    instructions = {
        'parts': [
            {
                'file': 'document'
            }
        ]
    }
    response = requests.request(
        'POST',
        'https://api.pspdfkit.com/build',
        headers={
            'Authorization': f'Bearer {os.getenv("PSPDFKIT_API_KEY")}'
        },
        files={
            'document': open(filename, 'rb')
        },
        data={
            'instructions': json.dumps(instructions)
        },
        stream=True
    )
    if response.ok:
        pdf_name = filename.split('.')[0]
        with open(f'{pdf_name}.pdf', 'wb') as fd:
            for chunk in response.iter_content(chunk_size=20096):
                fd.write(chunk)
    else:
        print(response.text)
        exit()
    os.remove(filename)

def pdf_process(filename):
    PDFReader = download_loader("PDFReader")
    loader = PDFReader()
    documents = loader.load_data(file=Path(f'{filename}.pdf'))

    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5")
    service_context = ServiceContext.from_defaults(llm=llm, embed_model=embed_model)

    return GPTVectorStoreIndex.from_documents(
        documents, storage_context=storage_context, service_context=service_context
    )

def pdf_to_base64(file_path):
    try:
        with open(file_path, 'rb') as pdf_file:
            pdf_content = pdf_file.read()
            base64_encoded = base64.b64encode(pdf_content).decode('utf-8')
            print(base64_encoded)
            return base64_encoded
    except Exception as e:
        print(f"Error converting PDF to base64: {e}")
        return None

@router.post("/finfunc/techexcel")
async def upload_excel(excel: UploadFile = File(...)):
    directory = "Summ"
    os.makedirs(directory, exist_ok=True)
    file_location = f"./{excel.filename}"
    with open(file_location, "wb+") as file_object:
        file_object.write(excel.file.read())
    table_name = excel.filename.split('.')[0]
    uploaded_excels.append(table_name)
    excel_to_pdf(excel.filename)
    pdf_filepath = table_name + '.pdf'
    pdf_base64 = pdf_to_base64(pdf_filepath)
    os.remove(table_name + '.pdf')
    return {"message": f"Excel file '{excel.filename}' uploaded and saved under '{file_location}'. Table '{table_name}' created in Azure SQL Database.",
            "pdf_base64": f'{pdf_base64}'}

@router.get("/finfunc/uploaded/techexcel_names")
async def get_uploaded_excel_names():
    uploaded_excel_names = [name.split('.')[0] for name in uploaded_excels]
    return {"uploaded_excels": uploaded_excel_names}

def initialize_query_engine(pdf_content):
    global index_counter
    index_number = index_counter
    logging.debug(f"Initializing query engine for index {index_number}...")
    PDFReader = download_loader("PDFReader")
    loader = PDFReader()
    documents = loader.load_data(file=pdf_content)
    chroma_client = chromadb.EphemeralClient()
    chroma_collection = chroma_client.get_or_create_collection(str(uuid.uuid4()))
    embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    service_context = ServiceContext.from_defaults(
        llm=llm,
        embed_model=embed_model
    )
    index = GPTVectorStoreIndex.from_documents(
        documents, storage_context=storage_context, service_context=service_context, batch_size=20
    )
    return index

@router.post("/finfunc/upload/pdf")
async def upload_pdf(pdf: UploadFile = File(...)):
    try:
        global index_counter
        with NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(await pdf.read())
            temp_file.seek(0)
            index = initialize_query_engine(temp_file)
            uploaded_pdf_data[f'index_{index_counter}'] = pdf.filename
            cache[f'index_{index_counter}'] = index
            index_counter += 1
        return {"status": "done", "index_number": index_counter - 1}
    except Exception as e:
        return {"status - error": str(e)}

def answerme(query, index_number):
    try:
        if f'index_{index_number}' not in cache:
            raise ValueError(f"Index {index_number} not initialized")
        index = cache[f'index_{index_number}']
        logging.debug(f"Querying PDF using index {index_number}...")

        if any(keyword in query.lower() for keyword in ['summary', 'explain', 'detail']):
            query += " in 250 to 750 words"

        response = index.as_query_engine().query(query)
        return str(response)
    except Exception as e:
        logging.error(f"Error while processing query: {e}")
        raise e

def insert_into_database(user_query):
    print("Inserting user query into the database...")

    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        f"SERVER={os.getenv('AZURE_SQL_SERVER')};"
        f"DATABASE={os.getenv('AZURE_SQL_DATABASE')};"
        f"UID={os.getenv('AZURE_SQL_UID')};"
        f"PWD={os.getenv('AZURE_SQL_PWD')};"
    )

    cursor = conn.cursor()

    message_id = str(uuid.uuid4())

    sql_query = "INSERT INTO finfunc_record (MessageID, UserQuestion, Timestamp) VALUES (?, ?, ?)"
    timestamp = datetime.now()
    cursor.execute(sql_query, (message_id, user_query, timestamp))
    print("User query inserted successfully.")

    conn.commit()

@router.get("/finfunc/query-pdf/{index_number}")
async def query_pdf(query: str, index_number: int):
    try:
        query_result = answerme(query, index_number)

        insert_into_database(query)
        print("User query inserted into the database.")

        return {"response": query_result}
    except Exception as e:
        logging.error(f"Error querying PDF: {e}")
        return {"error": "Failed to query PDF"}

@router.get("/finfunc/list-pdf")
async def list_pdf():
    try:
        logging.debug("Listing PDFs and Excel files...")

        unique_filenames = set()

        pdf_filenames = list(uploaded_pdf_data.values())
        excel_names = list(uploaded_excels)

        all_filenames = pdf_filenames + excel_names

        all_filenames_filtered = []

        for filename in all_filenames:
            if "ABC" not in filename and filename not in unique_filenames:
                all_filenames_filtered.append(filename)
                unique_filenames.add(filename)

        logging.debug(f"Filtered Files found: {all_filenames_filtered}")

        return {"filenames": all_filenames_filtered}
    except Exception as e:
        logging.error(f"Error listing files: {e}")
        return {"error": str(e)}
