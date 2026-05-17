# This file implements FR1 (Task Scheduler)


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


if __name__ == "__main__":
    print(schedule_tasks([(1, 0, 10, 50), (2, 2, 5, 50), (3, 3, 3, 50)], 0))
    print(schedule_tasks([(1, 0, 10, 50), (2, 2, 5, 60), (3, 3, 3, 70)], 0))
    print(schedule_tasks([(1, 0, 10, 50), (2, 2, 5, 50), (3, 3, 3, 50)], 8))
    print(schedule_tasks([(1, 0, 10, 200), (2, 2, 5, 50), (3, 3, 3, 50)], 0))
    
    # Task ( ID, start_time, duration, priority )