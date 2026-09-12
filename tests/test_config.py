"""pytest configuration for OpenStates MCP tests."""

from pathlib import Path

from _pytest.config import Config
from loguru import logger

# Configure test logging
test_log_path = Path(__file__).parent / "test_logs" / "test.log"
test_log_path.parent.mkdir(exist_ok=True)
logger.add(test_log_path, rotation="10 MB", retention="1 week")


def pytest_configure(config: Config) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
