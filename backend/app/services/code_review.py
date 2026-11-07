import re

import json
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional


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
            "rules": [rule.to_dict() for rule in self.rules],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RulePack:
        return cls(
            name=data["name"],
            version=data["version"],
            description=data["description"],
            rules=[Rule.from_dict(r) for r in data.get("rules", [])],
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
        all_rules = []
        for pack in self.load_all_packs():
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
