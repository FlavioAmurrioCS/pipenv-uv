# flake8: noqa: E501, FBT001, FBT002
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import logging
    import subprocess
    from collections.abc import Iterable
    from pathlib import Path
    from subprocess import Popen
    from typing import Any
    from typing import NamedTuple

    from pipenv.patched.pip._vendor.rich.status import Status
    from pipenv.project import Project
    from uv_to_pipfile.uv_to_pipfile2 import PipenvPackage
    from uv_to_pipfile.uv_to_pipfile2 import _PipfileLockSource

    class ResolverArgs(NamedTuple):
        pre: bool
        clear: bool
        verbose: int
        category: str | None
        system: bool
        parse_only: bool
        pipenv_site: str | None
        requirements_dir: str | None
        write: str | None
        constraints_file: str | None
        packages: list[str]


__ORIGINAL_RESOLVE_FUNC__ = None
__ORIGINAL_PIP_INSTALL_DEPS_FUNC__ = None


def get_logger() -> logging.Logger:
    import logging

    return logging.getLogger(__name__)


###############
def parse_requirements_lines(f: Iterable[str]) -> tuple[dict[str, PipenvPackage], str]:  # noqa: C901, PLR0912, PLR0915
    """Extracted from uv_to_pipfile.uv_to_pipfile2"""
    import os
    import re

    ret: dict[str, PipenvPackage] = {}
    _index = ""
    hashes = []
    for _line in f:
        line = _line.strip("\n \\")
        if not line:
            continue
        if line.startswith("#"):
            continue
        if line.startswith("-i "):
            _index = line.split("-i ")[-1]
            continue
        if line.startswith("--hash="):
            hashes.append(line.split("--hash=")[-1])
            continue

        hashes.sort()
        hashes = []

        package, _, markers = line.partition(";")
        package = package.strip()
        markers = markers.strip()

        pkg: PipenvPackage
        extras = ""
        name = "NOTHING"

        if package.startswith("-e "):
            project_dir = os.path.abspath(package.split("-e ")[-1])
            pyproject_path = os.path.join(project_dir, "pyproject.toml")
            name = os.path.basename(project_dir)
            if os.path.exists(pyproject_path):
                pattern = re.compile(r'name\s*=\s*["\']([^"\']+)["\']')
                with open(pyproject_path) as pf:
                    for mline in pf:
                        match = pattern.search(mline)
                        if match:
                            name = match.group(1)
                            break

            pkg = {
                "editable": True,
                "file": line.split("-e ")[-1],
            }
        elif "git+" in package:
            name, _, git_full = package.partition("@")
            if "[" in name:
                name, extras = line.strip("]").split("[", maxsplit=1)
            url, _, ref = git_full.partition("@")
            _vcs, _, git = url.partition("+")
            pkg = {
                "git": git,
                "ref": ref,
            }
        else:
            name, _, version = package.partition("==")
            extras = ""
            if "[" in name:
                name, extras = name.strip("]").split("[", maxsplit=1)
            pkg = {
                "hashes": hashes,
                "version": f"=={version}",
            }

        if markers:
            pkg["markers"] = markers
        if extras:
            pkg["extras"] = extras.split(",")
        ret[name] = pkg
    return ret, _index


###############


def resolve(cmd: list[str], st: Status, project: Project) -> subprocess.CompletedProcess[str]:
    if __ORIGINAL_RESOLVE_FUNC__ is None:
        msg = "Original resolve function is not available"
        raise RuntimeError(msg)
    from pipenv.resolver import get_parser

    parsed: ResolverArgs
    parsed, _remaining = get_parser().parse_known_args(cmd[2:])  # pyright: ignore[reportAssignmentType] # pyrefly: ignore[bad-assignment]
    constraints_file = parsed.constraints_file
    write = parsed.write or "/dev/stdout"
    logger = get_logger()
    if not constraints_file:
        logger.warning("No constraints file provided, running original function")
        return __ORIGINAL_RESOLVE_FUNC__(cmd, st, project)

    constraints: dict[str, str] = {}
    with open(constraints_file) as f:
        for line in f:
            left, right = line.split(", ", maxsplit=1)
            # NOTE: When using different sources, we need to strip the index URL
            constraints[left] = right.strip().split(" -i ", maxsplit=1)[0].strip()
    if not constraints:
        logger.warning("No constraints found, running original function")
        return __ORIGINAL_RESOLVE_FUNC__(cmd, st, project)

    import os

    if "PIPENV_UV_VERBOSE" in os.environ:
        data = {
            "constraints": constraints,
            "cmd": cmd,
            "project": vars(project),
        }
        import json

        logger.info("\nRunning pip compile with data: %s", json.dumps(data, default=str, indent=2))

    # NOTE: We could support multiple sources, but we don't need to for now
    # This would require use to parse index annotations.
    sources: list[_PipfileLockSource] = project.pipfile_sources()  # pyright: ignore[reportAssignmentType] # pyrefly: ignore[bad-assignment]
    if not sources:
        msg = "No sources found in Pipfile"
        raise ValueError(msg)
    if len(sources) > 1:
        msg = "Multiple sources are not supported"
        raise ValueError(msg)
    default_source, *_other_sources = sources

    from uv._find_uv import find_uv_bin

    cmd = [
        find_uv_bin(),
        "pip",
        "compile",
        f"--python={project.python(parsed.system)}",
        "--format=requirements.txt",  # The format in which the resolution should be output
        "--generate-hashes",  # Include distribution hashes in the output file
        "--no-strip-extras",  # Include extras in the output file
        "--no-strip-markers",  # Include environment markers in the output file
        "--no-annotate",  # Exclude comment annotations indicating the source of each package
        "--no-header",  # Exclude the comment header at the top of the generated output file
        "--quiet",  # Use quiet output
        f"--default-index={default_source['url']}",  # The URL of the default package index
        # *(f"--index={source['url']}" for source in _other_sources), # The URLs to use when resolving dependencies, in addition to the default index
        # "--emit-index-annotation",  # Include comment annotations indicating the index used to resolve each package (e.g., `# from https://pypi.org/simple`)
        *(
            () if not parsed.pre else ("--prerelease=allow",)
        ),  # The strategy to use when considering pre-release versions
        "-",
    ]
    if "PIPENV_UV_VERBOSE" in os.environ:
        logger.info("\nRunning command: %s", " ".join(cmd))
    import subprocess

    st.console.print("Pipenv is being enhanced with uv!")
    result = subprocess.run(  # noqa: S603
        cmd, input="\n".join(constraints.values()), text=True, capture_output=True, check=False
    )
    if result.returncode != 0:
        logger.error("uv pip compile failed with return code %d", result.returncode)
        logger.error("uv pip compile failed with output: %s", result.stdout)
        logger.error("uv pip compile failed with error: %s", result.stderr)
        logger.error("Falling back to original function")
        return __ORIGINAL_RESOLVE_FUNC__(cmd, st, project)

    packages, _index = parse_requirements_lines(result.stdout.splitlines())
    with open(write, "w") as f:
        import json

        f.write(json.dumps([{"name": k, **v} for k, v in packages.items()]))
    return result


def subprocess_run(  # noqa: PLR0913
    args: list[str],
    *,
    block: bool = True,
    text: bool = True,
    capture_output: bool = True,
    encoding: str = "utf-8",
    env: dict[str, str] | None = None,
    **other_kwargs: Any,  # noqa: ANN401
) -> Popen[str]:
    if block:
        msg = "This patch only supports blocking subprocess.run calls"
        raise ValueError(msg)
    import os
    import subprocess

    _env = os.environ.copy()
    _env["PYTHONIOENCODING"] = encoding
    if env:
        # Ensure all environment variables are strings
        string_env = {k: str(v) for k, v in env.items() if v is not None}
        _env.update(string_env)
    other_kwargs["env"] = _env
    if capture_output:
        other_kwargs["stdout"] = subprocess.PIPE
        other_kwargs["stderr"] = subprocess.PIPE

    python, _file, _install, *rest = args
    from uv._find_uv import find_uv_bin

    rest.remove("--no-input")

    args = [
        find_uv_bin(),
        "pip",
        "install",
        f"--python={python}",
        f"--prefix={os.path.dirname(os.path.dirname(python))}",
        *rest,
    ]

    import sys

    print("Install go brrr with uv!", file=sys.stderr)
    if "PIPENV_UV_VERBOSE" in os.environ:
        get_logger().info("\nRunning command: %s", " ".join(args))

    return subprocess.Popen(args, universal_newlines=text, encoding=encoding, **other_kwargs)  # noqa: S603


def pip_install_deps(  # noqa: PLR0913
    project: Project,
    deps: list[str],
    sources: list[_PipfileLockSource],
    allow_global: bool = False,
    ignore_hashes: bool = False,
    no_deps: bool = False,
    requirements_dir: Path | None = None,
    use_pep517: bool = True,
    extra_pip_args: list[str] | None = None,
) -> list[Popen[str]]:
    if __ORIGINAL_PIP_INSTALL_DEPS_FUNC__ is None:
        msg = "Original pip_install_deps function is not available"
        raise RuntimeError(msg)
    from unittest.mock import patch

    import pipenv.utils.pip

    with patch.object(pipenv.utils.pip, "subprocess_run", subprocess_run):
        return __ORIGINAL_PIP_INSTALL_DEPS_FUNC__(
            project=project,
            deps=deps,
            sources=sources,
            allow_global=allow_global,
            ignore_hashes=ignore_hashes,
            no_deps=no_deps,
            requirements_dir=requirements_dir,
            use_pep517=use_pep517,
            extra_pip_args=extra_pip_args,
        )


def _patch() -> None:
    global __ORIGINAL_RESOLVE_FUNC__
    global __ORIGINAL_PIP_INSTALL_DEPS_FUNC__  # noqa: PLW0603

    if __ORIGINAL_RESOLVE_FUNC__ is not None or __ORIGINAL_PIP_INSTALL_DEPS_FUNC__ is not None:
        # Already patched
        return

    import os

    if os.getenv("PIPENV_UV_DISABLE_ALL_PATCHES"):
        return
    import sys

    if sys.argv and sys.argv[0] and sys.argv[0].endswith("pipenv"):
        from pipenv.utils import resolver

        if not os.getenv("PIPENV_UV_DISABLE_RESOLVE_PATCH"):
            __ORIGINAL_RESOLVE_FUNC__, resolver.resolve = resolver.resolve, resolve

        if not os.getenv("PIPENV_UV_DISABLE_INSTALL_PATCH"):
            from pipenv.utils import pip

            __ORIGINAL_PIP_INSTALL_DEPS_FUNC__ = pip.pip_install_deps
            pip.pip_install_deps = pip_install_deps  # pyrefly: ignore[bad-assignment]
