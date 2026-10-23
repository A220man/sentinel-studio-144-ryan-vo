from datetime import datetime, UTC
from typing import Optional, List
from sqlalchemy import String, Text, DateTime, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    keycloak_sub: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    reviews: Mapped[List["Review"]] = relationship("Review", back_populates="author", lazy="selectin")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="user", lazy="selectin")

    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
    )


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    repository_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    base_branch: Mapped[str] = mapped_column(String(255), default="main", nullable=False)
    head_branch: Mapped[str] = mapped_column(String(255), nullable=False)
    diff_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ReviewStatus] = mapped_column(SQLEnum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False, index=True)
    findings_count: Mapped[int] = mapped_column(default=0, nullable=False)
    critical_count: Mapped[int] = mapped_column(default=0, nullable=False)
    high_count: Mapped[int] = mapped_column(default=0, nullable=False)
    medium_count: Mapped[int] = mapped_column(default=0, nullable=False)
    low_count: Mapped[int] = mapped_column(default=0, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    author: Mapped["User"] = relationship("User", back_populates="reviews", lazy="selectin")
    findings: Mapped[List["Finding"]] = relationship("Finding", back_populates="review", lazy="selectin", cascade="all, delete-orphan")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="review", lazy="selectin")

    __table_args__ = (
        Index("ix_reviews_author_status", "author_id", "status"),
        Index("ix_reviews_created_desc", "created_at"),
    )


class FindingSeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(str, enum.Enum):
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    MAINTAINABILITY = "maintainability"


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    start_line: Mapped[int] = mapped_column(nullable=False)
    end_line: Mapped[int] = mapped_column(nullable=False)
    severity: Mapped[FindingSeverity] = mapped_column(SQLEnum(FindingSeverity), nullable=False, index=True)
    category: Mapped[FindingCategory] = mapped_column(SQLEnum(FindingCategory), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    suggestion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rule_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    is_llm_generated: Mapped[bool] = mapped_column(default=False, nullable=False)
    llm_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    review: Mapped["Review"] = relationship("Review", back_populates="findings", lazy="selectin")

    __table_args__ = (
        Index("ix_findings_review_severity", "review_id", "severity"),
        Index("ix_findings_file_path", "file_path"),
    )


class AuditAction(str, enum.Enum):
    LOGIN = "login"
    LOGOUT = "logout"
    REVIEW_CREATE = "review_create"
    REVIEW_UPDATE = "review_update"
    REVIEW_DELETE = "review_delete"
    REVIEW_EXPORT = "review_export"
    FINDING_CREATE = "finding_create"
    FINDING_UPDATE = "finding_update"
    SETTINGS_CHANGE = "settings_change"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    review_id: Mapped[Optional[int]] = mapped_column(ForeignKey("reviews.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[AuditAction] = mapped_column(SQLEnum(AuditAction), nullable=False, index=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs", lazy="selectin")
    review: Mapped[Optional["Review"]] = relationship("Review", back_populates="audit_logs", lazy="selectin")

    __table_args__ = (
        Index("ix_audit_logs_user_created", "user_id", "created_at"),
        Index("ix_audit_logs_review_created", "review_id", "created_at"),
        Index("ix_audit_logs_action_created", "action", "created_at"),
    )