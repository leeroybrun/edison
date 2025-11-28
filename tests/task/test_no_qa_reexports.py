"""Test that QA types are not re-exported from task modules.

This ensures clean module boundaries and prevents import confusion.
QA types should only be imported from their canonical locations.
"""
import pytest


def test_qarecord_not_in_task_models():
    """QARecord should not be importable from task.models."""
    from edison.core.task import models

    # QARecord should not be in the module
    assert not hasattr(models, 'QARecord'), \
        "QARecord should not be re-exported from task.models"

    # QARecord should not be in __all__
    if hasattr(models, '__all__'):
        assert 'QARecord' not in models.__all__, \
            "QARecord should not be in task.models.__all__"


def test_qarepository_not_in_task_repository():
    """QARepository should not be importable from task.repository."""
    from edison.core.task import repository

    # QARepository should not be in the module
    assert not hasattr(repository, 'QARepository'), \
        "QARepository should not be re-exported from task.repository"

    # QARepository should not be in __all__
    if hasattr(repository, '__all__'):
        assert 'QARepository' not in repository.__all__, \
            "QARepository should not be in task.repository.__all__"


def test_qarecord_import_from_canonical_location():
    """QARecord should be importable from its canonical location."""
    from edison.core.qa.models import QARecord

    # Should be able to import from canonical location
    assert QARecord is not None


def test_qarepository_import_from_canonical_location():
    """QARepository should be importable from its canonical location."""
    from edison.core.qa.repository import QARepository

    # Should be able to import from canonical location
    assert QARepository is not None


def test_task_models_exports_only_task_types():
    """task.models should only export Task-related types."""
    from edison.core.task import models

    # Task should be present
    assert hasattr(models, 'Task'), "Task should be in task.models"

    if hasattr(models, '__all__'):
        # __all__ should only contain Task types
        for name in models.__all__:
            assert not name.startswith('QA'), \
                f"task.models.__all__ should not contain QA types, found: {name}"


def test_task_repository_exports_only_task_repository():
    """task.repository should only export TaskRepository."""
    from edison.core.task import repository

    # TaskRepository should be present
    assert hasattr(repository, 'TaskRepository'), \
        "TaskRepository should be in task.repository"

    if hasattr(repository, '__all__'):
        # __all__ should only contain TaskRepository
        assert repository.__all__ == ['TaskRepository'], \
            f"task.repository.__all__ should only contain TaskRepository, got: {repository.__all__}"
