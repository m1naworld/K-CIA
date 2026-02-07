"""T7: Frontend build verification tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


class TestFrontendBuild:
    @pytest.mark.slow
    def test_typescript_compiles(self):
        """T7-1: tsc --noEmit succeeds with 0 errors."""
        result = subprocess.run(
            ["npx", "tsc", "--noEmit"],
            cwd=FRONTEND_DIR,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, f"TypeScript errors:\n{result.stdout}\n{result.stderr}"

    @pytest.mark.slow
    def test_next_build(self):
        """T7-2: next build succeeds."""
        result = subprocess.run(
            ["npx", "next", "build"],
            cwd=FRONTEND_DIR,
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, f"Build failed:\n{result.stdout}\n{result.stderr}"
