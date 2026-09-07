from __future__ import annotations

from typing import TYPE_CHECKING

from pipenv_uv import parse_requirements_lines

if TYPE_CHECKING:
    from pathlib import Path


def _local_project(tmp_path: Path, dirname: str, name: str) -> Path:
    project = tmp_path / dirname
    project.mkdir()
    (project / "pyproject.toml").write_text(f'[project]\nname = "{name}"\n', encoding="utf-8")
    return project


def test_main() -> None:
    assert True


def test_parse_requirements_lines_local_path(tmp_path: Path) -> None:
    """A non-editable local path dep is keyed by its distribution name, not by its path."""
    project = _local_project(tmp_path, "cartografia", "biblioteca-cartografia")

    packages, _index = parse_requirements_lines([str(project)])

    assert packages == {"biblioteca-cartografia": {"path": str(project)}}


def test_parse_requirements_lines_local_path_without_pyproject(tmp_path: Path) -> None:
    """Without a pyproject.toml the directory basename is used, as for editable deps."""
    project = tmp_path / "shuju-guanli"
    project.mkdir()

    packages, _index = parse_requirements_lines([str(project)])

    assert packages == {"shuju-guanli": {"path": str(project)}}


def test_parse_requirements_lines_editable_path(tmp_path: Path) -> None:
    """An editable local path dep keeps its existing shape."""
    project = _local_project(tmp_path, "vishleshan", "vishleshan-core")

    packages, _index = parse_requirements_lines([f"-e {project}"])

    assert packages == {"vishleshan-core": {"editable": True, "file": str(project)}}


def test_parse_requirements_lines_editable_path_with_markers(tmp_path: Path) -> None:
    """Environment markers are not included in an editable dep's file value."""
    project = _local_project(tmp_path, "almacenamiento", "almacenamiento-cliente")

    packages, _index = parse_requirements_lines([f"-e {project} ; python_version >= '3.9'"])

    assert packages == {
        "almacenamiento-cliente": {
            "editable": True,
            "file": str(project),
            "markers": "python_version >= '3.9'",
        }
    }


def test_parse_requirements_lines_pinned_version() -> None:
    """A regular pinned package is unaffected."""
    packages, _index = parse_requirements_lines(["idna==3.10"])

    assert packages == {"idna": {"hashes": [], "version": "==3.10"}}
