import copy
from collections import deque
from typing import List, Dict, Any, Tuple

'''
This module provides an event-driven simulation of fixed partition memory allocation
under First-Fit and Best-Fit strategies with FCFS job scheduling.

Expose run_simulation(strategy) for the GUI.
'''

# Default job stream
DEFAULT_JOBS: List[Dict[str, int]] = [
    {'stream': 1, 'time': 5, 'size': 5760},
    {'stream': 2, 'time': 4, 'size': 4190},
    {'stream': 3, 'time': 8, 'size': 3290},
    {'stream': 4, 'time': 2, 'size': 2030},
    {'stream': 5, 'time': 2, 'size': 2550},
    {'stream': 6, 'time': 6, 'size': 6990},
    {'stream': 7, 'time': 8, 'size': 8940},
    {'stream': 8, 'time': 10, 'size': 740},
    {'stream': 9, 'time': 7, 'size': 3930},
    {'stream': 10, 'time': 6, 'size': 6890},
    {'stream': 11, 'time': 5, 'size': 6580},
    {'stream': 12, 'time': 8, 'size': 3820},
    {'stream': 13, 'time': 9, 'size': 9140},
    {'stream': 14, 'time': 10, 'size': 420},
    {'stream': 15, 'time': 10, 'size': 220},
    {'stream': 16, 'time': 7, 'size': 7540},
    {'stream': 17, 'time': 3, 'size': 3210},
    {'stream': 18, 'time': 1, 'size': 1380},
    {'stream': 19, 'time': 9, 'size': 9850},
    {'stream': 20, 'time': 3, 'size': 3610},
    {'stream': 21, 'time': 7, 'size': 7540},
    {'stream': 22, 'time': 2, 'size': 2710},
    {'stream': 23, 'time': 8, 'size': 8390},
    {'stream': 24, 'time': 5, 'size': 5950},
    {'stream': 25, 'time': 10, 'size': 760},
]

# Default memory partitions (fixed, contiguous)
DEFAULT_MEMORY: List[Dict[str, Any]] = [
    {'block': 1, 'size': 9500, 'status': 'free', 'job': None, 'internal_fragmentation': 0, 'use_time': 0, 'use_count': 0},
    {'block': 2, 'size': 7000, 'status': 'free', 'job': None, 'internal_fragmentation': 0, 'use_time': 0, 'use_count': 0},
    {'block': 3, 'size': 4500, 'status': 'free', 'job': None, 'internal_fragmentation': 0, 'use_time': 0, 'use_count': 0},
    {'block': 4, 'size': 8500, 'status': 'free', 'job': None, 'internal_fragmentation': 0, 'use_time': 0, 'use_count': 0},
    {'block': 5, 'size': 3000, 'status': 'free', 'job': None, 'internal_fragmentation': 0, 'use_time': 0, 'use_count': 0},
    {'block': 6, 'size': 9000, 'status': 'free', 'job': None, 'internal_fragmentation': 0, 'use_time': 0, 'use_count': 0},
    {'block': 7, 'size': 1000, 'status': 'free', 'job': None, 'internal_fragmentation': 0, 'use_time': 0, 'use_count': 0},
    {'block': 8, 'size': 5500, 'status': 'free', 'job': None, 'internal_fragmentation': 0, 'use_time': 0, 'use_count': 0},
    {'block': 9, 'size': 1500, 'status': 'free', 'job': None, 'internal_fragmentation': 0, 'use_time': 0, 'use_count': 0},
    {'block': 10, 'size': 500, 'status': 'free', 'job': None, 'internal_fragmentation': 0, 'use_time': 0, 'use_count': 0},
]

def _find_block_first_fit(blocks: List[Dict[str, Any]], size: int) -> Tuple[int, Dict[str, Any]]:
    for i, b in enumerate(blocks):
        if b['status'] == 'free' and b['size'] >= size:
            return i, b
    return -1, None


def _find_block_best_fit(blocks: List[Dict[str, Any]], size: int) -> Tuple[int, Dict[str, Any]]:
    best_idx = -1
    best_size = None
    for i, b in enumerate(blocks):
        if b['status'] == 'free' and b['size'] >= size:
            if best_size is None or b['size'] < best_size:
                best_size = b['size']
                best_idx = i
    return (best_idx, blocks[best_idx]) if best_idx >= 0 else (-1, None)


def _allocate(block: Dict[str, Any], job: Dict[str, Any], t: int, metrics: Dict[str, Any]):
    block['status'] = 'occupied'
    block['job'] = {
        'stream': job['stream'],
        'size': job['size'],
        'remaining': job['time'],
        'start_time': t,
    }
    block['internal_fragmentation'] = block['size'] - job['size']
    block['use_count'] += 1
    metrics['internal_fragmentation_sum'] += block['internal_fragmentation']
    metrics['allocations'] += 1


def _free(block: Dict[str, Any]):
    block['status'] = 'free'
    block['job'] = None
    block['internal_fragmentation'] = 0


def run_simulation(strategy: str = 'First Fit', jobs: List[Dict[str, int]] = None, memory: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Run the event-driven simulation.

    strategy: 'First Fit' | 'Best Fit'
    jobs: optional list of jobs (dicts with stream, time, size). If None, use DEFAULT_JOBS.
    memory: optional memory blocks list. If None, use DEFAULT_MEMORY.

    Returns a results dict with metrics and final states.
    """
    jobs = copy.deepcopy(jobs if jobs is not None else DEFAULT_JOBS)
    blocks = copy.deepcopy(memory if memory is not None else DEFAULT_MEMORY)

    # FCFS waiting queue. All jobs "arrive" at t=0 in input order.
    waiting_q = deque(jobs)
    t = 0

    # Metrics
    metrics = {
        'time': 0,
        'jobs_completed': 0,
        'internal_fragmentation_sum': 0,
        'allocations': 0,
        'queue_length_time_area': 0,  # sum over time of queue length (for avg)
        'queue_length_max': 0,
        'waiting_times': [],
        'block_never_used': 0,
    }

    # Map: job_stream -> arrival_time (all 0) and allocation_time
    allocation_time: Dict[int, int] = {}

    # Helper to attempt allocations from queue repeatedly until no more can be allocated
    def try_allocate_from_queue():
        nonlocal waiting_q, t
        progressed = True
        while progressed and waiting_q:
            progressed = False
            # Peek FCFS
            job = waiting_q[0]
            # Choose finder
            if strategy.lower().startswith('best'):
                idx, block = _find_block_best_fit(blocks, job['size'])
            else:
                idx, block = _find_block_first_fit(blocks, job['size'])
            if idx >= 0:
                waiting_q.popleft()
                _allocate(blocks[idx], job, t, metrics)
                allocation_time[job['stream']] = t
                progressed = True

    # Initial allocation attempts at t=0
    try_allocate_from_queue()

    # Simulation loop: continue until all jobs completed
    while True:
        # Record queue length for time t
        metrics['queue_length_time_area'] += len(waiting_q)
        metrics['queue_length_max'] = max(metrics['queue_length_max'], len(waiting_q))

        # If no running jobs and no waiting jobs, done
        running = [b for b in blocks if b['status'] == 'occupied']
        if not running and not waiting_q:
            break

        # Advance time by 1 unit
        t += 1

        # Decrement running jobs and accumulate use_time
        for b in blocks:
            if b['status'] == 'occupied' and b['job'] is not None:
                b['job']['remaining'] -= 1
                b['use_time'] += 1

        # Free completed jobs
        for b in blocks:
            if b['status'] == 'occupied' and b['job'] is not None and b['job']['remaining'] <= 0:
                metrics['jobs_completed'] += 1
                _free(b)

        # After freeing, try to allocate from queue at this event time
        try_allocate_from_queue()

    metrics['time'] = t

    # Derived metrics
    throughput = metrics['jobs_completed'] / metrics['time'] if metrics['time'] > 0 else 0
    avg_queue_length = metrics['queue_length_time_area'] / metrics['time'] if metrics['time'] > 0 else 0

    # Waiting times for jobs that were allocated: allocation_time - arrival(0)
    waiting_times = []
    for j in jobs:
        st = j['stream']
        waiting_times.append(allocation_time.get(st, None))
    realized_waits = [w for w in waiting_times if w is not None]
    avg_wait_time = sum(realized_waits) / len(realized_waits) if realized_waits else 0

    # Storage utilization: never used partitions and heavily used (>=50% of sim time)
    never_used = sum(1 for b in blocks if b['use_count'] == 0)
    heavily_used = sum(1 for b in blocks if b['use_time'] >= 0.5 * metrics['time'])
    total_blocks = len(blocks)

    avg_internal_frag = (metrics['internal_fragmentation_sum'] / metrics['allocations']) if metrics['allocations'] > 0 else 0

    results = {
        'strategy': strategy,
        'total_time': metrics['time'],
        'jobs_completed': metrics['jobs_completed'],
        'throughput': throughput,
        'avg_queue_length': avg_queue_length,
        'max_queue_length': metrics['queue_length_max'],
        'avg_wait_time': avg_wait_time,
        'waiting_times': waiting_times,
        'avg_internal_fragmentation': avg_internal_frag,
        'never_used_partitions_pct': (never_used / total_blocks * 100.0) if total_blocks else 0,
        'heavily_used_partitions_pct': (heavily_used / total_blocks * 100.0) if total_blocks else 0,
        'final_blocks': blocks,
        'jobs': jobs,
    }

    return results

'''
Notes for report sections (c)-(f):

(c) FCFS conflict handling: jobs are enqueued in a waiting queue when no suitable
    partition is free. The queue is FIFO; new arrivals join the tail. Allocation always
    serves the head of the queue when a fitting partition becomes available.

(d) Job clocks and wait clocks: each running job maintains a remaining-time counter
    decremented every time unit. Wait clock per job is the time spent from arrival to
    allocation; here, arrival is t=0, so wait equals allocation time.

(e) Events: completion of a job (freeing a partition) and initial time t=0. On each event,
    the allocator attempts to place waiting jobs into memory according to the chosen
    strategy.

(f) Compare results returned by run_simulation for 'First Fit' and 'Best Fit' on the given
    workload to discuss throughput, utilization, queueing, and fragmentation.
'''


"""
GUI guidance is implemented in frontend/gui.py. Use run_simulation() from this module.
"""
