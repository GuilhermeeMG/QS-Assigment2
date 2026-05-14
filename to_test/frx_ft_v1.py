import sys

REPS = 1_000_000


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


def ft_redundance(func: callable, *args, **kwargs):
    # First two calls to check for consistency.
    result1 = func(*args, **kwargs)
    result2 = func(*args, **kwargs)

    # If results differ, do a third call to break the tie.
    if result1 != result2:
        result3 = func(*args, **kwargs)

        # Determine the majority result among the three calls.
        if result1 == result3:
            return result1
        elif result2 == result3:
            return result2
    else:
        return result1


def schedule_tasks_ft(tasks, current_time) -> bool:
    return ft_redundance(schedule_tasks, tasks, current_time)


def checksum_ft(payload, n: int, received_checksum: int) -> bool:
    return ft_redundance(checksum, payload, n, received_checksum)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        reps = int(sys.argv[1])
    else:
        reps = REPS
        
    for i in range(reps):
        result = schedule_tasks_ft([(1, 0, 10, 50), (2, 2, 5, 50), (3, 3, 3, 50)], 0)
        #checksum_ft(bytes([i % 256 for i in range(10)]), 10, 0)
        print(result, flush=True)
