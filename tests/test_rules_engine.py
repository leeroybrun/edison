"""Tests for rules engine."""
import pytest

from edison.core.rules import RulesEngine, RuleViolationError


def test_rules_engine_initialization():
    """Test rules engine loads config correctly."""
    config = {
        'rules': {
            'enforcement': True,
            'byState': {
                'done': [
                    {'id': 'all-tests-pass', 'description': 'Tests pass', 'enforced': True, 'blocking': True}
                ]
            }
        }
    }

    engine = RulesEngine(config)
    assert engine.enforcement_enabled is True
    assert 'done' in engine.rules_by_state
    assert len(engine.rules_by_state['done']) == 1


def test_blocking_rule_violation():
    """Test blocking rule prevents state transition."""
    config = {
        'rules': {
            'byState': {
                'done': [
                    {'id': 'all-tests-pass', 'description': 'Tests must pass', 'blocking': True}
                ]
            }
        }
    }

    engine = RulesEngine(config)
    task = {'id': 'T-001', 'testStatus': {'allPass': False}}

    with pytest.raises(RuleViolationError) as exc:
        engine.check_state_transition(task, 'wip', 'done')

    assert 'all-tests-pass' in str(exc.value)


def test_non_blocking_rule_warning():
    """Test non-blocking rule returns warning."""
    config = {
        'rules': {
            'byState': {
                'done': [
                    {'id': 'task-complete', 'description': 'Task complete', 'blocking': False}
                ]
            }
        }
    }

    engine = RulesEngine(config)
    task = {'id': 'T-001'}

    violations = engine.check_state_transition(task, 'wip', 'done')
    assert len(violations) > 0
    assert violations[0].severity == 'warning'
