# Python Async Guide

Comprehensive guide for asyncio and asynchronous programming in Python.

---

## Core Concepts

### async/await Basics

```python
import asyncio

async def fetch_data(url: str) -> dict:
    """Async function that fetches data."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()

async def main() -> None:
    """Entry point for async code."""
    data = await fetch_data("https://api.example.com/data")
    print(data)

# Run the event loop
asyncio.run(main())
```

### When to Use Async

**Good for:**
- I/O-bound operations (network, file, database)
- Concurrent HTTP requests
- WebSocket connections
- Real-time data processing

**Not good for:**
- CPU-bound operations (use multiprocessing instead)
- Simple scripts with no concurrency needs
- When all operations are sequential anyway

---

## Async Context Managers

### Using async with

```python
import httpx
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# Using third-party async context managers
async def fetch_all(urls: list[str]) -> list[dict]:
    async with httpx.AsyncClient() as client:
        results = []
        for url in urls:
            response = await client.get(url)
            results.append(response.json())
        return results

# Creating custom async context managers
@asynccontextmanager
async def managed_connection(host: str) -> AsyncGenerator[Connection, None]:
    """Async context manager for database connection."""
    conn = await create_connection(host)
    try:
        yield conn
    finally:
        await conn.close()

# Usage
async def query_database() -> list[dict]:
    async with managed_connection("localhost") as conn:
        return await conn.query("SELECT * FROM users")
```

---

## Async Iterators

### Using async for

```python
from collections.abc import AsyncIterator

async def stream_lines(path: str) -> AsyncIterator[str]:
    """Async generator that streams file lines."""
    async with aiofiles.open(path) as f:
        async for line in f:
            yield line.strip()

async def process_file(path: str) -> None:
    async for line in stream_lines(path):
        await process_line(line)
```

### Async Comprehensions

```python
# Async list comprehension
results = [result async for result in async_generator()]

# Async dict comprehension
mapping = {key: value async for key, value in async_items()}

# With filtering
filtered = [x async for x in source if await should_include(x)]
```

---

## Concurrency Patterns

### TaskGroup (Python 3.11+)

```python
async def fetch_all_concurrent(urls: list[str]) -> list[dict]:
    """Fetch multiple URLs concurrently using TaskGroup."""
    results: list[dict] = []

    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(fetch_url(url)) for url in urls]

    # All tasks completed when exiting context
    return [task.result() for task in tasks]
```

### gather (with error handling)

```python
async def fetch_all_with_gather(urls: list[str]) -> list[dict | Exception]:
    """Fetch all URLs, returning errors for failed requests."""
    tasks = [fetch_url(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

async def fetch_all_fail_fast(urls: list[str]) -> list[dict]:
    """Fetch all URLs, fail immediately on any error."""
    tasks = [fetch_url(url) for url in urls]
    return await asyncio.gather(*tasks)  # Raises on first error
```

### Semaphore for Rate Limiting

```python
async def fetch_with_limit(
    urls: list[str],
    max_concurrent: int = 10
) -> list[dict]:
    """Fetch URLs with concurrency limit."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def limited_fetch(url: str) -> dict:
        async with semaphore:
            return await fetch_url(url)

    tasks = [limited_fetch(url) for url in urls]
    return await asyncio.gather(*tasks)
```

---

## Timeouts

### Using asyncio.timeout (Python 3.11+)

```python
async def fetch_with_timeout(url: str, timeout: float = 10.0) -> dict:
    """Fetch with timeout."""
    async with asyncio.timeout(timeout):
        return await fetch_url(url)

async def safe_fetch(url: str) -> dict | None:
    """Fetch with timeout, returning None on timeout."""
    try:
        async with asyncio.timeout(5.0):
            return await fetch_url(url)
    except TimeoutError:
        return None
```

### Using wait_for

```python
async def fetch_with_wait_for(url: str) -> dict:
    """Fetch with timeout using wait_for."""
    try:
        return await asyncio.wait_for(fetch_url(url), timeout=10.0)
    except asyncio.TimeoutError:
        raise TimeoutError(f"Request to {url} timed out")
```

---

## Cancellation

### Handling Cancellation

```python
async def cancellable_task() -> None:
    """Task that handles cancellation gracefully."""
    try:
        while True:
            await process_item()
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        # Cleanup before exiting
        await cleanup()
        raise  # Re-raise to propagate cancellation

async def run_with_cancellation() -> None:
    """Run task with cancellation support."""
    task = asyncio.create_task(cancellable_task())

    await asyncio.sleep(10)  # Let it run for 10 seconds
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        print("Task was cancelled")
```

### Shield from Cancellation

```python
async def critical_operation() -> None:
    """Operation that should complete even if outer task is cancelled."""
    try:
        await asyncio.shield(save_to_database())
    except asyncio.CancelledError:
        # Shield was cancelled, but save_to_database continues
        pass
```

---

## Common Patterns

### Producer-Consumer Queue

```python
async def producer(queue: asyncio.Queue[str]) -> None:
    """Produce items to queue."""
    for i in range(100):
        await queue.put(f"item-{i}")
        await asyncio.sleep(0.1)
    await queue.put(None)  # Sentinel to stop consumer

async def consumer(queue: asyncio.Queue[str]) -> None:
    """Consume items from queue."""
    while True:
        item = await queue.get()
        if item is None:
            break
        await process(item)
        queue.task_done()

async def main() -> None:
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=10)

    async with asyncio.TaskGroup() as tg:
        tg.create_task(producer(queue))
        tg.create_task(consumer(queue))
```

### Background Tasks

```python
class BackgroundProcessor:
    """Process items in background."""

    def __init__(self) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start background processing."""
        self._task = asyncio.create_task(self._process_loop())

    async def stop(self) -> None:
        """Stop background processing."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def submit(self, item: str) -> None:
        """Submit item for processing."""
        await self._queue.put(item)

    async def _process_loop(self) -> None:
        """Main processing loop."""
        while True:
            item = await self._queue.get()
            try:
                await self._process(item)
            except Exception as e:
                logger.error(f"Error processing {item}: {e}")
            finally:
                self._queue.task_done()
```

---

## Avoiding Common Mistakes

### Don't Block the Event Loop

```python
# BAD: Blocking call in async function
async def bad_fetch() -> str:
    response = requests.get(url)  # BLOCKS!
    return response.text

# GOOD: Use async HTTP client
async def good_fetch() -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text

# GOOD: Run blocking code in thread pool
async def run_blocking() -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, blocking_function)
```

### Don't Create Tasks Without Awaiting

```python
# BAD: Task may be garbage collected
async def bad_fire_and_forget() -> None:
    asyncio.create_task(background_work())  # Not awaited!

# GOOD: Track the task
async def good_fire_and_forget() -> None:
    task = asyncio.create_task(background_work())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
```

### Don't Mix Sync and Async Incorrectly

```python
# BAD: Calling async from sync without proper handling
def bad_sync_wrapper():
    result = async_function()  # Returns coroutine, not result!

# GOOD: Use asyncio.run for entry points
def good_sync_wrapper():
    return asyncio.run(async_function())

# GOOD: Or mark function as async
async def good_async_caller():
    return await async_function()
```

---

## Testing Async Code

### pytest-asyncio

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await fetch_data("key")
    assert result is not None

@pytest.fixture
async def async_client():
    """Async fixture."""
    client = await create_client()
    yield client
    await client.close()

@pytest.mark.asyncio
async def test_with_async_fixture(async_client):
    response = await async_client.get("/")
    assert response.status_code == 200
```

### Testing Timeouts

```python
@pytest.mark.asyncio
async def test_timeout_handling():
    with pytest.raises(TimeoutError):
        async with asyncio.timeout(0.1):
            await asyncio.sleep(1.0)

@pytest.mark.asyncio
async def test_cancelled_task():
    async def long_running():
        await asyncio.sleep(10)

    task = asyncio.create_task(long_running())
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
```

---

## Performance Tips

### Batch Operations

```python
# BAD: Sequential requests
async def bad_fetch_all(ids: list[str]) -> list[dict]:
    results = []
    for id in ids:
        result = await fetch_one(id)
        results.append(result)
    return results

# GOOD: Concurrent requests
async def good_fetch_all(ids: list[str]) -> list[dict]:
    tasks = [fetch_one(id) for id in ids]
    return await asyncio.gather(*tasks)
```

### Connection Pooling

```python
# GOOD: Reuse client with connection pool
async def fetch_many_efficient(urls: list[str]) -> list[dict]:
    # Client manages connection pool internally
    async with httpx.AsyncClient() as client:
        tasks = [client.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        return [r.json() for r in responses]
```

---

## Summary

1. Use `async with` for resource management
2. Use `async for` for streaming data
3. Use TaskGroup (3.11+) for structured concurrency
4. Use Semaphore for rate limiting
5. Handle CancelledError properly
6. Never block the event loop
7. Always await or track created tasks
8. Use asyncio.timeout for timeouts
9. Test async code with pytest-asyncio
10. Batch concurrent operations for performance
