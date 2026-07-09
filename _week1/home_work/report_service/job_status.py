from enum import Enum


class JobStatus(str, Enum):
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
