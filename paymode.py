# This file is part of the payment_collect_cabal module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import PoolMeta, Pool


class PayMode(metaclass=PoolMeta):
    __name__ = 'payment.paymode'

    @property
    def origin_name(self):
        pool = Pool()
        PayModeCabal = pool.get('payment.paymode.cabal')
        name = super().origin_name
        if isinstance(self.origin, PayModeCabal):
            name = self.origin.paymode.rec_name
        return name

    @classmethod
    def _get_origin(cls):
        models = super()._get_origin()
        models.append('payment.paymode.cabal')
        return models
