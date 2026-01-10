from ..platform_selector import PlatformType
from .base import PlatformAdapter
from .github import GitHubAdapter
from .linear import LinearAdapter
from .markdown import MarkdownAdapter


def get_platform_adapter(platform: PlatformType) -> PlatformAdapter:
    if platform == PlatformType.MARKDOWN:
        return MarkdownAdapter()
    elif platform == PlatformType.LINEAR:
        return LinearAdapter()
    elif platform == PlatformType.GITHUB:
        return GitHubAdapter()
    else:
        raise ValueError(f'Unsupported platform: {platform}')
