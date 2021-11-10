# This file is part of the payment_collect_cabal module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal

import logging
from trytond.pool import Pool
from trytond.modules.payment_collect.payments import PaymentMixIn
from trytond.model import ModelStorage, ModelSQL, ModelView, fields
from trytond.transaction import Transaction
logger = logging.getLogger(__name__)

RETORNOS_CABAL = {
    ' ': 'Correcto',
    'A': 'Código de Identificación de socio no numérico o cero',
    'B': 'Cuenta Inhabilitada',
    'C': 'Moneda Distinta al Comercio',
    'D': 'Débito Duplicado',
    'E': 'Cuenta Bloqueada Transitoriamente',
    'F': 'Usuario Extranjero',
    'G': 'Importe no numérico o cero',
    'H': 'Fecha de presentación mayor a 35 días o inválida',
    'I': 'Tarjeta Inexistente',
    'J': 'Número de cupón no numérico',
    'K': 'Código de operación no numérico',
    'L': 'Cuenta Sin Disponible',
    'M': 'Cuenta en Situación Irregular',
    'N': 'Comercio Desactivado',
    'O': 'Consulte a la entidad',
    'R': 'Stop Debit',
    'V': 'Tarjeta Vencida',
}

class PayModeCabal(ModelStorage, PaymentMixIn):
    'Pay Mode Cabal'
    __name__ = 'payment.paymode.cabal'

    _SEPARATOR = ';'
    #_DEBITO_CODE = '51'
    #_CREDITO_CODE = '53'

    @classmethod
    def __setup__(cls):
        super(PayModeCabal, cls).__setup__()
        cls._error_messages.update({
            'missing_company_code':
                'Debe establecer el número de comercio CABAL',
                })

    def generate_collect(self, start):
        logger.info("generate_collect: cabal")
        pool = Pool()

        Company = pool.get('company.company')
        Attachment = pool.get('ir.attachment')
        Invoice = pool.get('account.invoice')
        Currency = pool.get('currency.currency')
        Configuration = pool.get('payment_collect.configuration')
        today = pool.get('ir.date').today()
        config = Configuration(1)
        if config.cabal_company_code:
            company_code = config.cabal_company_code
        else:
            self.raise_user_error('missing_company_code')
        self.periods = start.periods
        csv_format = start.csv_format
        self.monto_total = Decimal('0')
        self.cantidad_registros = 0
        self.type = 'send'
        self.filename = 'COPYTAPS.txt'
        format_number = self.get_format_number()
        format_date = self.get_format_date()
        domain = self.get_domain(start.periods)
        domain.append(('paymode.type', '=', start.paymode_type))
        order = self.get_order()
        invoices = Invoice.search(domain, order=order)
        self.res = []

        self.nro_cupon = 0
        self.id_empresa = company_code
        self.codigo_operacion = '01'
        for invoice in invoices:
            self.client_number = invoice.party.code.rjust(9, '0')
            self.credit_card_number = invoice.paymode.credit_number.ljust(16)
            self.amount = Currency.round(invoice.currency, invoice.amount_to_pay)
            self.total_amount = self.amount.to_eng_string().replace('.',
                '').rjust(11, '0')
            self.white_spaces = ' '.ljust(107)
            self.fecha_prestacion = start.expiration_date.strftime("%d%m%y")
            self.white_spaces2 = ' '.ljust(27)
            self.moneda = 'P'
            self.white_spaces3 = ' '.ljust(21)
            self.nro_cupon = self.nro_cupon + 1
            self.white_spaces4 = ' '.ljust(10)
            self.nro_contribuyente = '0'.ljust(15, '0')
            self.monto_total = self.monto_total + invoice.total_amount
            self.res.append(self.a_texto(csv_format))
            self.cantidad_registros = self.cantidad_registros + 1

        collect = self.create_collect()
        self.attach_collect()

        company = Company(Transaction().context.get('company'))
        remito_info = """
        Nombre Empresa: %s
        Fecha de Vto: %s, Cant. Ditos: %s, Importe Total: %s
        """ % (company.party.name, format_date(start.expiration_date),
            self.cantidad_registros, format_number(self.monto_total))
        remito = Attachment()
        remito.name = 'REMITO.txt'
        remito.resource = collect
        remito.data = remito_info.encode('utf8')
        remito.save()

        return [collect]

    def lista_campo_ordenados(self):
        """ Devuelve lista de campos ordenados """
        self.nro_cupon_campo = str(self.nro_cupon).rjust(4, '0')
        return [
            self.client_number,
            self.credit_card_number,
            self.total_amount,
            self.white_spaces,
            self.fecha_prestacion,
            self.white_spaces2,
            self.id_empresa,
            self.moneda,
            self.white_spaces3,
            self.nro_cupon_campo,
            self.white_spaces4,
            self.codigo_operacion,
            self.nro_contribuyente,
            ]

    def return_collect(self, start):
        logger.info("return_collect: cabal")
        super().return_collect(start, RETORNOS_CABAL)
        pool = Pool()
        Invoice = pool.get('account.invoice')
        Configuration = pool.get('payment_collect.configuration')
        config = Configuration(1)
        payment_method = None
        if config.payment_method_cabal:
            payment_method = config.payment_method_cabal

        if not self.return_file:
            self.raise_user_error('return_file_empty')

        # Obtener numeros de invoices de self.start.return_file
        self.paymode_type = start.paymode_type
        order = self.get_order()

        party_codes = []
        for line in self.return_file.decode('utf-8').splitlines():
            party_code = line[0:9].lstrip('0')
            party_codes.append(party_code)
            self.codigo_retorno[party_code] = line[115]

        domain = self.get_domain(start.periods)
        domain.append(('paymode.type', '=', self.__name__))
        domain.append(('party.code', 'in', party_codes))
        invoices = Invoice.search(domain, order=order)
        pay_date = pool.get('ir.date').today()
        self.filename = "%s-%s-%s" % (start.paymode_type, self.type,
            pay_date.strftime("%Y-%m-%d"))

        for invoice in invoices:
            if self.codigo_retorno[invoice.party.code] == ' ':
                transaction = self.message_invoice([invoice], 'A',
                    'Movimiento Aceptado', invoice.amount_to_pay, pay_date,
                    payment_method=payment_method)
            else:
                transaction = self.message_invoice([invoice], 'R',
                    self.tabla_codigos[self.codigo_retorno[invoice.party.code]],
                    invoice.amount_to_pay, payment_method=payment_method)
            transaction.collect = self.collect
            transaction.save()
        self.attach_collect()
        return [self.collect]
