# flake8: noqa: S603
from __future__ import annotations

import logging
import os
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from uv_to_pipfile.uv_to_pipfile2 import PipfileLock

    from pipenv_uv._types import Pipfile

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found,unused-ignore]


logger = logging.getLogger(__name__)


def entrypoints() -> Generator[tuple[str, str], None, None]:
    with open("pyproject.toml", "rb") as f:
        pyproject = tomllib.load(f)
    yield from pyproject["project"]["scripts"].items()


@pytest.mark.parametrize("pair", entrypoints())
def test_help(pair: tuple[str, str]) -> None:
    k, _v = pair
    result = subprocess.run([k, "--help"], check=False, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(result.stderr)
        msg = f"Error running {k} --help"
        raise AssertionError(msg)


def test_lock(tmp_path: Path) -> None:
    """
    Test that pipenv lock works correctly with uv integration.
    - Make a Pipfile with several packages.
    - Run pipenv lock --dev to create the lock file with uv disabled.
    - Run pipenv lock --dev again to recreate the lock file with uv enabled.
    - Compare the two lock files to ensure that the uv integration works as expected.
        - Assert ensure files are not identical as uv adds less hashes.
        - The metadata sections should be identical.
        - The number of packages in both sections should be the same.
        - The package names should be the same.
        - For each package, the version should be the same.
        - For each package, the hashes in the original lock file should be a superset of
          the hashes in the new lock file.
    - Ensure that all packages from the Pipfile are present in the new lock file.
    """
    os.environ.pop("VIRTUAL_ENV", None)
    env = {"PIPENV_UV_DISABLE_ALL_PATCHES": "1"}
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    python_bin = sys.executable
    pipfile: Pipfile = {
        "source": [{"name": "pypi", "url": "https://pypi.org/simple", "verify_ssl": True}],
        "packages": {
            "requests": ">=2.0.0",
            "urllib3": "<2.0.0",
            "cffi": "!=2.0.0,>1.17.1",  # Force to use pre-release version
            "flask": {
                "version": "==1.1.2",
                "extras": ["dotenv"],
            },
            "sample-lib": {
                "file": "./sample-lib",
                "editable": True,
            },
        },
        "dev-packages": {
            "pytest": ">=6.0.0",
            "uv": "*",
            "ruff": "*",
        },
        "requires": {
            "python_version": python_version,
        },
        "pipenv": {"allow_prereleases": True},
    }
    import tomli_w

    pipfile_str = tomli_w.dumps(pipfile)

    import shutil

    from uv import find_uv_bin

    uv_bin = find_uv_bin()
    pipenv_bin = shutil.which("pipenv") or "pipenv"

    subprocess.run(
        (uv_bin, "init", f"--python={python_bin}", "--lib", "sample-lib"),
        check=True,
        cwd=tmp_path,
    )
    subprocess.run((uv_bin, "add", "lambda-dev-server"), check=True, cwd=tmp_path / "sample-lib")

    pipfile_path = tmp_path / "Pipfile"
    pipfile_path.write_text(pipfile_str)

    assert pipfile_path.exists()
    assert pipfile_path.read_text() == pipfile_str

    subprocess.run((pipenv_bin, "lock", "--dev"), check=True, cwd=tmp_path, env=env)
    assert pipfile_path.read_text() == pipfile_str
    lock_file = tmp_path / "Pipfile.lock"
    assert lock_file.exists()
    with lock_file.open("r", encoding="utf-8") as f:
        import json

        original_lock_data: PipfileLock = json.load(f)

    lock_file.rename(lock_file.with_suffix(".bak"))
    assert not lock_file.exists()

    subprocess.run((pipenv_bin, "lock", "--dev"), check=True, cwd=tmp_path)
    with lock_file.open("r", encoding="utf-8") as f:
        new_lock_data: PipfileLock = json.load(f)

    assert original_lock_data != new_lock_data  # they should not be identical as uv has less hashes
    assert original_lock_data["_meta"] == new_lock_data["_meta"]
    assert len(original_lock_data["default"]) == len(new_lock_data["default"])
    assert len(original_lock_data["develop"]) == len(new_lock_data["develop"])
    assert original_lock_data["default"].keys() == new_lock_data["default"].keys()
    assert original_lock_data["develop"].keys() == new_lock_data["develop"].keys()
    for section in ("default", "develop"):
        for pkg in original_lock_data[section]:
            orig_pkg_data = original_lock_data[section][pkg]
            new_pkg_data = new_lock_data[section][pkg]
            if "version" in orig_pkg_data and "version" in new_pkg_data:
                assert orig_pkg_data["version"] == new_pkg_data["version"]  # type: ignore[typeddict-item, unused-ignore]
            if "hashes" in orig_pkg_data and "hashes" in new_pkg_data:
                assert set(orig_pkg_data["hashes"]) >= set(new_pkg_data["hashes"])  # type: ignore[typeddict-item, unused-ignore]

    assert {*pipfile["dev-packages"].keys(), *pipfile["packages"].keys()} <= {
        *new_lock_data["default"].keys(),
        *new_lock_data["develop"].keys(),
    }
    # print(f"code --diff {lock_file.with_suffix('.bak')} {lock_file}")
    # print()
