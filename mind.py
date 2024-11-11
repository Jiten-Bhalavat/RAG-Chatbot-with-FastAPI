import os
import openai
from dotenv import load_dotenv
load_dotenv()

from llama_index.core import (
     SimpleDirectoryReader,
     load_index_from_storage, 
     StorageContext,
     VectorStoreIndex,
     ServiceContext,
     PromptTemplate,
     get_response_synthesizer,
)

from llama_index.core.text_splitter import SentenceSplitter
from llama_index.llms.openai import OpenAI
from llama_index.core.postprocessor.sbert_rerank import SentenceTransformerRerank
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core import Settings



class RelianceQueryEngine:
    def __init__(self, api_key, document_folder_path, folder_name):
        openai.api_key = api_key
        self.document_folder_path = document_folder_path   #/jiten
        self.folder_name=folder_name    #jiten
        self.pdf_path_store=self.pdf_selector()
        self.documents = self.load_documents()
        self.nodes = self.create_nodes()
        # self.service_context = self.create_service_context()
        self.index = self.create_index()
        self.query_engine = self.create_query_engine()
        self.chunk_size=500
        self.chunk_overlap=100

    def pdf_selector(self):
        pdf_path_store=[]
        processed_filenames = set()
        metadata_file = os.path.join(self.document_folder_path, 'metadata.txt')

        # Load existing processed filenames if available
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as file:
                processed_filenames = set(file.read().splitlines())

        # Iterate through the folder and process new PDFs
        for filename in os.listdir(self.document_folder_path):
            if filename.endswith('.pdf'):
                pdf_path = os.path.join(self.document_folder_path, filename)

                # Check if the PDF has been processed before
                if filename not in processed_filenames:
                    pdf_path_store.append(pdf_path)
                    processed_filenames.add(filename)

        # Save the updated processed filenames
        with open(metadata_file, 'w') as file:
            file.write('\n'.join(processed_filenames))
        print(len(pdf_path_store))
        return pdf_path_store


    def load_documents(self):
        documents = []
        for pdf_path in self.pdf_path_store:
            load = SimpleDirectoryReader(input_files=[pdf_path]).load_data()
            documents.extend(load)

        print(f"Loaded {len(documents)} new documents")
        return documents
        # loaders = [
        #     SimpleDirectoryReader(self.document_folder_path),
        # ]  
        # for loader in loaders:
        #     documents.extend(loader.load_data())
        # print(f"Loaded {len(documents)} new documents")
        
    
    def create_nodes(self):
        node_parser = SentenceSplitter(chunk_size=500, chunk_overlap=100)        
        nodes = node_parser.get_nodes_from_documents(self.documents)
        print(f"{len(nodes)} Nodes Created")
        return nodes

    def create_service_context(self):
        Settings.llm= OpenAI(model="gpt-3.5-turbo", temperature=0.1)
        Settings.embed_model="local:BAAI/bge-large-en-v1.5",
        # service_context = ServiceContext.from_defaults(
        #     llm=llm,
        #     embed_model="local:BAAI/bge-large-en-v1.5",
        # )
        print(f"Models Loaded")
        return Settings.llm, Settings.embed_model

    def create_index(self):
        base_folder = os.getcwd()
        folder_path = os.path.join(base_folder, "Embeddings", self.folder_name)
        print("folder path in create index: ", folder_path)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path, exist_ok=True)
            index = VectorStoreIndex(self.nodes, Settings.llm, embed_model=Settings.embed_model)
            index.storage_context.persist(folder_path)
        else:
            storage_context = StorageContext.from_defaults(persist_dir=folder_path)
            index = load_index_from_storage(storage_context=storage_context)
            index.insert_nodes(self.nodes)
            index.storage_context.persist(folder_path)
        return index

    def create_query_engine(self):
        bge_reranker_large = SentenceTransformerRerank(model="BAAI/bge-reranker-large", top_n=3)
        qa_prompt_tmpl = (
            "Context information is below.\n"
            "---------------------\n"
            "{context_str}\\n"
            "---------------------\n"
            "Given the context information and not prior knowledge, "
            "answer the query.\n"
            "If the context information does not contain an answer to the query, "
            "respond with \"No information\".\n"
            "Query: {query_str}\n"
            "Answer: "
        )
        qa_prompt = PromptTemplate(qa_prompt_tmpl)
        retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=5,
            ## we can add here vector store query mode=hybrid 
        )
        response_synthesizer = get_response_synthesizer(
            llm=Settings.llm,
            text_qa_template=qa_prompt,
            response_mode="compact",
        )
        query_engine = RetrieverQueryEngine(
            retriever=retriever,
            response_synthesizer=response_synthesizer,
            node_postprocessors=[bge_reranker_large],
        )
        return query_engine

    def query(self, query_str):
        response = self.query_engine.query(query_str)
        return response

if __name__ == "__main__":
    pass