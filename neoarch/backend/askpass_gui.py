"""Standalone SUDO_ASKPASS helper that shows NeoArch's dark password dialog.

Invoked as ``python -m neoarch.backend.askpass_gui`` from the temporary
askpass script built by :func:`neoarch.backend.auth.prepare_askpass_env`.
Prints the entered password to stdout on success; exits non-zero when
cancelled so the caller can fall back to a system dialog.
"""

import sys


def main() -> int:
    from PyQt6.QtWidgets import QApplication
    from neoarch.frontend.components.dark_dialogs import dark_input

    app = QApplication.instance() or QApplication(sys.argv[:1])
    text, ok = dark_input(
        None,
        "Authentication Required",
        "NeoArch requires administrative privileges:",
    )
    if ok and text:
        sys.stdout.write(text + "\n")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
