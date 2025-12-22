class _ColorShades:
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def _50(self) -> str:
        return f"{self._name}-50"

    @property
    def _100(self) -> str:
        return f"{self._name}-100"

    @property
    def _200(self) -> str:
        return f"{self._name}-200"

    @property
    def _300(self) -> str:
        return f"{self._name}-300"

    @property
    def _400(self) -> str:
        return f"{self._name}-400"

    @property
    def _500(self) -> str:
        return f"{self._name}-500"

    @property
    def _600(self) -> str:
        return f"{self._name}-600"

    @property
    def _700(self) -> str:
        return f"{self._name}-700"

    @property
    def _800(self) -> str:
        return f"{self._name}-800"

    @property
    def _900(self) -> str:
        return f"{self._name}-900"

    @property
    def _950(self) -> str:
        return f"{self._name}-950"


class _ColorsNamespace:
    Slate = _ColorShades("slate")
    Gray = _ColorShades("gray")
    Zinc = _ColorShades("zinc")
    Neutral = _ColorShades("neutral")
    Stone = _ColorShades("stone")
    Red = _ColorShades("red")
    Orange = _ColorShades("orange")
    Amber = _ColorShades("amber")
    Yellow = _ColorShades("yellow")
    Lime = _ColorShades("lime")
    Green = _ColorShades("green")
    Emerald = _ColorShades("emerald")
    Teal = _ColorShades("teal")
    Cyan = _ColorShades("cyan")
    Sky = _ColorShades("sky")
    Blue = _ColorShades("blue")
    Indigo = _ColorShades("indigo")
    Violet = _ColorShades("violet")
    Purple = _ColorShades("purple")
    Fuchsia = _ColorShades("fuchsia")
    Pink = _ColorShades("pink")
    Rose = _ColorShades("rose")


Colors = _ColorsNamespace()
