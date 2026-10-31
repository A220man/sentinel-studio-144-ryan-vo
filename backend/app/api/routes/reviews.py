from datetime import datetime, UTC
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_active_user, require_operator, verify_csrf
from app.schemas.review import (
    ReviewCreate,
    ReviewUpdate,
    ReviewListResponse,
    ReviewDetailResponse,
    ReviewSearchParams,
    PaginatedReviews,
    ReviewExportRequest,
    ReviewExportResponse,
    ReviewImportRequest,
    ReviewImportResponse,
    FindingResponse,
    FindingCreate,
    FindingUpdate,
    ReviewStatus,
    FindingSeverity,
    FindingCategory,
)
from app.models import Review, Finding, User, AuditLog, AuditAction, UserRole
from app.core.config import settings

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("", response_model=ReviewDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    request: Request,
    review_data: ReviewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(verify_csrf),
) -> ReviewDetailResponse:
    review = Review(
        author_id=current_user.id,
        title=review_data.title,
        description=review_data.description,
        repository_url=review_data.repository_url,
        base_branch=review_data.base_branch,
        head_branch=review_data.head_branch,
        diff_content=review_data.diff_content,
        status=ReviewStatus.PENDING,
    )
    db.add(review)
    await db.flush()

    audit = AuditLog(
        user_id=current_user.id,
        review_id=review.id,
        action=AuditAction.REVIEW_CREATE,
        details=f"Created review: {review.title}",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(review)

    return ReviewDetailResponse.model_validate(review)


@router.get("", response_model=PaginatedReviews)
async def list_reviews(
    params: ReviewSearchParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> PaginatedReviews:
    query = select(Review).options(selectinload(Review.findings))

    # Non-admin users can only see their own reviews
    if current_user.role != UserRole.ADMIN:
        query = query.where(Review.author_id == current_user.id)

    if params.status:
        query = query.where(Review.status == params.status)
    if params.author_id:
        # Only admins can filter by other users' reviews
        if current_user.role == UserRole.ADMIN:
            query = query.where(Review.author_id == params.author_id)
    if params.repository_url:
        query = query.where(Review.repository_url.ilike(f"%{params.repository_url}%"))
    if params.date_from:
        query = query.where(Review.created_at >= params.date_from)
    if params.date_to:
        query = query.where(Review.created_at <= params.date_to)

    query = query.order_by(desc(Review.created_at))

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    offset = (params.page - 1) * params.page_size
    query = query.offset(offset).limit(params.page_size)

    result = await db.execute(query)
    reviews = result.scalars().all()

    return PaginatedReviews(
        items=[ReviewListResponse.model_validate(r) for r in reviews],
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=(total + params.page_size - 1) // params.page_size,
    )


@router.get("/{review_id}", response_model=ReviewDetailResponse)
async def get_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ReviewDetailResponse:
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.findings))
        .where(Review.id == review_id)
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return ReviewDetailResponse.model_validate(review)


@router.patch("/{review_id}", response_model=ReviewDetailResponse)
async def update_review(
    request: Request,
    review_id: int,
    review_data: ReviewUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(verify_csrf),
) -> ReviewDetailResponse:
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    if review.author_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    update_data = review_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(review, field, value)

    review.updated_at = datetime.now(UTC)

    audit = AuditLog(
        user_id=current_user.id,
        review_id=review.id,
        action=AuditAction.REVIEW_UPDATE,
        details=f"Updated review: {review.title}",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(review)

    return ReviewDetailResponse.model_validate(review)


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    request: Request,
    review_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(verify_csrf),
) -> None:
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    if review.author_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    audit = AuditLog(
        user_id=current_user.id,
        review_id=review.id,
        action=AuditAction.REVIEW_DELETE,
        details=f"Deleted review: {review.title}",
    )
    db.add(audit)
    await db.delete(review)
    await db.commit()


@router.post("/{review_id}/export", response_model=ReviewExportResponse)
async def export_review(
    request: Request,
    review_id: int,
    export_data: ReviewExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(verify_csrf),
) -> ReviewExportResponse:
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.findings))
        .where(Review.id == review_id)
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    audit = AuditLog(
        user_id=current_user.id,
        review_id=review.id,
        action=AuditAction.REVIEW_EXPORT,
        details=f"Exported review as {export_data.format}",
    )
    db.add(audit)
    await db.commit()

    if export_data.format == "json":
        import json
        data = ReviewDetailResponse.model_validate(review).model_dump(mode="json")
        return ReviewExportResponse(
            content=json.dumps(data, indent=2, default=str),
            filename=f"review-{review_id}.json",
            media_type="application/json",
        )
    elif export_data.format == "markdown":
        lines = [f"# Review: {review.title}", "", f"**Status:** {review.status.value}", f"**Repository:** {review.repository_url or 'N/A'}", f"**Branches:** {review.base_branch} → {review.head_branch}", "", "## Findings", ""]
        for f in review.findings:
            lines.append(f"### {f.title} ({f.severity.value})")
            lines.append(f"**File:** `{f.file_path}:{f.start_line}-{f.end_line}`")
            lines.append(f"**Category:** {f.category.value}")
            lines.append(f"**Description:** {f.description}")
            if f.suggestion:
                lines.append(f"**Suggestion:** {f.suggestion}")
            if f.rule_id:
                lines.append(f"**Rule:** {f.rule_id}")
            lines.append("")
        return ReviewExportResponse(
            content="\n".join(lines),
            filename=f"review-{review_id}.md",
            media_type="text/markdown",
        )
    elif export_data.format == "sarif":
        import json
        sarif = {
            "version": "2.1.0",
            "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "runs": [{
                "tool": {"driver": {"name": "Sentinel Studio", "version": settings.APP_VERSION}},
                "results": []
            }]
        }
        for f in review.findings:
            sarif["runs"][0]["results"].append({
                "ruleId": f.rule_id or "unknown",
                "message": {"text": f.description},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": f.file_path},
                        "region": {"startLine": f.start_line, "endLine": f.end_line}
                    }
                }],
                "level": {"critical": "error", "high": "error", "medium": "warning", "low": "note", "info": "note"}.get(f.severity.value, "note")
            })
        return ReviewExportResponse(
            content=json.dumps(sarif, indent=2),
            filename=f"review-{review_id}.sarif",
            media_type="application/sarif+json",
        )

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid format")


@router.post("/import", response_model=ReviewImportResponse, status_code=status.HTTP_201_CREATED)
async def import_review(
    request: Request,
    import_data: ReviewImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(verify_csrf),
) -> ReviewImportResponse:
    import json
    try:
        data = json.loads(import_data.content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON content")

    # Validate required fields
    if "title" not in data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required field: title")

    # Create review from imported data
    review = Review(
        title=data.get("title"),
        repository_url=data.get("repository_url"),
        base_branch=data.get("base_branch", "main"),
        head_branch=data.get("head_branch", "HEAD"),
        diff_content=data.get("diff_content"),
        status=ReviewStatus(data.get("status", "pending")),
        author_id=current_user.id,
    )
    db.add(review)
    await db.flush()

    # Import findings if present
    if "findings" in data and isinstance(data["findings"], list):
        for finding_data in data["findings"]:
            finding = Finding(
                review_id=review.id,
                title=finding_data.get("title", "Untitled Finding"),
                file_path=finding_data.get("file_path", ""),
                start_line=finding_data.get("start_line", 1),
                end_line=finding_data.get("end_line", 1),
                severity=FindingSeverity(finding_data.get("severity", "info")),
                category=FindingCategory(finding_data.get("category", "maintainability")),
                description=finding_data.get("description", ""),
                suggestion=finding_data.get("suggestion"),
                rule_id=finding_data.get("rule_id"),
                llm_explanation=finding_data.get("llm_explanation"),
            )
            db.add(finding)

    audit = AuditLog(
        user_id=current_user.id,
        review_id=review.id,
        action=AuditAction.REVIEW_CREATE,
        details="Imported review from JSON",
    )
    db.add(audit)
    await db.commit()

    # Reload with findings
    result = await db.execute(
        select(Review)
        .options(selectinload(Review.findings))
        .where(Review.id == review.id)
    )
    review = result.scalar_one()
    return ReviewImportResponse.model_validate(review)


@router.post("/{review_id}/findings", response_model=FindingResponse, status_code=status.HTTP_201_CREATED)
async def create_finding(
    request: Request,
    review_id: int,
    finding_data: FindingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(verify_csrf),
) -> FindingResponse:
    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    if review.author_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    finding = Finding(
        review_id=review_id,
        **finding_data.model_dump()
    )
    db.add(finding)

    # Update review counts
    review.findings_count = (review.findings_count or 0) + 1
    severity_map = {
        FindingSeverity.CRITICAL: "critical_count",
        FindingSeverity.HIGH: "high_count",
        FindingSeverity.MEDIUM: "medium_count",
        FindingSeverity.LOW: "low_count",
    }
    if finding.severity in severity_map:
        setattr(review, severity_map[finding.severity], getattr(review, severity_map[finding.severity]) + 1)

    audit = AuditLog(
        user_id=current_user.id,
        review_id=review_id,
        action=AuditAction.FINDING_CREATE,
        details=f"Added finding: {finding.title}",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(finding)

    return FindingResponse.model_validate(finding)


@router.patch("/{review_id}/findings/{finding_id}", response_model=FindingResponse)
async def update_finding(
    request: Request,
    review_id: int,
    finding_id: int,
    finding_data: FindingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(verify_csrf),
) -> FindingResponse:
    result = await db.execute(
        select(Finding).where(Finding.id == finding_id, Finding.review_id == review_id)
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    result = await db.execute(select(Review).where(Review.id == review_id))
    review = result.scalar_one_or_none()
    if review.author_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    update_data = finding_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(finding, field, value)

    audit = AuditLog(
        user_id=current_user.id,
        review_id=review_id,
        action=AuditAction.FINDING_UPDATE,
        details=f"Updated finding: {finding.title}",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(finding)

    return FindingResponse.model_validate(finding)