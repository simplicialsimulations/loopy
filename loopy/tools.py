from __future__ import division

__copyright__ = "Copyright (C) 2012 Andreas Kloeckner"

__license__ = """
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import numpy as np
from pytools.persistent_dict import KeyBuilder as KeyBuilderBase
from loopy.symbolic import WalkMapper


def is_integer(obj):
    return isinstance(obj, (int, long, np.integer))


# {{{ custom KeyBuilder subclass

class PersistentHashWalkMapper(WalkMapper):
    """A subclass of :class:`loopy.symbolic.WalkMapper` for constructing
    persistent hash keys for use with
    :class:`pytools.persistent_dict.PersistentDict`.

    See also :meth:`LoopyKeyBuilder.update_for_pymbolic_expression`.
    """

    def __init__(self, key_hash):
        self.key_hash = key_hash

    def visit(self, expr):
        self.key_hash.update(type(expr).__name__.encode("utf8"))

    def map_variable(self, expr):
        self.key_hash.update(expr.name.encode("utf8"))

    def map_constant(self, expr):
        self.key_hash.update(repr(expr).encode("utf8"))


class LoopyKeyBuilder(KeyBuilderBase):
    """A custom :class:`pytools.persistent_dict.KeyBuilder` subclass
    for objects within :mod:`loopy`.
    """

    # Lists, sets and dicts aren't immutable. But loopy kernels are, so we're
    # simply ignoring that fact here.
    update_for_list = KeyBuilderBase.update_for_tuple
    update_for_set = KeyBuilderBase.update_for_frozenset

    def update_for_dict(self, key_hash, key):
        # Order matters for the hash--insert in sorted order.
        for dict_key in sorted(key.iterkeys()):
            self.rec(key_hash, (dict_key, key[dict_key]))

    def update_for_BasicSet(self, key_hash, key):
        from islpy import Printer
        prn = Printer.to_str(key.get_ctx())
        getattr(prn, "print_"+key._base_name)(key)
        key_hash.update(prn.get_str().encode("utf8"))

    def update_for_type(self, key_hash, key):
        try:
            method = getattr(self, "update_for_type_"+key.__name__)
        except AttributeError:
            pass
        else:
            method(key_hash, key)
            return

        raise TypeError("unsupported type for persistent hash keying: %s"
                % type(key))

    def update_for_type_auto(self, key_hash, key):
        key_hash.update("auto".encode("utf8"))

    def update_for_pymbolic_expression(self, key_hash, key):
        if key is None:
            self.update_for_NoneType(key_hash, key)
        else:
            PersistentHashWalkMapper(key_hash)(key)

# }}}


def fix_dtype_after_unpickling(dtype):
    # Work around https://github.com/numpy/numpy/issues/4317
    from pyopencl.compyte.dtypes import DTYPE_TO_NAME
    for other_dtype in DTYPE_TO_NAME:
        # Incredibly, DTYPE_TO_NAME contains strings...
        if isinstance(other_dtype, np.dtype) and dtype == other_dtype:
            return other_dtype

    raise RuntimeError(
            "don't know what to do with (likely broken) unpickled dtype '%s'"
            % dtype)

# vim: foldmethod=marker
