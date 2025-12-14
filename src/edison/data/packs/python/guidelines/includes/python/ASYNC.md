# Async (asyncio)

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: patterns -->
- Prefer structured concurrency (`TaskGroup`) when doing parallel work.
- Keep async boundaries explicit; don’t mix sync/async implicitly.

```py
import asyncio

async def fetch_one(i: int) -> int:
    await asyncio.sleep(0)
    return i

async def fetch_all() -> list[int]:
    results: list[int] = []
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch_one(i)) for i in range(3)]
    for t in tasks:
        results.append(t.result())
    return results
```
<!-- /section: patterns -->
