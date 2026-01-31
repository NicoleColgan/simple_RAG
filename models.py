"""Pydantic models for request/response validation"""
from pydantic import BaseModel, StringConstraints, Field
from typing import Annotated, Literal

class IngestResponse(BaseModel):
    files_processed: int
    filenames: list[str]
    chunks_ingested: int
    chunks: list[dict]
    error_msg: str | None

class MetaDataFilter(BaseModel):
    key: Literal['text', 'filename', 'gcs_uri']
    operation: Literal['eq', 'ne']    # restrict to exact values
    value: str

class QueryRequest(BaseModel):
    query: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    metadata_filter: MetaDataFilter | None = None

class QueryResponse(BaseModel):
    response: str = Field(description="Model response to user query using context")
    sources: list = Field(description="Files used to answer this question")
    confidence: float = Field(description="Models confidence in its answer")