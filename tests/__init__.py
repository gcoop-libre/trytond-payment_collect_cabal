# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

try:
    from trytond.modules.payment_collect_cabal.tests.test_payment_collect_cabal \
        import suite
except ImportError:
    from .test_payment_collect_cabal import suite

__all__ = ['suite']
