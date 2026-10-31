import pytest
from httpx import AsyncClient
from app.models import Review, ReviewStatus, Finding, FindingSeverity, FindingCategory


@pytest.mark.asyncio
async def test_create_review(client: AsyncClient, test_user, auth_headers_with_csrf):
    review_data = {
        "title": "Test Review",
        "description": "Test description",
        "repository_url": "https://github.com/test/repo",
        "base_branch": "main",
        "head_branch": "feature/test",
    }
    response = await client.post(
        "/reviews",
        json=review_data,
        headers=auth_headers_with_csrf,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == review_data["title"]
    assert data["author_id"] == test_user.id
    assert data["status"] == "pending"
    assert data["findings"] == []


@pytest.mark.asyncio
async def test_list_reviews(client: AsyncClient, test_user, auth_headers, db_session):
    # Clean up any existing reviews for this user
    from sqlalchemy import delete
    from app.models import Review
    await db_session.execute(delete(Review).where(Review.author_id == test_user.id))
    await db_session.commit()

    # Create 3 test reviews
    reviews_to_create = []
    for i in range(3):
        review = Review(
            author_id=test_user.id,
            title=f"Review List {i}",
            base_branch="main",
            head_branch=f"feature/{i}",
            status=ReviewStatus.COMPLETED,
        )
        db_session.add(review)
        reviews_to_create.append(review)
    await db_session.commit()
    for r in reviews_to_create:
        await db_session.refresh(r)

    response = await client.get("/reviews", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3


@pytest.mark.asyncio
async def test_get_review(client: AsyncClient, test_user, auth_headers, db_session):
    review = Review(
        author_id=test_user.id,
        title="Test Review",
        base_branch="main",
        head_branch="feature/test",
        status=ReviewStatus.COMPLETED,
    )
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)

    response = await client.get(f"/reviews/{review.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == review.id
    assert data["title"] == "Test Review"


@pytest.mark.asyncio
async def test_get_nonexistent_review(client: AsyncClient, auth_headers):
    response = await client.get("/reviews/99999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_review(client: AsyncClient, test_user, auth_headers_with_csrf, db_session):
    review = Review(
        author_id=test_user.id,
        title="Original Title",
        base_branch="main",
        head_branch="feature/test",
    )
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)

    response = await client.patch(
        f"/reviews/{review.id}",
        json={"title": "Updated Title", "status": "in_progress"},
        headers=auth_headers_with_csrf,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["status"] == "in_progress"


@pytest.mark.asyncio
async def test_delete_review(client: AsyncClient, test_user, auth_headers_with_csrf, db_session):
    review = Review(
        author_id=test_user.id,
        title="To Delete",
        base_branch="main",
        head_branch="feature/test",
    )
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)

    response = await client.delete(f"/reviews/{review.id}", headers=auth_headers_with_csrf)
    assert response.status_code == 204

    # Verify deleted
    response = await client.get(f"/reviews/{review.id}", headers=auth_headers_with_csrf)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_export_review_json(client: AsyncClient, test_user, auth_headers_with_csrf, db_session):
    review = Review(
        author_id=test_user.id,
        title="Export Test",
        base_branch="main",
        head_branch="feature/test",
        status=ReviewStatus.COMPLETED,
    )
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)

    finding = Finding(
        review_id=review.id,
        file_path="src/main.py",
        start_line=10,
        end_line=20,
        severity=FindingSeverity.HIGH,
        category=FindingCategory.BUG,
        title="Null pointer risk",
        description="Possible NPE at line 15",
    )
    db_session.add(finding)
    await db_session.commit()

    response = await client.post(
        f"/reviews/{review.id}/export",
        json={"review_id": review.id, "format": "json"},
        headers=auth_headers_with_csrf,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["media_type"] == "application/json"
    assert "Export Test" in data["content"]


@pytest.mark.asyncio
async def test_export_review_markdown(client: AsyncClient, test_user, auth_headers_with_csrf, db_session):
    review = Review(
        author_id=test_user.id,
        title="Export Test",
        base_branch="main",
        head_branch="feature/test",
    )
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)

    response = await client.post(
        f"/reviews/{review.id}/export",
        json={"review_id": review.id, "format": "markdown"},
        headers=auth_headers_with_csrf,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["media_type"] == "text/markdown"
    assert "Export Test" in data["content"]


@pytest.mark.asyncio
async def test_create_finding(client: AsyncClient, test_user, auth_headers_with_csrf, db_session):
    review = Review(
        author_id=test_user.id,
        title="Finding Test",
        base_branch="main",
        head_branch="feature/test",
    )
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)

    finding_data = {
        "file_path": "src/auth.py",
        "start_line": 50,
        "end_line": 55,
        "severity": "critical",
        "category": "security",
        "title": "SQL Injection",
        "description": "User input directly concatenated",
        "suggestion": "Use parameterized queries",
        "rule_id": "SQLI-001",
    }
    response = await client.post(
        f"/reviews/{review.id}/findings",
        json=finding_data,
        headers=auth_headers_with_csrf,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == finding_data["title"]
    assert data["severity"] == "critical"
    assert data["review_id"] == review.id


@pytest.mark.asyncio
async def test_import_review(client: AsyncClient, test_user, auth_headers_with_csrf, db_session):
    # Create a review to export first
    from app.models import Finding, FindingSeverity, FindingCategory
    review = Review(
        author_id=test_user.id,
        title="Original Review",
        base_branch="main",
        head_branch="feature/test",
        repository_url="https://github.com/test/repo",
    )
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)

    finding = Finding(
        review_id=review.id,
        title="Test Finding",
        file_path="src/main.py",
        start_line=10,
        end_line=20,
        severity=FindingSeverity.HIGH,
        category=FindingCategory.BUG,
        description="A test finding",
        suggestion="Fix it",
        rule_id="TEST-001",
    )
    db_session.add(finding)
    await db_session.commit()

    # Export the review as JSON
    export_response = await client.post(
        f"/reviews/{review.id}/export",
        json={"review_id": review.id, "format": "json"},
        headers=auth_headers_with_csrf,
    )
    assert export_response.status_code == 200
    export_data = export_response.json()

    # Import the review
    import_response = await client.post(
        "/reviews/import",
        json={"content": export_data["content"], "format": "json"},
        headers=auth_headers_with_csrf,
    )
    assert import_response.status_code == 201
    data = import_response.json()
    assert data["title"] == "Original Review"
    assert data["repository_url"] == "https://github.com/test/repo"
    assert len(data["findings"]) == 1
    assert data["findings"][0]["title"] == "Test Finding"
    assert data["findings"][0]["severity"] == "high"
    assert data["author_id"] == test_user.id


@pytest.mark.asyncio
async def test_import_review_invalid_json(client: AsyncClient, auth_headers_with_csrf):
    import_response = await client.post(
        "/reviews/import",
        json={"content": "not valid json", "format": "json"},
        headers=auth_headers_with_csrf,
    )
    assert import_response.status_code == 400
    assert "Invalid JSON" in import_response.json()["detail"]


@pytest.mark.asyncio
async def test_import_review_missing_title(client: AsyncClient, auth_headers_with_csrf):
    import_response = await client.post(
        "/reviews/import",
        json={"content": '{"repository_url": "https://github.com/test/repo"}', "format": "json"},
        headers=auth_headers_with_csrf,
    )
    assert import_response.status_code == 400
    assert "Missing required field: title" in import_response.json()["detail"]