"""Analytical transformations must be usable without the plotting dependency."""
import subprocess
import sys
from pathlib import Path


def test_analytical_module_imports_when_matplotlib_is_unavailable():
    code = '''
import importlib.abc
import sys
class NoPlotting(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "matplotlib" or fullname.startswith("matplotlib."):
            raise ModuleNotFoundError("plotting intentionally unavailable")
sys.meta_path.insert(0, NoPlotting())
from src.nba_analysis import prepare_bench_rotation, build_leaderboards
assert callable(prepare_bench_rotation) and callable(build_leaderboards)
'''
    result = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1],
                            text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
