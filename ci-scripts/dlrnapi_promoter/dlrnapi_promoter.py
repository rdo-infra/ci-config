#!/usr/bin/env python
"""
This file is currently in transition mode.
Almost all previous content has been transferred to the legacy_promoter
file, and the function called in the main are imported from there.
This serves as basis for the transition of the code to a more modularized
codebase To prepare for the implementation of component pipeline
"""
from __future__ import print_function
# Import previous content from the legacy_promoter file
from legacy_promoter import legacy_main


# Wrappers for the old code
def main():
    print("As part of the transition, the new promoter code will still call"
          "the old promoter code")
    # This new code will soon do something additional from the old promoter code
    #
    # legacy_main is imported from legacy code
    legacy_main()


if __name__ == '__main__':
    main()
