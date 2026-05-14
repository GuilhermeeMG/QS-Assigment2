import atexit
import multiprocessing as mp
import queue
import sys
import time

REPS = 1_000_000

SCHEDULE_TASKS_MAX_SECONDS = 0.08
CHECKSUM_MAX_SECONDS = 0.08

TESTING_TIMING = False
TESTING_REPS = 40
TESTING_WARMUP_REPS = 10

def normalize_task(task):
    """Return a validated task tuple or None if the task is invalid

    Accepted formats:
    - tuple/list: (task_id, start_time, duration, priority)
    """

    if isinstance(task, (tuple, list)) and len(task) == 4:  # Validate format
        task_id, start_time, duration, priority = task
    else:
        return None

    if not all(isinstance(x, int) for x in (task_id, start_time, duration, priority)): # all integers
        return None

    if duration <= 0:
        return None

    # priority must be in [1, 128].
    if not (1 <= priority <= 128):
        return None

    return (task_id, start_time, duration, priority)


def pick_best_ready(ready):
    """Pick and remove the highest-priority ready task

    Tie-breaker: earliest start time, then original input order
    """

    best_idx = 0
    best = ready[0]
    idx = 1
    while idx < len(ready):
        cand = ready[idx]
        #[task_id, start_time, priority, remaining, order]
        if cand[2] > best[2]:
            best_idx = idx
            best = cand
        elif cand[2] == best[2]:
            if cand[1] < best[1] or (cand[1] == best[1] and cand[4] < best[4]):
                best_idx = idx
                best = cand
        idx += 1

    return ready.pop(best_idx)


def schedule_tasks(tasks, current_time):
    """
    1. Highest-priority ready task runs first.
    2. If a higher-priority task becomes ready, preemption occurs.
    3. Equal-priority tasks are ordered by earliest start time.

    The returned list contains task IDs in execution order
    """

    if not isinstance(current_time, int) or current_time < 0:
        return []

    normalized_tasks = []
    #(task_id, start_time, priority, remaining, order)

    for order, raw_task in enumerate(tasks):
        task = normalize_task(raw_task)
        if task is None:
            continue

        task_id, start_time, duration, priority = task

        # Calculate how much time is left for this task at current_time
        time_passed = max(0, current_time - start_time)
        remaining = max(0, duration - time_passed)
        if remaining == 0:
            continue

        normalized_tasks.append((task_id, start_time, priority, remaining, order))

    if not normalized_tasks:
        return []

    # Pending tasks sorted by start time
    pending = sorted(normalized_tasks, key=lambda item: (item[1], item[4]))
    pending_idx = 0

    ready = []

    time = current_time
    sequence = []

    while pending_idx < len(pending) or ready:
        while pending_idx < len(pending) and pending[pending_idx][1] <= time:
            task_id, start_time, priority, remaining, order = pending[pending_idx]
            ready.append([task_id, start_time, priority, remaining, order])
            pending_idx += 1

        if not ready:
            # Idle until the next task becomes ready.
            time = pending[pending_idx][1]
            continue

        task_id, start_time, priority, remaining, order = pick_best_ready(ready)

        if not sequence or sequence[-1] != task_id:
            sequence.append(task_id)

        # Run until completion or next task arrival, then re-evaluate priorities
        if pending_idx < len(pending):
            next_arrival = pending[pending_idx][1]
        else:
            next_arrival = time + remaining
        run_for = min(remaining, next_arrival - time)

        if run_for <= 0:
            # fallback
            run_for = 0

        time += run_for
        remaining -= run_for

        if remaining > 0:
            ready.append([task_id, start_time, priority, remaining, order])

    return sequence


def checksum(payload, n: int, received_checksum: int) -> bool:
    """Validate a packet using a XOR-based checksum.

    The checksum of a payload of n bytes {b1, b2, ..., bn} is:
        b1 XOR b2 XOR ... XOR bn

    For an empty payload (n == 0), the checksum is defined as 0.

    Invalid values in the parameters return False.

    Accepted payload formats:
    - bytes / bytearray
    """

    # Validating n.
    if not isinstance(n, int) or n < 0:
        return False

    # Validating received_checksum.
    if not isinstance(received_checksum, int) or not (0 <= received_checksum <= 255):
        return False

    # Validating payload type.
    if not isinstance(payload, (bytes, bytearray)):
        return False
    
    # Validating payload length.
    if len(payload) != n:
        return False
    
    # Computing the checksum.
    computed = 0
    for b in payload:
        computed ^= b
        
    return computed == received_checksum

def _worker_loop(task_queue: mp.Queue, result_queue: mp.Queue) -> None:
    while True:
        task = task_queue.get()
        if task is None:
            return

        task_id, func, args, kwargs = task
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start
            result_queue.put((task_id, "ok", result, duration))
        except Exception as exc:
            duration = time.perf_counter() - start
            result_queue.put((task_id, "err", exc, duration))


class _WatchdogWorker:
    def __init__(self) -> None:
        self._ctx = mp.get_context("spawn")
        self._task_queue = self._ctx.Queue()
        self._result_queue = self._ctx.Queue()
        self._process = self._ctx.Process(
            target=_worker_loop,
            args=(self._task_queue, self._result_queue),
        )
        self._process.start()
        self._next_task_id = 1

    def submit(self, func: callable, args: tuple, kwargs: dict) -> int:
        task_id = self._next_task_id
        self._next_task_id += 1
        self._task_queue.put((task_id, func, args, kwargs))
        return task_id

    def get_result(self, task_id: int, max_seconds: float | None):
        try:
            if max_seconds is None:
                result_id, status, payload, duration = self._result_queue.get()
            else:
                result_id, status, payload, duration = self._result_queue.get(timeout=max_seconds)
        except queue.Empty:
            self._restart()
            return None, True, None

        if result_id != task_id:
            self._restart()
            return None, True, None

        if status == "err":
            raise payload

        return payload, False, duration

    def _restart(self) -> None:
        if self._process.is_alive():
            self._process.terminate()
        self._process.join()
        self._close_queues()
        self._task_queue = self._ctx.Queue()
        self._result_queue = self._ctx.Queue()
        self._process = self._ctx.Process(
            target=_worker_loop,
            args=(self._task_queue, self._result_queue),
        )
        self._process.start()
        self._next_task_id = 1

    def close(self) -> None:
        if self._process.is_alive():
            try:
                self._task_queue.put(None)
            except Exception:
                pass
            self._process.join(timeout=0.5)
            if self._process.is_alive():
                self._process.terminate()
                self._process.join()
        self._close_queues()

    def _close_queues(self) -> None:
        self._task_queue.close()
        self._task_queue.join_thread()
        self._result_queue.close()
        self._result_queue.join_thread()


class _WatchdogPool:
    _workers: list[_WatchdogWorker]
    _len_workers: int
    _next_worker: int

    def __init__(self, size: int = 2) -> None:
        self._workers = [_WatchdogWorker() for _ in range(size)]
        self._len_workers = size
        self._next_worker = 0

    def run_single(
        self, func: callable, args: tuple, kwargs: dict, max_seconds: float | None
    ) -> tuple:
        worker = self._workers[self._next_worker]
        self._next_worker = (self._next_worker + 1) % self._len_workers

        task_id = worker.submit(func, args, kwargs)
        start = time.perf_counter()
        payload, timed_out, duration = worker.get_result(task_id, max_seconds)
        if duration is None:
            duration = time.perf_counter() - start
        return payload, duration, timed_out

    def run_pair(
        self, func: callable, args: tuple, kwargs: dict, max_seconds: float
    ) -> list[tuple]:
        tasks = []
        start = time.perf_counter()
        for worker in self._workers:
            task_id = worker.submit(func, args, kwargs)
            tasks.append((worker, task_id))

        deadline = start + max_seconds
        results = []
        for worker, task_id in tasks:
            remaining = max(0.0, deadline - time.perf_counter())
            payload, timed_out, duration = worker.get_result(task_id, remaining)
            if duration is None:
                duration = time.perf_counter() - start
            results.append((payload, duration, timed_out))
        return results

    def close(self) -> None:
        for worker in self._workers:
            worker.close()


_WATCHDOG_POOL = None
_WATCHDOG_POOL_REGISTERED = False


def _get_pool() -> _WatchdogPool:
    global _WATCHDOG_POOL, _WATCHDOG_POOL_REGISTERED
    if _WATCHDOG_POOL is None:
        _WATCHDOG_POOL = _WatchdogPool(size=2)
        if not _WATCHDOG_POOL_REGISTERED:
            atexit.register(_shutdown_pool)
            _WATCHDOG_POOL_REGISTERED = True
    return _WATCHDOG_POOL


def _shutdown_pool() -> None:
    global _WATCHDOG_POOL
    if _WATCHDOG_POOL is not None:
        _WATCHDOG_POOL.close()
        _WATCHDOG_POOL = None


def _timed_call(func: callable, args: tuple, kwargs: dict, max_seconds: float | None) -> tuple:
    """
    Call the given function with arguments and measure the time taken.
    If it exceeds max_seconds, return a timeout indication.
    """
    if max_seconds is None:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration = time.perf_counter() - start
        return result, duration, False

    return _get_pool().run_single(func, args, kwargs, max_seconds)


def _timed_call_pair(func: callable, args: tuple, kwargs: dict, max_seconds: float | None) -> tuple:
    """Call the given function twice and measure each duration."""
    if max_seconds is None:
        start = time.perf_counter()
        result1 = func(*args, **kwargs)
        duration1 = time.perf_counter() - start

        start = time.perf_counter()
        result2 = func(*args, **kwargs)
        duration2 = time.perf_counter() - start

        return (result1, duration1, False), (result2, duration2, False)

    results = _get_pool().run_pair(func, args, kwargs, max_seconds)
    return results[0], results[1]


def _report_watchdog_issues(
    func_name: str, issues: list, timings: list, max_seconds: float
) -> None:
    """Report any watchdog issues detected during the redundant calls, including timing information."""
    timing_str = ", ".join(f"{t:.6f}s" for t in timings)
    issue_str = ", ".join(issues)
    print(
        f"[watchdog] {func_name} issues: {issue_str}. timings=[{timing_str}] max={max_seconds:.6f}s",
        file=sys.stderr,
    )


def ft_redundance(func: callable, *args, max_seconds: float | None = None, **kwargs):
    """Calls the given function multiple times to check for consistency and timing, and report any issues detected."""
    issues = []
    timings = []

    # First two calls in parallel to check for consistency and timing.
    (result1, t1, timed_out1), (result2, t2, timed_out2) = _timed_call_pair(
        func, args, kwargs, max_seconds=max_seconds
    )
    timings.append(t1)
    if timed_out1:
        issues.append("call1_timeout")
    timings.append(t2)
    if timed_out2:
        issues.append("call2_timeout")

    # If results differ, do a third call to break the tie.
    if timed_out1 or timed_out2 or result1 != result2:
        issues.append("result_mismatch_12")
        result3, t3, timed_out3 = _timed_call(func, args, kwargs, max_seconds=max_seconds)
        timings.append(t3)
        if timed_out3:
            issues.append("call3_timeout")

        # Determine the majority result among the three calls.
        if not timed_out1 and not timed_out3 and result1 == result3:
            result = result1
        elif not timed_out2 and not timed_out3 and result2 == result3:
            result = result2
        else:
            issues.append("result_mismatch_123")
            result = "ERROR_TMR"
    else:
        result = result1

    # Reporting issues if any.
    if issues and max_seconds is not None:
        _report_watchdog_issues(func.__name__, issues, timings, max_seconds)

    return result


def schedule_tasks_ft(tasks, current_time):
    return ft_redundance(
        schedule_tasks,
        tasks,
        current_time,
        max_seconds=SCHEDULE_TASKS_MAX_SECONDS,
    )


def checksum_ft(payload, n: int, received_checksum: int):
    return ft_redundance(
        checksum,
        payload,
        n,
        received_checksum,
        max_seconds=CHECKSUM_MAX_SECONDS,
    )


def execute_testing(reps):
    for _ in range(reps):
        result = schedule_tasks_ft([(1, 0, 10, 50), (2, 2, 5, 50), (3, 3, 3, 50)], 0)
        # flush=True so output is not lost if the process is killed mid-iteration.
        print(result, flush=True)


def execute_testing_timing(reps):
    times = []
    total_testing_reps = TESTING_REPS + TESTING_WARMUP_REPS
    for i in range(total_testing_reps):
        time1 = time.perf_counter()

        execute_testing(reps)

        if i < TESTING_WARMUP_REPS:
            print(
                f"[{i+1}/{total_testing_reps}] - Time for {reps} iterations (WARMUP): {time.perf_counter() - time1:.2f} seconds",
                flush=True,
            )
        else:
            times.append(time.perf_counter() - time1)
            print(
                f"[{i+1}/{total_testing_reps}] - Time for {reps} iterations: {time.perf_counter() - time1:.2f} seconds",
                flush=True,
            )

    print(f"Average time: {sum(times) / len(times):.2f} seconds", flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        reps = int(sys.argv[1])
    else:
        reps = REPS

    if TESTING_TIMING:
        execute_testing_timing(reps)
    else:
        execute_testing(reps)
