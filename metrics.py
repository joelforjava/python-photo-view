import logging
import resource

import time

LOG = logging.getLogger('frame.metrics')


# From https://medium.com/survata-engineering-blog/monitoring-memory-usage-of-a-running-python-program-49f027e3d1ba
class MemoryMonitor:
    def __init__(self):
        self.keep_measuring = True
        self.log = logging.getLogger('frame.MemoryMonitor')

    def measure_usage(self):
        max_usage = 0
        while self.keep_measuring:
            max_usage = max(
                max_usage,
                resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            self.log.info('Current max usage: %d', max_usage)
            # TODO - make configurable?
            time.sleep(90)

        return max_usage


def log_mem_usage():
    # This gives ridiculous values, e.g. 252170240, which is supposed to be kilobytes!
    # That ends up over 240 GB, which sounds.... wrong? I'm sure there's something wrong
    # with how I'm using it, but I'll come back to it later.
    # macOS Activity Monitor shows ~240 MB usage.
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    LOG.info('Current memory usage: %s', usage)
