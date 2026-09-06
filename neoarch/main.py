"""
NeoArch - Entry point

A modern Arch Linux package management frontend.
"""

import os
import sys


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] in ("--help", "-h"):
            print("NeoArch - Elevate Your Arch Experience")
            print("Usage: python -m neoarch")
            print("A graphical package manager for Arch Linux with AUR support.")
            sys.exit(0)
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Use --help for usage information.")
            sys.exit(1)

    if os.geteuid() == 0:
        print("Do not run this application as root.")
        sys.exit(1)

    from PyQt6.QtWidgets import QApplication

    from neoarch.frontend.main_window import ArchPkgManagerUniGetUI
    from neoarch.resources.paths import APP_NAME

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    window = ArchPkgManagerUniGetUI()
    window.show()

    # Make sure the very first mapped frame is complete (content + border
    # painted together) before the window manager fades the window in.
    app.processEvents()
    window.repaint()

    window.check_authentication_tools()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
