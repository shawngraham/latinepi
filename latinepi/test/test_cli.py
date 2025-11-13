"""
Tests for the CLI module.
"""
import subprocess
import sys
import unittest
from pathlib import Path


class TestCLI(unittest.TestCase):
    """Test cases for the CLI functionality."""

    def test_hello_world(self):
        """Test that cli.py prints 'Hello World'."""
        cli_path = Path(__file__).parent.parent / "cli.py"
        result = subprocess.run(
            [sys.executable, str(cli_path)],
            capture_output=True,
            text=True
        )
        self.assertIn("Hello World", result.stdout)
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
