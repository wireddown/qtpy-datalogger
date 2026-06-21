"""qtpy_datalogger package."""

import warnings

# Suppress tjguk/wmi #32
warnings.filterwarnings("ignore", category=SyntaxWarning, message="invalid escape sequence.*")
