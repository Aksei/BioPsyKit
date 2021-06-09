import shutil
from pathlib import Path
import platform

DOIT_CONFIG = {
    "default_tasks": ["format", "test", "lint"],
    "backend": "json",
}

HERE = Path(__file__).parent


def task_format():
    """Reformat all files using black."""
    return {"actions": [["black", HERE]], "verbosity": 1}


def task_format_check():
    """Check, but not change, formatting using black."""
    return {"actions": [["black", HERE, "--check"]], "verbosity": 1}


# def task_test():
#     """Run Pytest with coverage."""
#     return {
#         "actions": ["pytest --cov=biopsykit %(paras)s"],
#         "params": [{"name": "paras", "short": "p", "long": "paras", "default": ""}],
#         "verbosity": 2,
#     }


def task_lint():
    """Lint all files with Prospector."""
    return {"actions": [["prospector"]], "verbosity": 1}


def task_type_check():
    """Type check with mypy."""
    return {"actions": [["mypy", "-p", "biopsykit"]], "verbosity": 1}


def task_docs():
    """Build the html docs using Sphinx."""
    if platform.system() == "Windows":
        return {"actions": [[HERE / "docs/make.bat", "html"]], "verbosity": 2}
    else:
        return {"actions": [["make", "-C", HERE / "docs", "html"]], "verbosity": 2}


def task_register_ipykernel():
    """Add a jupyter kernel with the biopsykit env to your local install."""

    return {
        "actions": [
            ["python", "-m", "ipykernel", "install", "--user", "--name", "biopsykit", "--display-name", "biopsykit"]
        ]
    }
