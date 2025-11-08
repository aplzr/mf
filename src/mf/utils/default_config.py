from tomlkit import comment, document, nl

from .settings_registry import REGISTRY

__all__ = ["default_cfg"]

default_cfg = document()

for setting_key in REGISTRY:
    spec = REGISTRY[setting_key]
    default_cfg.add(comment(spec.help))
    default_cfg.add(setting_key, spec.default)
    default_cfg.add(nl())
