import numpy as np
from voyageai import Client
from mdb_toolkit.InputHandler import PDFHandler, ImageHandler, S3PDFHandler, S3ImageHandler

MODEL_NAME = "voyage-multimodal-3"


class MultiModalRetriever():
    def __init__(self, mongo_client, database_name, collection_name, index_name, s3_client, bucket_name, voyage_api_key):
        self.client = mongo_client
        self.database_name = database_name
        self.collection_name = collection_name
        self.index_name = index_name
        self.s3 = s3_client
        self.bucket_name = bucket_name
        self.vo = self._get_voyage_client(voyage_api_key)


    def _get_voyage_client(self, voyage_api_key):
        return Client(api_key=voyage_api_key)


    def _create_input_processor(self, input):
        input_format = "pdf"
        if input.startswith("s3://"):
            if input.endswith(".pdf"):
                return S3PDFHandler()
            else:
                return S3ImageHandler()
        else: 
            if input.endswith(".pdf"):
                return PDFHandler(bucket_name=self.bucket_name)
            else:
                return ImageHandler(bucket_name=self.bucket_name)
    
    
    def _create_embedding(self, processed_inputs):
        # handle parsing out images from pdfs, and/or pulling images from s3
        # create and return the actual embeddings
        return np.array(
            self.vo.multimodal_embed(
            inputs=[[x] for x in processed_inputs],
            model=MODEL_NAME,
            input_type="document"
        ).embeddings)

    def _store_embedding(self, document_vectors, metadata):
        # store the embeddings in mongodb alongside the 
        # file metadata in S3
        for i, doc_vector in enumerate(document_vectors):
            self.client[self.database_name][self.collection_name].insert_one({
                "s3_full_path": metadata["s3_full_path"],
                "s3_bucket_name": metadata["s3_bucket_name"],
                "s3_key": metadata["s3_key"],
                "content_embedding": doc_vector.tolist()
            })
        return True

    def mm_embed(self, inputs):
        # main entry point for the multimodal retriever utility
        # establishes embeddings for the input files and saves them
        # to mongodb

        for input_file in inputs:
            handler = self._create_input_processor(input_file)
            processed_inputs, metadata = handler.preprocess(self.s3, input_file)
            document_vectors = self._create_embedding(processed_inputs)
            self._store_embedding(document_vectors, metadata)
        
        return True
        

    def mm_query(self, query, k=5):
        # query the multimodal retriever for the most similar
        # documents to the query
        vector_results = self.client.vector_search(
            query=query,
            limit=k,
            database_name=self.database_name,
            collection_name=self.collection_name,
            index_name=self.index_name,
            embedding_field="content_embedding", #voyageai :)
        )
        return vector_results


        
