"""Application-specific exceptions."""


class ImagePromptGenerationError(Exception):
    """Raised when local vision prompt generation fails."""

    def __init__(self, message: str, *, code: str = "prompt_generation_failed") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class VideoGenerationError(Exception):
    """Raised when the video generation orchestration flow fails."""

    def __init__(self, message: str, *, code: str = "video_generation_failed") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class KieGenerationError(Exception):
    """Raised when the Kie.ai provider request fails."""

    def __init__(self, message: str, *, code: str = "kie_generation_failed") -> None:
        self.message = message
        self.code = code
        super().__init__(message)
