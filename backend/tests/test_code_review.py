import pytest
from app.services.code_review import (
    Rule,
    RulePack,
    RulePackLoader,
    RuleSeverity,
    RuleCategory,
    AnalysisFinding,
    PythonASTAnalyzer,
    DiffParser,
    EnhancedCodeAnalyzer,
    analyze_python_code,
    parse_diff,
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
            category=RuleCategory.BUG,
            languages=["python"],
            pattern=r"test",
        )
        assert rule.id == "test-rule"
        assert rule.name == "Test Rule"
        assert rule.pattern == r"test"

    def test_rule_to_dict(self):
        rule = Rule(
            id="test-rule",
            name="Test Rule",
            description="A test rule",
            severity=RuleSeverity.HIGH,
            category=RuleCategory.BUG,
            languages=["python"],
            pattern=r"test",
            metadata={"cwe": "CWE-123"},
        )
        data = rule.to_dict()
        assert data["id"] == "test-rule"
        assert data["severity"] == "high"
        assert data["category"] == "bug"
        assert data["metadata"] == {"cwe": "CWE-123"}

    def test_rule_from_dict(self):
        data = {
            "id": "test-rule",
            "name": "Test Rule",
            "description": "A test rule",
            "severity": "high",
            "category": "bug",
            "languages": ["python"],
            "pattern": r"test",
            "metadata": {"cwe": "CWE-123"},
        }
        rule = Rule.from_dict(data)
        assert rule.id == "test-rule"
        assert rule.severity == RuleSeverity.HIGH
        assert rule.category == RuleCategory.BUG
        assert rule.metadata == {"cwe": "CWE-123"}


class TestRulePack:
    def test_create_pack(self):
        rule = Rule(
            id="test-rule",
            name="Test Rule",
            description="A test rule",
            severity=RuleSeverity.HIGH,
            category=RuleCategory.BUG,
            languages=["python"],
        )
        pack = RulePack(
            name="test-pack",
            version="1.0.0",
            description="Test pack",
            rules=[rule],
        )
        assert pack.name == "test-pack"
        assert len(pack.rules) == 1

    def test_pack_to_dict(self):
        rule = Rule(
            id="test-rule",
            name="Test Rule",
            description="A test rule",
            severity=RuleSeverity.HIGH,
            category=RuleCategory.BUG,
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
                    "category": "bug",
                    "languages": ["python"],
                }
            ],
            "metadata": {"author": "test"},
        }
        pack = RulePack.from_dict(data)
        assert pack.name == "test-pack"
        assert len(pack.rules) == 1
        assert pack.rules[0].id == "test-rule"
        assert pack.metadata == {"author": "test"}

    def test_get_rules_for_language(self):
        rule1 = Rule(id="python-rule", name="Python Rule", description="", severity=RuleSeverity.HIGH, category=RuleCategory.BUG, languages=["python"])
        rule2 = Rule(id="js-rule", name="JS Rule", description="", severity=RuleSeverity.HIGH, category=RuleCategory.BUG, languages=["javascript"])
        rule3 = Rule(id="both-rule", name="Both Rule", description="", severity=RuleSeverity.HIGH, category=RuleCategory.BUG, languages=["python", "javascript"])
        pack = RulePack(name="test", version="1.0", description="", rules=[rule1, rule2, rule3])

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
        python_rules = loader.get_rules_for_language("python")
        assert len(python_rules) == 3


class TestPythonASTAnalyzer:
    def test_detects_sql_injection_fstring(self):
        code = '''
def get_user(cursor, user_id):
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
'''
        analyzer = PythonASTAnalyzer("test.py", code)
        findings = analyzer.analyze()
        assert len(findings) >= 1
        assert any(f.rule_id == "python-sql-injection-ast" for f in findings)

    def test_detects_sql_injection_format(self):
        code = '''
def get_user(cursor, user_id):
    cursor.execute("SELECT * FROM users WHERE id = {}".format(user_id))
'''
        analyzer = PythonASTAnalyzer("test.py", code)
        findings = analyzer.analyze()
        assert len(findings) >= 1
        assert any(f.rule_id == "python-sql-injection-ast" for f in findings)

    def test_detects_xss_render_template_string(self):
        code = '''
from flask import render_template_string
def hello(name):
    return render_template_string(f"Hello {name}")
'''
        analyzer = PythonASTAnalyzer("test.py", code)
        findings = analyzer.analyze()
        assert len(findings) >= 1
        assert any(f.rule_id == "python-xss-ast" for f in findings)

    def test_detects_thread_safety_lambda(self):
        code = '''
import threading
for i in range(10):
    t = threading.Thread(target=lambda: print(i))
    t.start()
'''
        analyzer = PythonASTAnalyzer("test.py", code)
        findings = analyzer.analyze()
        assert len(findings) >= 1
        assert any(f.rule_id == "python-thread-safety-ast" for f in findings)

    def test_clean_code_no_findings(self):
        code = '''
def add(a, b):
    return a + b

class Calculator:
    def multiply(self, x, y):
        return x * y
'''
        analyzer = PythonASTAnalyzer("test.py", code)
        findings = analyzer.analyze()
        assert len(findings) == 0

    def test_invalid_syntax_handled_gracefully(self):
        code = "def invalid syntax:"
        analyzer = PythonASTAnalyzer("test.py", code)
        findings = analyzer.analyze()
        assert findings == []


class TestDiffParser:
    def test_parse_simple_diff(self):
        diff = '''--- a/test.py
+++ b/test.py
@@ -1,4 +1,5 @@
 def hello():
+    print("added")
     return "world"
+
+    print("more")
'''
        parsed = DiffParser.parse_diff(diff)
        assert "test.py" in parsed
        assert len(parsed["test.py"]) == 1
        hunk = parsed["test.py"][0]
        assert hunk["old_start"] == 1
        assert hunk["old_count"] == 4
        assert hunk["new_start"] == 1
        assert hunk["new_count"] == 5
        assert len(hunk["lines"]) == 5
        types = [l["type"] for l in hunk["lines"]]
        assert "context" in types
        assert "add" in types

    def test_parse_multiple_hunks(self):
        diff = '''--- a/test.py
+++ b/test.py
@@ -1,4 +1,5 @@
 def hello():
+    print("added")
     return "world"
+
+    print("more")
@@ -10,3 +11,4 @@
 def goodbye():
+    print("bye")
     return "farewell"
+
'''
        parsed = DiffParser.parse_diff(diff)
        assert len(parsed["test.py"]) == 2

    def test_parse_multiple_files(self):
        diff = '''--- a/file1.py
+++ b/file1.py
@@ -1,1 +1,2 @@
+print("file1")
--- a/file2.py
+++ b/file2.py
@@ -1,1 +1,2 @@
+print("file2")
'''
        parsed = DiffParser.parse_diff(diff)
        assert "file1.py" in parsed
        assert "file2.py" in parsed

    def test_map_findings_to_diff(self):
        diff = '''--- a/test.py
+++ b/test.py
@@ -1,4 +1,5 @@
 def hello():
+    print("added")
     return "world"
+
+    print("more")
'''
        findings = [
            AnalysisFinding(
                rule_id="test",
                rule_name="Test",
                description="Test finding",
                severity=RuleSeverity.HIGH,
                category=RuleCategory.BUG,
                file_path="test.py",
                line_start=2,
                line_end=2,
                matched_text='print("added")',
                message="Test",
                metadata={},
            ),
            AnalysisFinding(
                rule_id="test",
                rule_name="Test",
                description="Test finding",
                severity=RuleSeverity.HIGH,
                category=RuleCategory.BUG,
                file_path="test.py",
                line_start=3,
                line_end=3,
                matched_text='return "world"',
                message="Test",
                metadata={},
            ),
        ]
        mapped = DiffParser.map_findings_to_diff(findings, diff)
        assert len(mapped) == 1
        assert mapped[0].line_start == 2


class TestEnhancedCodeAnalyzer:
    def test_analyze_python_with_ast(self):
        code = '''
def get_user(cursor, user_id):
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
'''
        analyzer = EnhancedCodeAnalyzer(get_default_loader())
        findings = analyzer.analyze_file("test.py", code, "python")
        rule_ids = {f.rule_id for f in findings}
        assert "python-sql-injection" in rule_ids
        assert "python-sql-injection-ast" in rule_ids

    def test_analyze_diff(self):
        diff = '''--- a/test.py
+++ b/test.py
@@ -1,4 +1,5 @@
 def get_user(cursor, user_id):
+    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
     return "world"
+
+    print("done")
'''
        analyzer = EnhancedCodeAnalyzer(get_default_loader())
        results = analyzer.analyze_diff(diff, "python")
        assert "test.py" in results
        findings = results["test.py"]
        rule_ids = {f.rule_id for f in findings}
        assert "python-sql-injection-ast" in rule_ids


class TestConvenienceFunctions:
    def test_analyze_python_code(self):
        code = 'cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")'
        findings = analyze_python_code("test.py", code)
        assert len(findings) >= 1
        assert any(f.rule_id == "python-sql-injection-ast" for f in findings)

    def test_parse_diff_function(self):
        diff = '''--- a/test.py
+++ b/test.py
@@ -1,1 +1,2 @@
+print("hello")
'''
        parsed = parse_diff(diff)
        assert "test.py" in parsed
        assert len(parsed["test.py"]) == 1
