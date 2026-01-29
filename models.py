"""Pydantic models for request/response validation"""
from pydantic import BaseModel

class IngestResponse(BaseModel):
    files_processed: int
    filenames: list[str]
    chunks_ingested: int
    chunks: list[dict]
    error_msg: str | None

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    response: str