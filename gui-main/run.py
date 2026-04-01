from __future__ import annotations

from runtime.bootstrap_env import configure_runtime_environment


def main() -> None:
    configure_runtime_environment(require_qt=True)
    from spine_ultrasound_ui.app import main as desktop_main

    desktop_main()


if __name__ == '__main__':
    main()
