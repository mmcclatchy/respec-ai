from enum import Enum


class PlatformType(Enum):
    LINEAR = 'linear'
    GITHUB = 'github'
    MARKDOWN = 'markdown'


class PlatformSelector:
    def __init__(self) -> None:
        self._platform_capabilities = {
            PlatformType.LINEAR: {
                'supports_issues': True,
                'supports_comments': True,
                'supports_projects': True,
                'supports_labels': True,
                'real_time_collaboration': True,
                'external_integration': True,
            },
            PlatformType.GITHUB: {
                'supports_issues': True,
                'supports_comments': True,
                'supports_projects': True,
                'supports_labels': True,
                'real_time_collaboration': False,
                'external_integration': True,
            },
            PlatformType.MARKDOWN: {
                'supports_issues': True,  # Via structured spec files
                'supports_comments': True,  # Via spec comment functionality
                'supports_projects': True,  # Via project plan files
                'supports_labels': False,
                'real_time_collaboration': False,
                'external_integration': False,
            },
        }

    def get_available_platforms(self) -> list[PlatformType]:
        return list(PlatformType)

    def get_platform_capabilities(self, platform: PlatformType) -> dict[str, bool]:
        return self._platform_capabilities.get(platform, {})

    def recommend_platform(self, requirements: dict[str, bool]) -> PlatformType:
        scores = {}

        for platform, capabilities in self._platform_capabilities.items():
            score = 0
            for requirement, needed in requirements.items():
                if needed and capabilities.get(requirement, False):
                    score += 1
                elif needed and not capabilities.get(requirement, False):
                    score -= 2  # Penalty for missing required feature
            scores[platform] = score

        # Return platform with highest score
        best_platform = max(scores.keys(), key=lambda p: scores[p])
        return best_platform

    def validate_platform_choice(self, platform: PlatformType, requirements: dict[str, bool]) -> bool:
        capabilities = self._platform_capabilities.get(platform, {})

        for requirement, needed in requirements.items():
            if needed and not capabilities.get(requirement, False):
                return False

        return True
