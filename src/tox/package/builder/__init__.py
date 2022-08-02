from .isolated import build
from .legacy import make_sdist


def build_package(config, session):
    return (
        build(config, session)
        if config.isolated_build
        else make_sdist(config, session)
    )
