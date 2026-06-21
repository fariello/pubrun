# This module provides functionality for generating publication-ready methods sections.

import sys
import types

class CallableModule(types.ModuleType):
    def __call__(self, *args, **kwargs):
        from pubrun.core import report as real_report
        return real_report(*args, **kwargs)

sys.modules[__name__].__class__ = CallableModule
