# Fault Tolerance Versions (v1 to v4)

Each version adds a feature or changes the execution model. Below is a concise summary of the differences and the benefits of each.

Version v1 (frx_ft_v1.py)
- Difference: Simple triple redundancy (2 calls + tie-breaker) with no timing or watchdog.
- Benefit: Fastest and simplest implementation; good baseline and easiest to reason about.

Version v2 (frx_ft_v2.py)
- Difference: Adds timing measurements and watchdog reporting when calls exceed a threshold, but no hard stop.
- Benefit: Adds observability for slow or inconsistent behavior with minimal overhead.

Version v3 (frx_ft_v3.py)
- Difference: Runs each call in a separate process and enforces a hard timeout by terminating the process.
- Benefit: Can stop hung or long-running calls, protecting the main loop from blocking.
- Trade-off: High overhead because each call spawns a new process; can be very slow for large REPS.

Version v4 (frx_ft_v4.py)
- Difference: Uses a persistent worker process for time-limited calls instead of spawning a process per call.
- Benefit: Keeps the hard timeout behavior while reducing overhead compared to v3.
- Trade-off: Still slower than in-process calls, but much faster than v3 when REPS is large.
