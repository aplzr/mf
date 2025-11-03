from tomlkit import comment, document, nl

from ..constants import DEFAULT_MEDIA_EXTENSIONS
from .settings_registry import REGISTRY

__all__ = ["default_cfg"]

# fmt: off
default_cfg = document()
default_cfg.add(comment("Media file search paths"))
default_cfg.add("search_paths", [])
default_cfg.add(nl())
default_cfg.add(comment("Media file extensions matched by 'mf find' and 'mf new'."))
default_cfg.add("media_extensions", DEFAULT_MEDIA_EXTENSIONS.copy())
default_cfg.add(nl())
default_cfg.add(comment("If true, 'mf find' and 'mf new' will only return results that match one of the file extensions"))
default_cfg.add(comment("defined by media_extensions. Otherwise all files found in the search paths will be returned."))
default_cfg.add(comment("Set to false if your search paths only contain media files and you don't want to manage media"))
default_cfg.add(comment("extensions."))
default_cfg.add("match_extensions", True)
default_cfg.add(nl())
default_cfg.add(comment("If true, files will be played in fullscreen mode"))
default_cfg.add("fullscreen_playback", True)
default_cfg.add(nl())
default_cfg.add(comment(REGISTRY["prefer_fd"].help))
default_cfg.add("prefer_fd", True)
# fmt: on
