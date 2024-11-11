from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse,HTMLResponse


import os
import shutil
import webbrowser
from mind import RelianceQueryEngine

# together1.py

import nest_asyncio
nest_asyncio.apply()
app = FastAPI()

# Define the base directory where the "Datasources" folder exists
BASE_DIR = os.getcwd()
DATASOURCES_DIR = os.path.join(BASE_DIR, "Datasources")
Embeddings_DIR = os.path.join(BASE_DIR, "Embeddings")
# Path to the HTML file
HTML_FILE = os.path.join(BASE_DIR, "upload_files.html")
query_engine = None

## APi key
api_key = os.getenv("OPENAI_API_KEY")

@app.get("/")
def read_root():
    with open(HTML_FILE, "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content, status_code=200)
    return {"message": "Welcome to the Reliance Query Engine API"}

@app.post("/upload_files")
async def upload_files(folder_name: str = Form(...), files: list[UploadFile] = File(...)):
    # Create the folder inside "Datasources" if it doesn't exist
    document_folder_path = os.path.join(DATASOURCES_DIR, folder_name)
    if not os.path.exists(document_folder_path):
        os.makedirs(document_folder_path)

    # Save each file in the folder
    saved_files = []
    for file in files:
        file_path = os.path.join(document_folder_path, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_files.append(file.filename)
        
    print({"message": f"Files saved in {document_folder_path}","Folder name:":folder_name, "saved_files": saved_files})
    # document_folder_path: fullstack/datasources/jiten
    # folder_name: jiten
    # embeddings_folder_path: fullstack/embeddings/jiten

    global query_engine
    query_engine = RelianceQueryEngine(api_key, document_folder_path,folder_name)
    return JSONResponse({"message": f"Files saved in {document_folder_path}", "saved_files": saved_files})

@app.get("/query/")
async def query_endpoint(query_str: str):
    try:
        response = query_engine.query(query_str)
        result = str(response)
        metadata = []
        for key, value in response.metadata.items():
            page_number = value['page_label']
            file_name = value['file_name']
            metadata.append({
                "page_number": page_number,
                "file_name": file_name
            })
        return {"result": result, "metadata": metadata}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Open the HTML file in the default web browser
    webbrowser.open(f"file://{HTML_FILE}")
    # Run the FastAPI app
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)