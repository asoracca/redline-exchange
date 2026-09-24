"""Compatibility entry point for the explicit-budget v2 evaluation CLI.

Credentials alone never start calls. Supply --authorize-live and all budget flags.
Without that flag this runs the scripted baseline and marks live as unmeasured.
"""

from .evaluate_v2 import main

if __name__ == "__main__":
    main()
