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
  - [TODO](#todo)
  - [License](#license)

## Installation

With pipx:

```shell
pipx install pipenv
pipx inject pipenv pipenv-uv
```

With uv:

```shell
uv tool install pipenv --with pipenv-uv --force-reinstall
```

## Usage

Just use pipenv as normal :D

You can disable `uv` by using setting `DISABLE_PIPENV_UV_PATCH` ie
```bash
DISABLE_PIPENV_UV_PATCH=1 pipenv lock
```

## TODO
- [ ] Handle conflicts for main packages and dev packages
- [ ] Use uv for sync/install as well
- [ ] Add test

## License

`pipenv-uv` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
