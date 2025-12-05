"""
Tests for config-driven rule IDs in session/next compute.

STRICT TDD: These tests verify rule IDs come from workflow.yaml config,
not hardcoded fallbacks.

P2-TP-004: Fix compute.py hardcoded rule IDs
"""
import pytest
from pathlib import Path
from edison.core.config.domains.workflow import WorkflowConfig


class TestGuidanceRules:
    """Test that guidance rules are configurable via workflow.yaml."""

    def test_delegation_guidance_rule_from_config(self):
        """Verify delegation guidance rule comes from config."""
        workflow_cfg = WorkflowConfig()
        rule = workflow_cfg.get_guidance_rule("delegation")
        
        assert rule is not None, "delegation guidance should have a primary rule"
        assert rule.startswith("RULE."), "guidance rule should be a valid rule ID"

    def test_delegation_guidance_rules_list(self):
        """Verify delegation has multiple guidance rules configured."""
        workflow_cfg = WorkflowConfig()
        rules = workflow_cfg.get_guidance_rules("delegation")
        
        assert len(rules) > 0, "delegation should have guidance rules"
        assert "RULE.DELEGATION.PRIORITY_CHAIN" in rules
        assert "RULE.DELEGATION.MOST_WORK" in rules

    def test_session_guidance_rules_from_config(self):
        """Verify session guidance rules are configurable."""
        workflow_cfg = WorkflowConfig()
        rules = workflow_cfg.get_guidance_rules("session")
        
        assert len(rules) > 0, "session should have guidance rules"
        assert "RULE.SESSION.NEXT_LOOP_DRIVER" in rules

    def test_context_guidance_rules_from_config(self):
        """Verify context management guidance rules are configurable."""
        workflow_cfg = WorkflowConfig()
        rules = workflow_cfg.get_guidance_rules("context")
        
        assert len(rules) > 0, "context should have guidance rules"
        assert "RULE.CONTEXT.BUDGET_MINIMIZE" in rules

    def test_missing_guidance_context_returns_none(self):
        """Verify missing guidance context returns None/empty."""
        workflow_cfg = WorkflowConfig()
        rule = workflow_cfg.get_guidance_rule("nonexistent")
        rules = workflow_cfg.get_guidance_rules("nonexistent")
        
        assert rule is None
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
