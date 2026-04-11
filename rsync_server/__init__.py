from buildstamp import load_metadata

from .server import RsyncModule, RsyncServer

_meta = load_metadata(__file__)
__version__ = _meta.version
__quality__ = _meta.quality
__commit__ = _meta.commit
__build_date__ = _meta.build_date

__all__ = ["RsyncModule", "RsyncServer"]
