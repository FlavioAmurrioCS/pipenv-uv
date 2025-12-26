from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing_extensions import NotRequired
    from typing_extensions import TypedDict

    class _PipfileSource(TypedDict):
        name: str
        url: str
        verify_ssl: bool

    class _PipfileRequires(TypedDict):
        python_version: str

    class _PipfilePackageDetailedFile(TypedDict):
        file: str
        editable: NotRequired[bool]

    class _PipfilePackageDetailed(TypedDict):
        editable: NotRequired[bool]
        extras: NotRequired[list[str]]
        version: str

    _PipfilePackage = str | _PipfilePackageDetailed | _PipfilePackageDetailedFile

    class _PipfilePipenv(TypedDict):
        allow_prereleases: NotRequired[bool]

    Pipfile = TypedDict(
        "Pipfile",
        {
            "source": NotRequired[list[_PipfileSource]],
            "dev-packages": NotRequired[dict[str, _PipfilePackage]],
            "packages": NotRequired[dict[str, _PipfilePackage]],
            "requires": NotRequired[_PipfileRequires],
            "pipenv": NotRequired[_PipfilePipenv],
        },
    )
