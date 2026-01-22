import math

def human_readable_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

def human_readable_time(seconds: int) -> str:
    if seconds < 0:
        return "Unknown"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{int(h)}h {int(m)}m"
    return f"{int(m)}m {int(s)}s"

def progress_bar(current: int, total: int, length: int = 10) -> str:
    if total == 0:
        return "░" * length
    percent = current / total
    filled_length = int(length * percent)
    bar = "▓" * filled_length + "░" * (length - filled_length)
    return bar

def speed_format(bytes_per_sec: int) -> str:
    return f"{human_readable_size(bytes_per_sec)}/s"

def percentage(current: int, total: int) -> str:
    if total == 0:
        return "0%"
    return f"{int((current / total) * 100)}%"
