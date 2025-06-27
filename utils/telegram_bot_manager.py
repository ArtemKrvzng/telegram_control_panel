import subprocess
import os
import sys
import threading

_active_bots = {}

def is_bot_running(token: str) -> bool:
    return token in _active_bots


def start_bot_for_user(token: str, user_id: int) -> bool:
    if not token or is_bot_running(token):
        print(f"[TG Bot] Бот уже запущен или токен пуст.")
        return False

    try:
        bot_runner_path = os.path.join(os.path.dirname(__file__), "bot_runner.py")

        proc = subprocess.Popen(
            [sys.executable, bot_runner_path, token, str(user_id)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        _active_bots[token] = proc
        print(f"[TG Bot] Бот запущен для user_id={user_id}")

        # Поток для вывода логов
        def log_output():
            try:
                for line in proc.stdout:
                    print(f"[STDOUT]: {line.strip()}")
                for line in proc.stderr:
                    print(f"[STDERR]: {line.strip()}")
            except Exception as e:
                print(f"[TG Bot] Ошибка чтения вывода: {e}")

        threading.Thread(target=log_output, daemon=True).start()

        return True

    except Exception as e:
        print(f"[TG Bot] Ошибка запуска bot_runner: {e}")
        return False


def stop_bot_by_token(token: str):
    if not is_bot_running(token):
        print(f"[TG Bot] Бот с токеном не запущен: {token}")
        return False

    proc = _active_bots[token]

    try:
        proc.terminate()
        proc.wait(timeout=10)
        print(f"Бот остановлен: {token}")
    except subprocess.TimeoutExpired:
        proc.kill()
        print(f"Принудительно завершён бот: {token}")
    except Exception as e:
        print(f"Ошибка остановки бота: {e}")
        return False
    finally:
        _active_bots.pop(token, None)
    return True

def stop_all_bots():
    tokens = list(_active_bots.keys())
    for token in tokens:
        stop_bot_by_token(token)
    print("[TG Bot] Все боты остановлены.")