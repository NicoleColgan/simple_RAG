from config import LLM_MAX_RESPONSE_LIMIT
SYSTEM_PROMPT = """
You are a helpful assistant that answers questions based ONLY on the provided context from a vector database

Rules:
1. Do not invent facts
2. Only answer the questions using the context. If the query cannot be answered using the context, say you dont know
3. Cite sources for your answer (by using the filename in the context metadata) in the form ["file1.txt", "file2.pdf"...]
4. Anwer in json format as per the answer format instructions below
"""

def construct_system_prompt(user_query: str, context: list[dict]):
    return f"""{SYSTEM_PROMPT}\n\n"question: {user_query}\n\ncontext: {context}"""

# Define response schema - https://docs.cloud.google.com/vertex-ai/generative-ai/docs/reference/rest/v1beta1/Schema
RESPONSE_SCHEMA = {
            "type": "object",
            "description": "json response schema for model",
            "properties": {
                "response": {
                    "type": "string",
                    "description": "Answer to the users question based on the context",
                    "nullable": False,
                    "maxLength": LLM_MAX_RESPONSE_LIMIT,  # soft limit - guidance for llm
                    "example": "Langchain is a framework for building your app with LLMs"
                },
                "sources": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of source filenames used",
                    "example": ["file1.txt", "file2.txt"],
                    "nullable": False,
                    "minItems": 0,  # can be empty if LLM cant answer question
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence in answer (0.0-1.0)",
                    "nullable": False,
                    "minimum": 0.0,
                    "maximum": 1.0,
                }
            },
            "required": ["response", "sources", "confidence"]
        }