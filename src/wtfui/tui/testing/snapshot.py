from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wtfui.tui.renderer import ConsoleRenderer


def snapshot(renderer: ConsoleRenderer) -> str:
    lines = []
    buffer = renderer.front_buffer

    for y in range(buffer.height):
        line_chars = []
        for x in range(buffer.width):
            cell = buffer.get(x, y)
            line_chars.append(cell.char if cell.char else " ")
        lines.append("".join(line_chars).rstrip())

    while lines and not lines[-1]:
        lines.pop()

    return "\n".join(lines)
