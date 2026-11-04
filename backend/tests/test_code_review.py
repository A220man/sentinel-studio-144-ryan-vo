import pytest
from app.services.code_review import (
    Rule,
    RulePack,
    RulePackLoader,
    RuleSeverity,
    RuleCategory,
    get_default_pack,
    get_default_loader,
)


class TestRuleSeverity:
    def test_values(self):
        assert RuleSeverity.CRITICAL.value == "critical"
        assert RuleSeverity.HIGH.value == "high"
        assert RuleSeverity.MEDIUM.value == "medium"
        assert RuleSeverity.LOW.value == "low"
        assert RuleSeverity.INFO.value == "info"


class TestRuleCategory:
    def test_values(self):
        assert RuleCategory.BUG.value == "bug"
        assert RuleCategory.SECURITY.value == "security"
        assert RuleCategory.PERFORMANCE.value == "performance"
        assert RuleCategory.STYLE.value == "style"
        assert RuleCategory.MAINTAINABILITY.value == "maintainability"


class TestRule:
    def test_create_rule(self):
        rule = Rule(
            id="test-rule",
            name="Test Rule",
            description="A test rule",
            severity=RuleSeverity.HIGH,
            category=RuleCategory.SECURITY,
            languages=["python"],
            pattern=r"test",
        )
        assert rule.id == "test-rule"
        assert rule.name == "Test Rule"
        assert rule.severity == RuleSeverity.HIGH
        assert rule.category == RuleCategory.SECURITY
        assert rule.languages == ["python"]
        assert rule.pattern == r"test"

    def test_rule_to_dict(self):
        rule = Rule(
            id="test-rule",
            name="Test Rule",
            description="A test rule",
            severity=RuleSeverity.HIGH,
            category=RuleCategory.SECURITY,
            languages=["python"],
            pattern=r"test",
            message_template="Custom: {description}",
            metadata={"cwe": "CWE-123"},
        )
        data = rule.to_dict()
        assert data["id"] == "test-rule"
        assert data["severity"] == "high"
        assert data["category"] == "security"
        assert data["languages"] == ["python"]
        assert data["pattern"] == r"test"
        assert data["message_template"] == "Custom: {description}"
        assert data["metadata"] == {"cwe": "CWE-123"}

    def test_rule_from_dict(self):
        data = {
            "id": "test-rule",
            "name": "Test Rule",
            "description": "A test rule",
            "severity": "high",
            "category": "security",
            "languages": ["python"],
            "pattern": r"test",
            "message_template": "Custom: {description}",
            "metadata": {"cwe": "CWE-123"},
        }
        rule = Rule.from_dict(data)
        assert rule.id == "test-rule"
        assert rule.severity == RuleSeverity.HIGH
        assert rule.category == RuleCategory.SECURITY
        assert rule.languages == ["python"]
        assert rule.pattern == r"test"
        assert rule.message_template == "Custom: {description}"
        assert rule.metadata == {"cwe": "CWE-123"}


class TestRulePack:
    def test_create_pack(self):
        rule = Rule(
            id="test-rule",
            name="Test Rule",
            description="A test rule",
            severity=RuleSeverity.HIGH,
            category=RuleCategory.SECURITY,
            languages=["python"],
        )
        pack = RulePack(
            name="test-pack",
            version="1.0.0",
            description="Test pack",
            rules=[rule],
        )
        assert pack.name == "test-pack"
        assert pack.version == "1.0.0"
        assert len(pack.rules) == 1

    def test_pack_to_dict(self):
        rule = Rule(
            id="test-rule",
            name="Test Rule",
            description="A test rule",
            severity=RuleSeverity.HIGH,
            category=RuleCategory.SECURITY,
            languages=["python"],
        )
        pack = RulePack(
            name="test-pack",
            version="1.0.0",
            description="Test pack",
            rules=[rule],
            metadata={"author": "test"},
        )
        data = pack.to_dict()
        assert data["name"] == "test-pack"
        assert data["version"] == "1.0.0"
        assert len(data["rules"]) == 1
        assert data["metadata"] == {"author": "test"}

    def test_pack_from_dict(self):
        data = {
            "name": "test-pack",
            "version": "1.0.0",
            "description": "Test pack",
            "rules": [
                {
                    "id": "test-rule",
                    "name": "Test Rule",
                    "description": "A test rule",
                    "severity": "high",
                    "category": "security",
                    "languages": ["python"],
                }
            ],
            "metadata": {"author": "test"},
        }
        pack = RulePack.from_dict(data)
        assert pack.name == "test-pack"
        assert pack.version == "1.0.0"
        assert len(pack.rules) == 1
        assert pack.rules[0].id == "test-rule"
        assert pack.metadata == {"author": "test"}

    def test_get_rules_for_language(self):
        rule1 = Rule(
            id="python-rule",
            name="Python Rule",
            description="Python only",
            severity=RuleSeverity.HIGH,
            category=RuleCategory.SECURITY,
            languages=["python"],
        )
        rule2 = Rule(
            id="js-rule",
            name="JS Rule",
            description="JS only",
            severity=RuleSeverity.HIGH,
            category=RuleCategory.SECURITY,
            languages=["javascript"],
        )
        rule3 = Rule(
            id="both-rule",
            name="Both Rule",
            description="Both languages",
            severity=RuleSeverity.HIGH,
            category=RuleCategory.SECURITY,
            languages=["python", "javascript"],
        )
        pack = RulePack(
            name="test-pack",
            version="1.0.0",
            description="Test pack",
            rules=[rule1, rule2, rule3],
        )
        python_rules = pack.get_rules_for_language("python")
        assert len(python_rules) == 2
        assert {r.id for r in python_rules} == {"python-rule", "both-rule"}

        js_rules = pack.get_rules_for_language("javascript")
        assert len(js_rules) == 2
        assert {r.id for r in js_rules} == {"js-rule", "both-rule"}


class TestRulePackLoader:
    def test_load_default_pack(self):
        loader = get_default_loader()
        pack = get_default_pack()
        assert pack.name == "default"
        assert pack.version == "1.0.0"
        assert len(pack.rules) == 6

    def test_default_pack_has_python_rules(self):
        pack = get_default_pack()
        python_rules = pack.get_rules_for_language("python")
        assert len(python_rules) == 3
        rule_ids = {r.id for r in python_rules}
        assert "python-null-pointer" in rule_ids
        assert "python-sql-injection" in rule_ids
        assert "python-xss" in rule_ids

    def test_default_pack_has_js_rules(self):
        pack = get_default_pack()
        js_rules = pack.get_rules_for_language("javascript")
        assert len(js_rules) == 3
        rule_ids = {r.id for r in js_rules}
        assert "javascript-null-pointer" in rule_ids
        assert "javascript-sql-injection" in rule_ids
        assert "javascript-xss" in rule_ids

    def test_loader_get_rules_for_language(self):
        loader = get_default_loader()
        # Uses default pack since no rule_packs dir exists
        python_rules = loader.get_rules_for_language("python")
        assert len(python_rules) == 3
