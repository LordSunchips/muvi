"""Compat shim for pre-final Python 3.14 builds (e.g. 3.14.0rc2), which lack the
`prefer_fwd_module` keyword that `typing._eval_type` gained shortly before 3.14.0
final and that current pydantic versions rely on. No-op on interpreters that
already have it (true 3.14.0+ final, or any later Python).
"""

import inspect
import sys
import typing

if sys.version_info >= (3, 14):
    _params = inspect.signature(typing._eval_type).parameters
    if "prefer_fwd_module" not in _params:
        _orig_eval_type = typing._eval_type

        def _eval_type_compat(*args: object, **kwargs: object) -> object:
            kwargs.pop("prefer_fwd_module", None)
            return _orig_eval_type(*args, **kwargs)

        typing._eval_type = _eval_type_compat
