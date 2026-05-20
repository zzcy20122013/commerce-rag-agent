from pydantic import BaseModel


class ProductCard(BaseModel):
    product_id: str
    title: str
    subtitle: str
    price: int
    image_url: str
    rating: float
    sales: int
    stock_status: str
    reasons: list[str]
    score: float


class CatalogImportRequest(BaseModel):
    source_file: str
    image_root: str | None = None


class CatalogImportErrorItem(BaseModel):
    row: int
    product_id: str | None = None
    error: str


class CatalogImportResult(BaseModel):
    job_id: str
    source_file: str
    imported_count: int
    failed_count: int
    errors: list[CatalogImportErrorItem]


class IndexRebuildResult(BaseModel):
    job_id: str
    status: str
    product_text_count: int
    knowledge_docs_count: int
    product_images_count: int
