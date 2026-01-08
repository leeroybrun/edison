"""Tests for config validate command - validator configuration lint rules.

Tests the validation lint rule that rejects validators with `triggers: ["*"]`
when `always_run: false`. This is a configuration footgun - wildcards should
not be used to simulate "always required" behavior.
"""

from __future__ import annotations

import pytest

from edison.cli.config.validate import _check_validator_config


class TestCheckValidatorConfigWildcardTriggers:
    """Test _check_validator_config for wildcard trigger misconfigurations."""

    def test_wildcard_triggers_with_always_run_false_rejected(self) -> None:
        """Validator with triggers=["*"] and always_run=false should be rejected."""
        config = {
            "validation": {
                "validators": {
                    "bad-validator": {
                        "name": "Bad Validator",
                        "triggers": ["*"],
                        "always_run": False,
                    }
                }
            }
        }

        issues = _check_validator_config(config)

        # Should have exactly one error
        assert len(issues) == 1
        level, msg = issues[0]
        assert level == "error"
        assert "bad-validator" in msg
        assert "triggers: [\"*\"]" in msg or 'triggers: ["*"]' in msg
        assert "always_run: true" in msg or "always_run" in msg

    def test_wildcard_triggers_with_always_run_true_accepted(self) -> None:
        """Validator with triggers=["*"] and always_run=true should be accepted."""
        config = {
            "validation": {
                "validators": {
                    "good-validator": {
                        "name": "Good Validator",
                        "triggers": ["*"],
                        "always_run": True,
                    }
                }
            }
        }

        issues = _check_validator_config(config)

        assert len(issues) == 0

    def test_normal_triggers_with_always_run_false_accepted(self) -> None:
        """Validator with normal triggers and always_run=false should be accepted."""
        config = {
            "validation": {
                "validators": {
                    "triggered-validator": {
                        "name": "Triggered Validator",
                        "triggers": ["*.py", "*.ts"],
                        "always_run": False,
                    }
                }
            }
        }

        issues = _check_validator_config(config)

        assert len(issues) == 0

    def test_empty_triggers_with_always_run_false_accepted(self) -> None:
        """Validator with empty triggers and always_run=false should be accepted."""
        config = {
            "validation": {
                "validators": {
                    "no-triggers-validator": {
                        "name": "No Triggers Validator",
                        "triggers": [],
                        "always_run": False,
                    }
                }
            }
        }

        issues = _check_validator_config(config)

        assert len(issues) == 0

    def test_missing_triggers_field_accepted(self) -> None:
        """Validator without triggers field should be accepted."""
        config = {
            "validation": {
                "validators": {
                    "no-triggers-field": {
                        "name": "No Triggers Field",
                        "always_run": False,
                    }
                }
            }
        }

        issues = _check_validator_config(config)

        assert len(issues) == 0

    def test_missing_always_run_field_with_wildcard_triggers_rejected(self) -> None:
        """Validator with triggers=["*"] and missing always_run defaults to false -> rejected."""
        config = {
            "validation": {
                "validators": {
                    "missing-always-run": {
                        "name": "Missing Always Run",
                        "triggers": ["*"],
                        # always_run not specified, defaults to false
                    }
                }
            }
        }

        issues = _check_validator_config(config)

        # Should be rejected since missing always_run defaults to false
        assert len(issues) == 1
        level, msg = issues[0]
        assert level == "error"
        assert "missing-always-run" in msg

    def test_multiple_validators_with_issues(self) -> None:
        """Multiple validators with wildcard+always_run=false should all be reported."""
        config = {
            "validation": {
                "validators": {
                    "bad-validator-1": {
                        "name": "Bad Validator 1",
                        "triggers": ["*"],
                        "always_run": False,
                    },
                    "good-validator": {
                        "name": "Good Validator",
                        "triggers": ["*.py"],
                        "always_run": False,
                    },
                    "bad-validator-2": {
                        "name": "Bad Validator 2",
                        "triggers": ["*"],
                        "always_run": False,
                    },
                }
            }
        }

        issues = _check_validator_config(config)

        assert len(issues) == 2
        validator_names = [msg for _, msg in issues]
        assert any("bad-validator-1" in name for name in validator_names)
        assert any("bad-validator-2" in name for name in validator_names)

    def test_no_validation_section(self) -> None:
        """Config without validation section should return no issues."""
        config = {"project": {"name": "test"}}

        issues = _check_validator_config(config)

        assert len(issues) == 0

    def test_no_validators_section(self) -> None:
        """Config with validation but no validators should return no issues."""
        config = {"validation": {"engines": {}}}

        issues = _check_validator_config(config)

        assert len(issues) == 0

    def test_wildcard_among_other_triggers_rejected(self) -> None:
        """Validator with * among other triggers and always_run=false should be rejected."""
        config = {
            "validation": {
                "validators": {
                    "mixed-triggers": {
                        "name": "Mixed Triggers",
                        "triggers": ["*.py", "*", "*.ts"],
                        "always_run": False,
                    }
                }
            }
        }

        issues = _check_validator_config(config)

        # Should be rejected since "*" is present
        assert len(issues) == 1
        level, msg = issues[0]
        assert level == "error"
        assert "mixed-triggers" in msg


class TestCheckValidatorConfigErrorMessage:
    """Test that error messages are actionable and clear."""

    def test_error_message_suggests_always_run_true(self) -> None:
        """Error message should suggest using always_run: true."""
        config = {
            "validation": {
                "validators": {
                    "test-validator": {
                        "name": "Test Validator",
                        "triggers": ["*"],
                        "always_run": False,
                    }
                }
            }
        }

        issues = _check_validator_config(config)

        assert len(issues) == 1
        _, msg = issues[0]
        assert "always_run: true" in msg.lower() or "always_run" in msg

    def test_error_message_suggests_narrowing_triggers(self) -> None:
        """Error message should suggest narrowing triggers as alternative."""
        config = {
            "validation": {
                "validators": {
                    "test-validator": {
                        "name": "Test Validator",
                        "triggers": ["*"],
                        "always_run": False,
                    }
                }
            }
        }

        issues = _check_validator_config(config)

        assert len(issues) == 1
        _, msg = issues[0]
        # Should mention narrowing triggers as an alternative fix
        assert "narrow" in msg.lower() or "trigger" in msg.lower()
