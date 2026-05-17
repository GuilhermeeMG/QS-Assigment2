import sys

from fr1_scheduler import schedule_tasks
from fr2_checksum import checksum

REPS = 1_000_000


if __name__ == "__main__":
    if len(sys.argv) > 1:
        reps = int(sys.argv[1])
    else:
        reps = REPS
        
    # Same workload, prints, and REPS as frx_ft_v4.py so ucXception campaigns
    # against this baseline and the FT version are directly comparable.
    for i in range(reps):
        result = schedule_tasks([(1, 0, 10, 50), (2, 2, 5, 50), (3, 3, 3, 50)], 0)
        print(result, flush=True)
