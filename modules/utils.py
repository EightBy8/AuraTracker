# modules/utils.py
import datetime
from colorama import init, Fore

init(autoreset=True)


def log(message: str, level: str = "INFO") -> None:
    """
    Simple timestamped logger using colorama.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    colors = {"INFO": Fore.CYAN, "ERROR": Fore.RED, "SUCCESS": Fore.GREEN, "WARNING": Fore.YELLOW}
    color = colors.get(level, "")
    print(color + f"[{timestamp}] [{level}] {message}")


def seconds_until(hour: int, minute: int, second: int = 0) -> float:
    """
    Return number of seconds from now until the next occurrence of hour:minute:second.
    If that time already passed today, returns the seconds until that time tomorrow.
    """
    now = datetime.datetime.now()
    target = datetime.datetime.combine(now.date(), datetime.time(hour, minute, second))
    if now >= target:
        target += datetime.timedelta(days=1)
    return (target - now).total_seconds()
