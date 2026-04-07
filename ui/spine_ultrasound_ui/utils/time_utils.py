import time


def now_text() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def now_ns() -> int:
    return time.time_ns()
