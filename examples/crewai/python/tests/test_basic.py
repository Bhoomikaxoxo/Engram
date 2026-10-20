"""
Basic tests for engram_crewai package

Validates package structure, imports, and basic functionality.
"""


def test_package_import():
    """Test that engram_crewai imports successfully."""
    import engram_crewai

    assert engram_crewai is not None


def test_storage_import():
    """Test that EngramStorage can be imported."""
    from engram_crewai import EngramStorage

    assert EngramStorage is not None


def test_memory_storage_import():
    """Test that EngramMemoryStorage can be imported."""
    from engram_crewai import EngramMemoryStorage

    assert EngramMemoryStorage is not None


def test_tools_import():
    """Test that tool classes can be imported."""
    from engram_crewai import (
        EngramDialecticTool,
        EngramGetContextTool,
        EngramSearchTool,
    )

    assert EngramGetContextTool is not None
    assert EngramDialecticTool is not None
    assert EngramSearchTool is not None


class TestPackageMetadata:
    """Test package metadata and structure."""

    def test_package_has_version(self):
        """Test that package exposes version information."""
        import engram_crewai

        assert hasattr(engram_crewai, "__version__")
        assert isinstance(engram_crewai.__version__, str)
        assert len(engram_crewai.__version__) > 0

    def test_package_all_exports(self):
        """Test that __all__ contains expected exports."""
        import engram_crewai

        assert hasattr(engram_crewai, "__all__")
        expected_exports = [
            "EngramStorage",
            "EngramMemoryStorage",
            "EngramGetContextTool",
            "EngramDialecticTool",
            "EngramSearchTool",
            "EngramDependencyError",
        ]

        for export in expected_exports:
            assert export in engram_crewai.__all__, f"{export} not in __all__"
