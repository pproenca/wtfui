from wtfui.core.element import Element

BRAILLE_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
DOT_FRAMES = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
LINE_FRAMES = ["-", "\\", "|", "/"]


class Spinner(Element):
    __slots__ = ("_frame_idx", "cls", "frames")

    def __init__(
        self,
        frames: list[str] | None = None,
        cls: str = "",
        **kwargs: object,
    ) -> None:
        super().__init__(cls=cls, **kwargs)
        self.frames = frames if frames is not None else BRAILLE_FRAMES
        self._frame_idx = 0
        self.cls = cls

    @property
    def current_frame(self) -> str:
        return self.frames[self._frame_idx]

    def advance(self) -> None:
        self._frame_idx = (self._frame_idx + 1) % len(self.frames)

    def reset(self) -> None:
        self._frame_idx = 0
