"""Tests for the prompt templates and prompt management module."""

from __future__ import annotations

import pytest

from blhackbox.prompts import (
    TEMPLATES,
    list_templates,
    load_playbook,
    load_template,
)


class TestLoadTemplate:
    """Test loading individual templates."""

    def test_load_known_template(self) -> None:
        content = load_template("quick-scan")
        assert "# Quick Scan" in content
        assert "[TARGET]" in content

    def test_load_with_target_replacement(self) -> None:
        content = load_template("quick-scan", target="example.com")
        assert "example.com" in content
        assert "[TARGET]" not in content

    def test_load_unknown_template_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown template"):
            load_template("nonexistent-template")

    def test_all_registered_templates_load(self) -> None:
        for name in TEMPLATES:
            content = load_template(name)
            assert len(content) > 100, f"Template {name} seems too short"

    def test_all_templates_have_data_processing_step(self) -> None:
        for name in TEMPLATES:
            content = load_template(name)
            assert "REQUIRED" in content or "mandatory" in content, (
                f"Template {name} missing mandatory data processing step"
            )

    def test_all_templates_mention_aggregation_pipeline(self) -> None:
        for name in TEMPLATES:
            content = load_template(name)
            assert "aggregate_results" in content or "AggregatedPayload" in content, (
                f"Template {name} does not reference data aggregation pipeline"
            )

    def test_all_templates_have_placeholder_section(self) -> None:
        for name in TEMPLATES:
            content = load_template(name)
            assert "Configuration" in content or "Edit These Placeholders" in content, (
                f"Template {name} missing placeholder configuration section"
            )


class TestListTemplates:
    """Test listing available templates."""

    def test_returns_list(self) -> None:
        templates = list_templates()
        assert isinstance(templates, list)

    def test_contains_expected_count(self) -> None:
        templates = list_templates()
        assert len(templates) == len(TEMPLATES)

    def test_entries_have_required_keys(self) -> None:
        templates = list_templates()
        for tpl in templates:
            assert "name" in tpl
            assert "file" in tpl
            assert "title" in tpl

    def test_titles_not_empty(self) -> None:
        templates = list_templates()
        for tpl in templates:
            assert tpl["title"], f"Template {tpl['name']} has empty title"

    def test_known_templates_present(self) -> None:
        templates = list_templates()
        names = {t["name"] for t in templates}
        assert "full-pentest" in names
        assert "full-attack-chain" in names
        assert "quick-scan" in names
        assert "bug-bounty" in names



class TestLoadPlaybook:
    """Test loading the Claude playbook."""

    def test_playbook_loads(self) -> None:
        content = load_playbook()
        assert "Blhackbox Pentest Playbook" in content

    def test_playbook_references_templates(self) -> None:
        content = load_playbook()
        assert "Prompt Templates" in content
        assert "full-pentest" in content
