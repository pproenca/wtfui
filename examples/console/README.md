# Console Demo

Interactive system monitor demonstrating Flow's ConsoleRenderer and Yoga layout engine.

## Features

- Real-time CPU, memory, disk, and network stats
- Process list with sorting and filtering
- Keyboard navigation and command input
- Yoga flexbox layout computation

## Run

```bash
# Via CLI
uv run flow demo console

# Direct
cd examples/console && uv run python -c "from app import run_demo; run_demo()"
```

## Controls

- `Tab`: Cycle focus (processes → command → sidebar)
- `↑/↓`: Scroll process list
- `q`: Quit
- Commands: `filter <text>`, `sort cpu|mem`, `top`, `kill <pid>`, `quit`
