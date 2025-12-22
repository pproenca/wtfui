import asyncio

from wtfui.core.scheduler import wait_for_scheduler


async def stabilize(max_wait: float = 1.0) -> bool:
    await asyncio.sleep(0)

    return wait_for_scheduler(max_wait)
