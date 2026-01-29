"""VertexAI embeddings"""
from config import EMBEDDING_BATCH_SIZE, EMBEDDING_MODEL, GCP_PROJECT_ID, GCP_LOCATION
from vertexai.language_models import TextEmbeddingModel
from google.cloud import aiplatform
import logging

logger = logging.getLogger(__name__)

class Embeddings:
    def __init__(self):
        try:
            aiplatform.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)  # set up vertexai client
            self.embedding_model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)
            logger.info("VertexAI initialised")
        except Exception as e:
            logger.error(f"Failed to initialise VertexAI: {e}", exc_info=True)
            raise   # propogate exception

    def embed_chunks_in_batches(self, chunks):
        """Embed chunks in batches and insert into pinecone db"""
        embeddings = []

        for i in range(0,len(chunks), EMBEDDING_BATCH_SIZE):
            batch = chunks[i:i + EMBEDDING_BATCH_SIZE]

            texts = [chunk["data"] for chunk in batch]

            # Batch embeddings calls
            try:
                text_embeddings = self.embedding_model.get_embeddings(texts)
            except Exception as e:
                logger.error(f"Failed to embed batch {i//EMBEDDING_BATCH_SIZE + 1}: {e}", exc_info=True)
                raise   # dont want partial documents stored

            # prepare chunks for pinecone
            for j, chunk in enumerate(batch):
                embeddings.append({
                    "id": chunk["id"],
                    "values": text_embeddings[j].values,  # actual embeddings vector
                    "metadata": {
                        "text": chunk["data"],
                        "filename": chunk["filename"],
                        "gcs_uri": chunk["gcs_uri"]
                    }
                })
        
            logger.info(f"Embedded batch {i//EMBEDDING_BATCH_SIZE + 1}: {len(batch)} chunks")

        return embeddings
