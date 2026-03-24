from scripts.avatar_widget import main as run_avatar_widget
from scripts.hotkey_daemon import main as run_hotkey_daemon


def main() -> None:
    try:
        run_avatar_widget()
    except SystemExit as exc:
        if exc.code not in (0, None):
            print("Desktop widget is unavailable. Falling back to headless background mode.")
            run_hotkey_daemon()
        else:
            raise


if __name__ == "__main__":
    main()
