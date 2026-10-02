"""Self-update through the installer. No GTK here."""

import os

INSTALLER_URL = "https://raw.githubusercontent.com/abdulahwahdi/claude-monitoring/main/install.sh"
UPDATE_COMMAND = "curl -fsSL %s | sh" % INSTALLER_URL
PIP_HINT = "Update with: pip install --user --upgrade ."
PACKAGE_PREFIX = "/usr/lib/python3/"


def installed_from_package(module_file=__file__) -> bool:
    """True for the .deb install, which the installer can upgrade.

    pip installs live elsewhere and must be upgraded with pip, or the
    installer would add a second copy next to them.
    """
    return os.path.realpath(module_file).startswith(PACKAGE_PREFIX)
