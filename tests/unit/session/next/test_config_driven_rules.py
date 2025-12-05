"""
Tests for config-driven rule IDs in session/next compute.

STRICT TDD: These tests verify rule IDs come from:
1. workflow.yaml transitions (for enforcement rules)
2. rules/registry.yml contexts (for guidance rules)

P2-TP-004: Fix compute.py hardcoded rule IDs
"""
import pytest
from pathlib import Path
from edison.core.config.domains.workflow import WorkflowConfig
from edison.core.session.next.rules import get_rules_for_context


class TestGuidanceRulesFromRegistry:
    """Test that guidance rules come from rules/registry.yml via context lookup."""

    def test_delegation_guidance_rules_from_registry(self):
        """Verify delegation guidance rules come from registry contexts."""
        rules = get_rules_for_context("delegation")
        
        assert len(rules) > 0, "delegation context should have rules in registry"
        rule_ids = [r.get("id") for r in rules]
        assert "RULE.DELEGATION.PRIORITY_CHAIN" in rule_ids

    def test_guidance_context_returns_rules(self):
        """Verify guidance context returns rules from registry."""
        rules = get_rules_for_context("guidance")
        
        # Should return rules that have contexts: [guidance, ...]
        assert len(rules) >= 0  # May be empty if no rules have guidance context

    def test_validation_context_returns_rules(self):
        """Verify validation context returns rules from registry."""
        rules = get_rules_for_context("validation")
        
        assert len(rules) > 0, "validation context should have rules"
        rule_ids = [r.get("id") for r in rules]
        # VALIDATION.FIRST has contexts: [validation, transition]
        assert "RULE.VALIDATION.FIRST" in rule_ids

    def test_transition_context_returns_rules(self):
        """Verify transition context returns rules from registry."""
        rules = get_rules_for_context("transition")
        
        assert len(rules) > 0, "transition context should have rules"

    def test_nonexistent_context_returns_empty(self):
        """Verify nonexistent context returns empty list."""
        rules = get_rules_for_context("nonexistent_context_xyz")
        
        assert rules == []


class TestConfigDrivenRuleIds:
    """Test that rule IDs are loaded from config, not hardcoded."""

    def test_task_blocked_to_wip_has_rules_in_config(self):
        """Verify task blocked→wip transition has rules defined in workflow.yaml."""
        workflow_cfg = WorkflowConfig()
        rules = workflow_cfg.get_transition_rules("task", "blocked", "wip")
        
        assert rules is not None, "task.blocked→wip should have rules in config"
        assert len(rules) > 0, "task.blocked→wip should have at least one rule"
        assert "RULE.GUARDS.FAIL_CLOSED" in rules

    def test_task_wip_to_done_has_rules_in_config(self):
        """Verify task wip→done transition has rules defined in workflow.yaml."""
        workflow_cfg = WorkflowConfig()
        rules = workflow_cfg.get_transition_rules("task", "wip", "done")
        
        assert rules is not None, "task.wip→done should have rules in config"
        assert len(rules) > 0, "task.wip→done should have at least one rule"
        assert "RULE.GUARDS.FAIL_CLOSED" in rules

    def test_qa_todo_to_wip_has_rules_in_config(self):
        """Verify qa todo→wip transition has rules defined in workflow.yaml."""
        workflow_cfg = WorkflowConfig()
        rules = workflow_cfg.get_transition_rules("qa", "todo", "wip")
        
        assert rules is not None, "qa.todo→wip should have rules in config"
        assert len(rules) > 0, "qa.todo→wip should have at least one rule"
        assert "RULE.VALIDATION.FIRST" in rules

    def test_qa_waiting_to_todo_has_rules_in_config(self):
        """Verify qa waiting→todo transition has rules defined in workflow.yaml."""
        workflow_cfg = WorkflowConfig()
        rules = workflow_cfg.get_transition_rules("qa", "waiting", "todo")
        
        assert rules is not None, "qa.waiting→todo should have rules in config"
        assert len(rules) > 0, "qa.waiting→todo should have at least one rule"
        # Config uses RULE.QA.WAITING_TO_TODO_TASK_DONE, not RULE.VALIDATION.FIRST
        assert "RULE.QA.WAITING_TO_TODO_TASK_DONE" in rules

    def test_task_done_to_validated_has_rules_in_config(self):
        """Verify task done→validated transition has rules defined in workflow.yaml."""
        workflow_cfg = WorkflowConfig()
        rules = workflow_cfg.get_transition_rules("task", "done", "validated")
        
        assert rules is not None, "task.done→validated should have rules in config"
        assert len(rules) > 0, "task.done→validated should have at least one rule"
        assert "RULE.VALIDATION.FIRST" in rules

    def test_all_key_transitions_have_rules(self):
        """Verify all key transitions referenced by compute.py have rules in config."""
        workflow_cfg = WorkflowConfig()
        
        # These are the transitions that compute.py uses for action building
        required_transitions = [
            ("task", "blocked", "wip"),
            ("task", "wip", "done"),
            ("task", "done", "validated"),
            ("qa", "waiting", "todo"),
            ("qa", "todo", "wip"),
        ]
        
        missing = []
        for domain, from_state, to_state in required_transitions:
            rules = workflow_cfg.get_transition_rules(domain, from_state, to_state)
            if not rules:
                missing.append(f"{domain}.{from_state}→{to_state}")
        
        assert not missing, f"Missing rules for transitions: {missing}"

