"""Manager modules for NeoArch package manager."""

from . import git_manager
from . import docker_manager
from . import plugin_manager

__all__ = [
    'git_manager',
    'docker_manager',
    'plugin_manager',
]
