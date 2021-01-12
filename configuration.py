# This file is part of the payment_collect_cabal module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import ModelSQL, fields
from trytond.pool import PoolMeta, Pool
from trytond.modules.company.model import CompanyValueMixin

__all__ = ['Configuration', 'ConfigurationPaymentCollectCABAL']


class Configuration(metaclass=PoolMeta):
    __name__ = 'payment_collect.configuration'
    payment_method_cabal = fields.MultiValue(fields.Many2One(
            'account.invoice.payment.method', "Payment Method CABAL",
            required=True))
    cabal_company_code = fields.MultiValue(fields.Char('Comany code CABAL'))

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'cabal_company_code':
            return pool.get('payment_collect.configuration.cabal')
        elif field == 'payment_method_cabal':
            return pool.get('payment_collect.configuration.cabal')
        return super(Configuration, cls).multivalue_model(field)


class ConfigurationPaymentCollectCABAL(ModelSQL, CompanyValueMixin):
    "PaymentCollect Configuration CABAL"
    __name__ = 'payment_collect.configuration.cabal'
    payment_method_cabal = fields.Many2One('account.invoice.payment.method',
        "Payment Method CABAL")
    cabal_company_code = fields.Char('Compay code CABAL')
