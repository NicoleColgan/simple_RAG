"""VertexAI embeddings"""
from config import EMBEDDING_BATCH_SIZE, EMBEDDING_MODEL, GCP_PROJECT_ID, GCP_LOCATION, LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_OUTPUT_TOKENS
from vertexai.language_models import TextEmbeddingModel
from google.cloud import aiplatform
import logging
from vertexai.generative_models import GenerativeModel, GenerationConfig
from services.prompts import construct_system_prompt, RESPONSE_SCHEMA
import json

logger = logging.getLogger(__name__)

class Embeddings:
    def __init__(self):
        try:
            aiplatform.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)  # set up vertexai client
            self.embedding_model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)
            self.llm = GenerativeModel(LLM_MODEL)
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
    
    def get_single_embedding(self, text: str):
        """Get embedding for a single text (e.g., user query)"""
        try:
            embeddings = self.embedding_model.get_embeddings([text])  # Expects a list
            return embeddings[0].values  # Return the 768-dim vector
        except Exception as e:
            logger.error(f"Failed to create embedding from text: {text}: {e}", exc_info=True)
            raise

    def get_answer(self, context: list[dict], user_query: str, stream: bool = False):
        try:
            response = self.llm.generate_content(
                contents=construct_system_prompt(user_query,context),
                generation_config=GenerationConfig( # https://docs.cloud.google.com/vertex-ai/generative-ai/docs/reference/rest/v1beta1/GenerationConfig
                    response_mime_type="application/json",
                    response_schema=RESPONSE_SCHEMA,
                    temperature=LLM_TEMPERATURE,
                    max_output_tokens=LLM_MAX_OUTPUT_TOKENS
                ),
                stream=stream
            )
            if stream:
                return response # generator for streaming
            return json.loads(response.text)
        except json.JSONDecodeError as json_decode_error:
            logger.error(f"Error decoding json from model response: {json_decode_error}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Error getting response from LLM: {e}", exc_info=True)
            raise