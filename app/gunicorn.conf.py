from prometheus_client import multiprocess


def child_exit(server, worker):
    # Tidy up metric files of dead workers (prometheus multiprocess mode).
    multiprocess.mark_process_dead(worker.pid)
