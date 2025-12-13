# pipenv-uv

[![PyPI - Version](https://img.shields.io/pypi/v/pipenv-uv.svg)](https://pypi.org/project/pipenv-uv)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pipenv-uv.svg)](https://pypi.org/project/pipenv-uv)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/FlavioAmurrioCS/pipenv-uv/main.svg)](https://results.pre-commit.ci/latest/github/FlavioAmurrioCS/pipenv-uv/main)

Patch pipenv to use uv for lock and sync operations.

-----

## Table of Contents

- [pipenv-uv](#pipenv-uv)
  - [Table of Contents](#table-of-contents)
  - [Installation](#installation)
  - [Usage](#usage)
  - [Environmental Variables](#environmental-variables)
  - [TODO](#todo)
  - [License](#license)

## Installation

With pipx:

```bash
pipx install pipenv
pipx inject pipenv pipenv-uv
```

With uv:

```bash
uv tool install pipenv --with pipenv-uv --force-reinstall
```

Inject directly into pipenv(incase you install pipenv with something like brew):

```bash
"$(head -n1 "$(which pipenv)" | sed 's|#!||g')" -m pip install pipenv-uv
```

## Usage

Just use pipenv as normal :D

## Environmental Variables
- `PIPENV_UV_DISABLE_RESOLVE_PATCH` - Disable the patch for the resolve/lock command
- `PIPENV_UV_DISABLE_INSTALL_PATCH` - Disable the patch for install command
- `PIPENV_UV_DISABLE_ALL_PATCHES` - Disable all patches
- `PIPENV_UV_VERBOSE` - Enable verbose output

## TODO
- [ ] Handle conflicts for main packages and dev packages
- [x] Use uv for sync/install as well
- [ ] Add test

## License

`pipenv-uv` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
