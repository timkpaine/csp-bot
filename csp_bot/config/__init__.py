from logging import getLogger
from pathlib import Path
from typing import List, Optional

from ccflow import RootModelRegistry, load_config as load_config_base

from csp_bot import __version__

log = getLogger(__name__)

__all__ = ("load_config",)


def load_config(
    config_dir: str = "",
    config_name: str = "",
    overrides: Optional[List[str]] = None,
    *,
    overwrite: bool = False,
    basepath: str = "",
) -> RootModelRegistry:
    return load_config_base(
        root_config_dir=str(Path(__file__).parent.resolve()),
        root_config_name="conf",
        config_dir=config_dir,
        config_name=config_name,
        overrides=overrides,
        overwrite=overwrite,
        basepath=basepath,
    )
