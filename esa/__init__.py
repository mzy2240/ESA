"""The following are importable from the top-level ``esa`` package:

*   SAW: ESA's primary class
*   Error: Base Error class for ESA exceptions. This exception is never
    directly raised.
*   PowerWorldError: Error class for when PowerWorld/SimAuto reports an
    error.
*   COMError: Error class for when something goes wrong communicating
    with Windows and/or SimAuto.
*   CommandNotRespectedError: Error class for when a commanded change is
    not respected by PowerWorld/SimAuto. This exception is only raised
    via SAW helper methods like
    ``change_and_confirm_params_multiple_element``
*   __version__: ESA's version.
"""
# Please keep the docstring above up to date with all the imports.
from .saw import SAW, PowerWorldError, COMError, CommandNotRespectedError,\
    Error
__version__ = "1.0.3"
