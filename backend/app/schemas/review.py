from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class ReviewStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class FindingSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(str, Enum):
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    MAINTAINABILITY = "maintainability"


class FindingBase(BaseModel):
    file_path: str = Field(..., max_length=500)
    start_line: int = Field(..., ge=1)
    end_line: int = Field(..., ge=1)
    severity: FindingSeverity
    category: FindingCategory
    title: str = Field(..., max_length=500)
    description: str
    suggestion: Optional[str] = None
    rule_id: Optional[str] = Field(None, max_length=100)
    is_llm_generated: bool = False
    llm_explanation: Optional[str] = None


class FindingCreate(FindingBase):
    pass


class FindingUpdate(BaseModel):
    severity: Optional[FindingSeverity] = None
    category: Optional[FindingCategory] = None
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    suggestion: Optional[str] = None
    rule_id: Optional[str] = Field(None, max_length=100)
    is_llm_generated: Optional[bool] = None
    llm_explanation: Optional[str] = None


class FindingResponse(FindingBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    review_id: int
    created_at: datetime


class ReviewBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    repository_url: Optional[str] = Field(None, max_length=500)
    base_branch: str = Field("main", max_length=255)
    head_branch: str = Field(..., max_length=255)
    diff_content: Optional[str] = None


class ReviewCreate(ReviewBase):
    pass


class ReviewUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    repository_url: Optional[str] = Field(None, max_length=500)
    base_branch: Optional[str] = Field(None, max_length=255)
    head_branch: Optional[str] = Field(None, max_length=255)
    diff_content: Optional[str] = None
    status: Optional[ReviewStatus] = None


class ReviewListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    author_id: int
    title: str
    description: Optional[str]
    repository_url: Optional[str]
    base_branch: str
    head_branch: str
    status: ReviewStatus
    findings_count: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class ReviewDetailResponse(ReviewListResponse):
    findings: List[FindingResponse] = []


class ReviewSearchParams(BaseModel):
    status: Optional[ReviewStatus] = None
    author_id: Optional[int] = None
    repository_url: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class PaginatedReviews(BaseModel):
    items: List[ReviewListResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class ReviewExportRequest(BaseModel):
    review_id: int
    format: str = Field("json", pattern="^(json|sarif|markdown)$")


class ReviewExportResponse(BaseModel):
    content: str
    filename: str
    media_type: str


class ReviewImportRequest(BaseModel):
    content: str = Field(..., min_length=1)
    format: str = Field("json", pattern="^(json)$")


class ReviewImportResponse(ReviewDetailResponse):
    pass