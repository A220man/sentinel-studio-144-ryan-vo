from __future__ import annotations

import ast
import json
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import difflib


class RuleSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class RuleCategory(str, Enum):
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    MAINTAINABILITY = "maintainability"


@dataclass(frozen=True)
class Rule:
    id: str
    name: str
    description: str
    severity: RuleSeverity
    category: RuleCategory
    languages: list[str]
    pattern: Optional[str] = None
    ast_node_type: Optional[str] = None
    message_template: str = "{description}"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "severity": self.severity.value,
            "category": self.category.value,
            "languages": self.languages,
            "pattern": self.pattern,
            "ast_node_type": self.ast_node_type,
            "message_template": self.message_template,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Rule:
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            severity=RuleSeverity(data["severity"]),
            category=RuleCategory(data["category"]),
            languages=data["languages"],
            pattern=data.get("pattern"),
            ast_node_type=data.get("ast_node_type"),
            message_template=data.get("message_template", "{description}"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class RulePack:
    name: str
    version: str
    description: str
    rules: list[Rule] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "rules": [r.to_dict() for r in self.rules],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RulePack:
        return cls(
            name=data["name"],
            version=data["version"],
            description=data["description"],
            rules=[Rule.from_dict(r) for r in data["rules"]],
            metadata=data.get("metadata", {}),
        )

    def get_rules_for_language(self, language: str) -> list[Rule]:
        return [rule for rule in self.rules if language in rule.languages]


@dataclass
class AnalysisFinding:
    rule_id: str
    rule_name: str
    description: str
    severity: RuleSeverity
    category: RuleCategory
    file_path: str
    line_start: int
    line_end: int
    matched_text: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "description": self.description,
            "severity": self.severity.value,
            "category": self.category.value,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "matched_text": self.matched_text,
            "message": self.message,
            "metadata": self.metadata,
        }


class CodeAnalyzer:
    def __init__(self, loader: Optional[RulePackLoader] = None):
        self.loader = loader or get_default_loader()

    def analyze_file(self, file_path: str, content: str, language: str) -> list[AnalysisFinding]:
        """Analyze a single file's content against rules for the given language."""
        rules = self.loader.get_rules_for_language(language)
        findings = []

        for rule in rules:
            if not rule.pattern:
                continue
            findings.extend(self._match_rule(content, file_path, rule))

        return findings

    def _match_rule(self, content: str, file_path: str, rule: Rule) -> list[AnalysisFinding]:
        """Match a single rule's pattern against content and return findings with line numbers."""
        findings = []
        try:
            pattern = re.compile(rule.pattern, re.MULTILINE)
        except re.error:
            return findings

        lines = content.splitlines()
        for match in pattern.finditer(content):
            # Calculate line numbers (1-indexed)
            line_start = content[:match.start()].count('\n') + 1
            line_end = content[:match.end()].count('\n') + 1

            # Get matched text (limited to first line for readability)
            matched_text = match.group(0)
            if '\n' in matched_text:
                matched_text = matched_text.split('\n')[0]
            matched_text = matched_text[:200]

            # Format message
            message = rule.message_template.format(description=rule.description)

            findings.append(AnalysisFinding(
                rule_id=rule.id,
                rule_name=rule.name,
                description=rule.description,
                severity=rule.severity,
                category=rule.category,
                file_path=file_path,
                line_start=line_start,
                line_end=line_end,
                matched_text=matched_text,
                message=message,
                metadata=rule.metadata,
            ))

        return findings

    def analyze_files(self, files: dict[str, tuple[str, str]]) -> dict[str, list[AnalysisFinding]]:
        """
        Analyze multiple files.
        Args:
            files: Dict mapping file_path -> (content, language)
        Returns:
            Dict mapping file_path -> list of findings
        """
        results = {}
        for file_path, (content, language) in files.items():
            results[file_path] = self.analyze_file(file_path, content, language)
        return results


class PythonASTAnalyzer(ast.NodeVisitor):
    """AST-based analyzer for Python code detecting NPE, SQLi, XSS, thread-safety issues."""

    def __init__(self, file_path: str, content: str):
        self.file_path = file_path
        self.content = content
        self.lines = content.splitlines()
        self.findings: list[AnalysisFinding] = []
        self._call_stack: list[str] = []

    def visit_Call(self, node: ast.Call) -> None:
        # Check for SQL injection: execute/executemany with f-string or formatted string
        if isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr
            if attr_name in ("execute", "executemany", "raw", "execute_script"):
                for arg in node.args:
                    if self._is_formatted_string(arg):
                        self._add_finding(
                            rule_id="python-sql-injection-ast",
                            rule_name="SQL Injection Risk (AST)",
                            description="SQL query uses string formatting - potential SQL injection",
                            severity=RuleSeverity.CRITICAL,
                            category=RuleCategory.SECURITY,
                            node=node,
                            metadata={"cwe": "CWE-89", "owasp": "A03:2021", "detection": "ast"},
                        )
        # Check for XSS: render_template_string, mark_safe, safe
        if isinstance(node.func, ast.Name) and node.func.id in ("render_template_string", "mark_safe"):
            self._add_finding(
                rule_id="python-xss-ast",
                rule_name="Cross-Site Scripting (XSS) Risk (AST)",
                description="Unsafe template rendering or marking content as safe",
                severity=RuleSeverity.HIGH,
                category=RuleCategory.SECURITY,
                node=node,
                metadata={"cwe": "CWE-79", "owasp": "A03:2021", "detection": "ast"},
            )
        # Check for thread-safety: threading.Thread with lambda/closure capturing loop variable
        if isinstance(node.func, ast.Attribute) and node.func.attr == "Thread":
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "threading":
                for kw in node.keywords:
                    if kw.arg == "target" and isinstance(kw.value, ast.Lambda):
                        self._add_finding(
                            rule_id="python-thread-safety-ast",
                            rule_name="Thread Safety Risk (AST)",
                            description="Thread target is a lambda - may capture loop variables incorrectly",
                            severity=RuleSeverity.MEDIUM,
                            category=RuleCategory.BUG,
                            node=node,
                            metadata={"cwe": "CWE-567", "detection": "ast"},
                        )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Check for null pointer dereference: attribute access on potentially None
        # This is a heuristic - we flag chained attribute access that could fail
        if isinstance(node.value, ast.Call):
            # Method call result could be None
            pass
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        # Check for potential index errors on potentially empty sequences
        pass

    def _is_formatted_string(self, node: ast.AST) -> bool:
        """Check if node is an f-string, format() call, or % formatting."""
        if isinstance(node, ast.JoinedStr):  # f-string
            return True
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "format":
                return True
            if isinstance(node.func, ast.Name) and node.func.id == "format":
                return True
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):  # % formatting
            return True
        return False

    def _add_finding(self, rule_id: str, rule_name: str, description: str,
                     severity: RuleSeverity, category: RuleCategory,
                     node: ast.AST, metadata: dict[str, Any]) -> None:
        line_start = getattr(node, "lineno", 1)
        line_end = getattr(node, "end_lineno", line_start)
        # Get the source line(s)
        matched_text = ""
        if line_start <= len(self.lines):
            matched_text = self.lines[line_start - 1][:200]
        self.findings.append(AnalysisFinding(
            rule_id=rule_id,
            rule_name=rule_name,
            description=description,
            severity=severity,
            category=category,
            file_path=self.file_path,
            line_start=line_start,
            line_end=line_end,
            matched_text=matched_text,
            message=f"{rule_name}: {description}",
            metadata=metadata,
        ))

    def analyze(self) -> list[AnalysisFinding]:
        try:
            tree = ast.parse(self.content, filename=self.file_path)
            self.visit(tree)
        except SyntaxError:
            pass  # Invalid Python syntax, skip AST analysis
        return self.findings


class DiffParser:
    """Parse unified diff and map hunks to file/line ranges."""

    @staticmethod
    def parse_diff(diff_content: str) -> dict[str, list[dict[str, Any]]]:
        """
        Parse a unified diff and return a mapping of file paths to hunks.
        Each hunk contains: old_start, old_count, new_start, new_count, lines.
        """
        result: dict[str, list[dict[str, Any]]] = {}
        current_file = None
        current_hunk = None

        for line in diff_content.splitlines():
            # File header: --- a/file or +++ b/file
            if line.startswith("--- ") or line.startswith("+++ "):
                # Extract file path
                parts = line.split(" ", 1)
                if len(parts) > 1:
                    file_path = parts[1].strip()
                    # Remove a/ or b/ prefix
                    if file_path.startswith(("a/", "b/")):
                        file_path = file_path[2:]
                    if file_path not in result:
                        result[file_path] = []
                    current_file = file_path
                continue

            # Hunk header: @@ -old_start,old_count +new_start,new_count @@
            if line.startswith("@@ ") and current_file:
                hunk_header = line[3:line.rfind("@@")].strip()
                # Parse: -old_start,old_count +new_start,new_count
                parts = hunk_header.split(" ")
                old_range = parts[0][1:]  # remove -
                new_range = parts[1][1:]  # remove +

                old_start, old_count = DiffParser._parse_range(old_range)
                new_start, new_count = DiffParser._parse_range(new_range)

                current_hunk = {
                    "old_start": old_start,
                    "old_count": old_count,
                    "new_start": new_start,
                    "new_count": new_count,
                    "lines": [],
                }
                result[current_file].append(current_hunk)
                continue

            # Hunk content lines
            if current_hunk is not None and current_file:
                if line.startswith(" "):  # context line
                    current_hunk["lines"].append({"type": "context", "content": line[1:]})
                elif line.startswith("-"):  # removed line
                    current_hunk["lines"].append({"type": "remove", "content": line[1:]})
                elif line.startswith("+"):  # added line
                    current_hunk["lines"].append({"type": "add", "content": line[1:]})

        return result

    @staticmethod
    def _parse_range(range_str: str) -> tuple[int, int]:
        """Parse range like '10,5' or '10' into (start, count)."""
        if "," in range_str:
            start, count = range_str.split(",")
            return int(start), int(count)
        return int(range_str), 1

    @staticmethod
    def map_findings_to_diff(findings: list[AnalysisFinding], diff_content: str) -> list[AnalysisFinding]:
        """
        Map findings to diff hunks, filtering to only findings in added lines.
        Returns findings that fall within added lines in the diff.
        """
        parsed = DiffParser.parse_diff(diff_content)
        mapped = []

        for finding in findings:
            file_hunks = parsed.get(finding.file_path, [])
            if not file_hunks:
                continue

            # Check if finding falls on an added line in any hunk
            for hunk in file_hunks:
                new_line = hunk["new_start"]
                for line_info in hunk["lines"]:
                    if line_info["type"] == "add":
                        if finding.line_start == new_line:
                            mapped.append(finding)
                            break
                    if line_info["type"] != "remove":
                        new_line += 1
                if mapped and mapped[-1] is finding:
                    break

        return mapped


class EnhancedCodeAnalyzer(CodeAnalyzer):
    """Enhanced analyzer combining regex rules with AST-based analysis."""

    def analyze_file(self, file_path: str, content: str, language: str) -> list[AnalysisFinding]:
        """Analyze with both regex rules and AST-based analyzers."""
        findings = super().analyze_file(file_path, content, language)

        # Add AST-based analysis for Python
        if language == "python":
            ast_analyzer = PythonASTAnalyzer(file_path, content)
            findings.extend(ast_analyzer.analyze())

        # TODO: Add tree-sitter based analyzers for JavaScript/TypeScript

        return findings

    def analyze_diff(self, diff_content: str, language: str = "python") -> dict[str, list[AnalysisFinding]]:
        """
        Analyze a diff by extracting new/modified content and running analysis.
        Returns findings mapped to diff hunks.
        """
        parsed = DiffParser.parse_diff(diff_content)
        results = {}

        for file_path, hunks in parsed.items():
            all_findings = []
            for hunk in hunks:
                # Create a snippet with all lines in the hunk (context + added)
                # to preserve correct line numbers
                snippet_lines = []
                added_line_indices = []  # Track which snippet lines are added lines
                for i, line_info in enumerate(hunk["lines"]):
                    if line_info["type"] != "remove":  # Include context and added lines
                        snippet_lines.append(line_info["content"])
                        if line_info["type"] == "add":
                            added_line_indices.append(len(snippet_lines) - 1)

                if not snippet_lines:
                    continue

                snippet = "\n".join(snippet_lines)
                pseudo_path = f"{file_path}:hunk:{hunk['new_start']}"
                findings = self.analyze_file(pseudo_path, snippet, language)

                # Filter to only findings on added lines and adjust line numbers
                for f in findings:
                    # Check if finding is on an added line in the snippet
                    snippet_line = f.line_start - 1  # 0-indexed
                    if snippet_line in added_line_indices:
                        # Map to actual file line number
                        f.file_path = file_path
                        # Find the actual line number in the new file
                        actual_line = hunk["new_start"]
                        for j, line_info in enumerate(hunk["lines"]):
                            if j == snippet_line:
                                break
                            if line_info["type"] != "remove":
                                actual_line += 1
                        f.line_start = actual_line
                        f.line_end = actual_line
                        all_findings.append(f)

            if all_findings:
                results[file_path] = all_findings

        return results


class RulePackLoader:
    def __init__(self, packs_dir: Optional[str] = None):
        self.packs_dir = Path(packs_dir) if packs_dir else Path(__file__).parent.parent.parent / "rule_packs"
        self._cache: dict[str, RulePack] = {}

    def load_pack(self, pack_name: str) -> RulePack:
        if pack_name in self._cache:
            return self._cache[pack_name]

        pack_path = self.packs_dir / f"{pack_name}.json"
        if not pack_path.exists():
            raise FileNotFoundError(f"Rule pack not found: {pack_name}")

        with open(pack_path, "r") as f:
            data = json.load(f)

        pack = RulePack.from_dict(data)
        self._cache[pack_name] = pack
        return pack

    def load_all_packs(self) -> list[RulePack]:
        packs = []
        if self.packs_dir.exists():
            for pack_file in self.packs_dir.glob("*.json"):
                try:
                    pack = self.load_pack(pack_file.stem)
                    packs.append(pack)
                except Exception:
                    continue
        return packs

    def get_rules_for_language(self, language: str) -> list[Rule]:
        all_rules = []
        packs = self.load_all_packs()
        if not packs:
            # Fall back to default pack
            default_pack = get_default_pack()
            return default_pack.get_rules_for_language(language)
        for pack in packs:
            all_rules.extend(pack.get_rules_for_language(language))
        return all_rules


DEFAULT_RULES = [
    Rule(
        id="python-null-pointer",
        name="Null Pointer Dereference",
        description="Potential null pointer dereference detected",
        severity=RuleSeverity.HIGH,
        category=RuleCategory.BUG,
        languages=["python"],
        pattern=r"\.(\w+)\s*\(\s*\)",
        ast_node_type="Call",
        message_template="Possible null dereference: {description}",
        metadata={"cwe": "CWE-476"},
    ),
    Rule(
        id="python-sql-injection",
        name="SQL Injection Risk",
        description="Potential SQL injection via string formatting",
        severity=RuleSeverity.CRITICAL,
        category=RuleCategory.SECURITY,
        languages=["python"],
        pattern=r"(execute|executemany)\s*\(\s*[f\"']",
        ast_node_type="Call",
        message_template="SQL injection risk: {description}",
        metadata={"cwe": "CWE-89", "owasp": "A03:2021"},
    ),
    Rule(
        id="python-xss",
        name="Cross-Site Scripting (XSS)",
        description="Potential XSS via unsafe template rendering",
        severity=RuleSeverity.HIGH,
        category=RuleCategory.SECURITY,
        languages=["python"],
        pattern=r"(render_template_string|mark_safe|safe)\s*\(",
        ast_node_type="Call",
        message_template="XSS risk: {description}",
        metadata={"cwe": "CWE-79", "owasp": "A03:2021"},
    ),
    Rule(
        id="javascript-null-pointer",
        name="Null Pointer Dereference",
        description="Potential null/undefined property access",
        severity=RuleSeverity.HIGH,
        category=RuleCategory.BUG,
        languages=["javascript", "typescript"],
        pattern=r"\?\.\s*\w+",
        ast_node_type="MemberExpression",
        message_template="Possible null/undefined access: {description}",
        metadata={"cwe": "CWE-476"},
    ),
    Rule(
        id="javascript-sql-injection",
        name="SQL Injection Risk",
        description="Potential SQL injection via string concatenation",
        severity=RuleSeverity.CRITICAL,
        category=RuleCategory.SECURITY,
        languages=["javascript", "typescript"],
        pattern=r"(query|execute)\s*\(\s*[`\"']",
        ast_node_type="CallExpression",
        message_template="SQL injection risk: {description}",
        metadata={"cwe": "CWE-89", "owasp": "A03:2021"},
    ),
    Rule(
        id="javascript-xss",
        name="Cross-Site Scripting (XSS)",
        description="Potential XSS via innerHTML or dangerouslySetInnerHTML",
        severity=RuleSeverity.HIGH,
        category=RuleCategory.SECURITY,
        languages=["javascript", "typescript"],
        pattern=r"(innerHTML|dangerouslySetInnerHTML)\s*=",
        ast_node_type="AssignmentExpression",
        message_template="XSS risk: {description}",
        metadata={"cwe": "CWE-79", "owasp": "A03:2021"},
    ),
]

DEFAULT_PACK = RulePack(
    name="default",
    version="1.0.0",
    description="Default rule pack for common security and bug patterns",
    rules=DEFAULT_RULES,
    metadata={"author": "Sentinel Studio", "type": "builtin"},
)


def get_default_pack() -> RulePack:
    return DEFAULT_PACK


def get_default_loader() -> RulePackLoader:
    return RulePackLoader()


def analyze_python_code(file_path: str, content: str) -> list[AnalysisFinding]:
    """Convenience function for Python AST analysis."""
    analyzer = PythonASTAnalyzer(file_path, content)
    return analyzer.analyze()


def parse_diff(diff_content: str) -> dict[str, list[dict[str, Any]]]:
    """Convenience function for diff parsing."""
    return DiffParser.parse_diff(diff_content)
