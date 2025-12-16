import sys
import time

SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


def make_progress(prefix: str, spinner_only: bool = False):
    """
    LIVE progress UI (ТОЛЬКО консоль).

    РЕЖИМЫ:
      spinner_only=False:
          <prefix>  ⠹ 15%
      spinner_only=True:
          <prefix>  ⠹

    ПРАВИЛА:
    - Без вертикальных палок внутри индикатора
    - Строка ВРЕМЕННАЯ
    - По завершении строка ПОЛНОСТЬЮ стирается
    - НИЧЕГО не логирует
    - НЕ печатает финальные строки
    - Никогда не попадает в log-файл

    Возвращает:
        progress_callback(current, total)
        finish() -> elapsed_seconds
    """

    start = time.time()
    last_len = 0
    spin_idx = 0

    def _erase():
        nonlocal last_len
        if last_len:
            sys.stdout.write("\r" + (" " * last_len) + "\r")
            sys.stdout.flush()
            last_len = 0

    def progress_callback(current: int = 0, total: int = 0):
        nonlocal last_len, spin_idx

        frame = SPINNER[spin_idx % len(SPINNER)]
        spin_idx += 1

        if spinner_only:
            line = f"{prefix}  {frame}"
        else:
            if not total:
                return
            percent = int(current * 100 / total)
            line = f"{prefix}  {frame} {percent}%"

        sys.stdout.write("\r" + line)
        sys.stdout.flush()
        last_len = len(line)

        # для реального прогресса — стираем на 100%
        if not spinner_only and total and current >= total:
            _erase()

    def finish() -> float:
        _erase()
        return time.time() - start

    return progress_callback, finish
