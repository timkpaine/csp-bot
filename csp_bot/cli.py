from logging import getLogger
from pprint import pprint

import csp_gateway
import hydra
from ccflow import ModelRegistry
from csp_gateway import Gateway

from csp_bot import __version__

log = getLogger(__name__)

__all__ = (
    "load",
    "run",
    "main",
)


def load(cfg):
    log.info("Loading csp-bot config...")
    registry = ModelRegistry.root()
    registry.load_config(cfg=cfg, overwrite=True)
    return registry["gateway"]


def run(cfg):
    gateway: Gateway = load(cfg)
    log.info(f"Starting csp_gateway version {csp_gateway.__version__}")
    log.info(f"Starting csp_bot version {__version__}")
    kwargs = cfg["start"]
    if kwargs:  # i.e. start=False override on command line
        log.info(f"Starting gateway with arguments: {kwargs}")
        gateway.start(**kwargs)
    else:
        pprint(gateway.model_dump(by_alias=True))


@hydra.main(config_path="config", config_name="conf", version_base=None)
def main(cfg):
    run(cfg)


if __name__ == "__main__":
    main()
