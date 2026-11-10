from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Any

from app.services.code_review import (
    CodeAnalyzer,
    DiffParser,
    EnhancedCodeAnalyzer,
    PythonASTAnalyzer,
    Rule,
    RulePackLoader,
    RuleSeverity,
    RuleCategory,
    analyze_python_code,
    parse_diff,
    get_default_loader,
)

router = APIRouter(prefix="/code-review", tags=["code-review"])


class AnalyzeFileRequest(BaseModel):
    file_path: str = Field(..., description="Path to the file being analyzed")
    content: str = Field(..., description="File content to analyze")
    language: str = Field(..., description="Programming language (python, javascript, typescript)")


class AnalyzeFileResponse(BaseModel):
    file_path: str
    findings: list[dict[str, Any]]
    total_findings: int


class AnalyzeDiffRequest(BaseModel):
    diff_content: str = Field(..., description="Unified diff content")
    language: str = Field(default="python", description="Programming language")


class AnalyzeDiffResponse(BaseModel):
    files: dict[str, list[dict[str, Any]]]
    total_findings: int


class RuleResponse(BaseModel):
    id: str
    name: str
    description: str
    severity: str
    category: str
    languages: list[str]
    pattern: str | None
    ast_node_type: str | None
    metadata: dict[str, Any]


class RulePackResponse(BaseModel):
    name: str
    version: str
    description: str
    rules: list[RuleResponse]
    total: int


@router.post("/analyze/file", response_model=AnalyzeFileResponse)
async def analyze_file(request: AnalyzeFileRequest) -> AnalyzeFileResponse:
    """Analyze a single file's content for security and bug patterns."""
    analyzer = EnhancedCodeAnalyzer(get_default_loader())
    findings = analyzer.analyze_file(request.file_path, request.content, request.language)
    return AnalyzeFileResponse(
        file_path=request.file_path,
        findings=[f.to_dict() for f in findings],
        total_findings=len(findings),
    )


@router.post("/analyze/diff", response_model=AnalyzeDiffResponse)
async def analyze_diff(request: AnalyzeDiffRequest) -> AnalyzeDiffResponse:
    """Analyze a unified diff for issues in added/modified lines."""
    analyzer = EnhancedCodeAnalyzer(get_default_loader())
    results = analyzer.analyze_diff(request.diff_content, request.language)

    all_findings = []
    for file_findings in results.values():
        all_findings.extend(file_findings)

    return AnalyzeDiffResponse(
        files={fp: [f.to_dict() for f in findings] for fp, findings in results.items()},
        total_findings=len(all_findings),
    )


@router.post("/analyze/python", response_model=AnalyzeFileResponse)
async def analyze_python(request: AnalyzeFileRequest) -> AnalyzeFileResponse:
    """Analyze Python code using AST-based analyzers only."""
    if request.language != "python":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint only supports Python language",
        )
    findings = analyze_python_code(request.file_path, request.content)
    return AnalyzeFileResponse(
        file_path=request.file_path,
        findings=[f.to_dict() for f in findings],
        total_findings=len(findings),
    )


@router.post("/parse-diff", response_model=dict)
async def parse_diff_endpoint(request: AnalyzeDiffRequest) -> dict:
    """Parse a unified diff and return structured hunk information."""
    parsed = parse_diff(request.diff_content)
    return {"files": parsed, "total_files": len(parsed)}


@router.get("/rules", response_model=RulePackResponse)
async def get_rules(language: str | None = None) -> RulePackResponse:
    """Get all available rules, optionally filtered by language."""
    loader = get_default_loader()
    if language:
        rules = loader.get_rules_for_language(language)
    else:
        rules = []
        for pack in loader.load_all_packs():
            rules.extend(pack.rules)
        if not rules:
            from app.services.code_review import get_default_pack
            default_pack = get_default_pack()
            rules = default_pack.rules

    return RulePackResponse(
        name="default",
        version="1.0.0",
        description="Default rule pack for common security and bug patterns",
        rules=[
            RuleResponse(
                id=r.id,
                name=r.name,
                description=r.description,
                severity=r.severity.value,
                category=r.category.value,
                languages=r.languages,
                pattern=r.pattern,
                ast_node_type=r.ast_node_type,
                metadata=r.metadata,
            )
            for r in rules
        ],
        total=len(rules),
    )

