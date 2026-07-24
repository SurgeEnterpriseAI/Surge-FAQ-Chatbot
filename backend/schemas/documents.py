from pydantic import BaseModel


class UploadJobStatus(BaseModel):
    job_id: str
    kind: str
    status: str
    progress: float = 0.0
    current_file: str = ""
    added: int = 0
    skipped: int = 0
    error: str | None = None


class UploadResponse(BaseModel):
    job_id: str


class DocumentOut(BaseModel):
    source: str
    markdown_file: str
    searchable: bool = True
    status: str = "indexed"  # indexed | indexing | partially_indexed | unindexed
    vectors_indexed: int = 0
    expected_chunks: int = 0
    progress_pct: float = 100.0


class DocumentListResponse(BaseModel):
    documents: list[DocumentOut]
