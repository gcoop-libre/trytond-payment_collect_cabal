# This file is part of the payment_collect_cabal module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import logging
from decimal import Decimal

from trytond.model import ModelStorage
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.modules.payment_collect.payments import PaymentMixIn

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

    def generate_collect(self, start):
        logger.info("generate_collect: cabal")
        pool = Pool()
        Configuration = pool.get('payment_collect.configuration')
        Company = pool.get('company.company')
        Invoice = pool.get('account.invoice')
        Currency = pool.get('currency.currency')
        Attachment = pool.get('ir.attachment')

        config = Configuration(1)
        if config.cabal_company_code:
            company_code = config.cabal_company_code
        else:
            raise UserError(gettext(
                'payment_collect_cabal.msg_missing_company_code'))
        company = Company(Transaction().context.get('company'))
        today = (Transaction().context.get('date') or
            pool.get('ir.date').today())

        self.cantidad_registros = 0
        self.monto_total = Decimal('0')
        csv_format = start.csv_format
        format_number = self.get_format_number()

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
            self.amount = Currency.round(invoice.currency,
                invoice.amount_to_pay)
            self.total_amount = self._formatear_importe(self.amount, 11)
            self.white_spaces = ' '.ljust(107)
            self.fecha_prestacion = start.expiration_date.strftime("%d%m%y")
            self.white_spaces2 = ' '.ljust(27)
            self.moneda = 'P'
            self.white_spaces3 = ' '.ljust(21)
            self.nro_cupon = self.nro_cupon + 1
            self.white_spaces4 = ' '.ljust(10)
            self.nro_contribuyente = '0'.ljust(15, '0')

            self.res.append(self.a_texto(csv_format))

            self.cantidad_registros = self.cantidad_registros + 1
            self.monto_total = self.monto_total + invoice.total_amount

        self.type = 'send'
        self.filename = 'COPYTAPS.txt'
        self.periods = start.periods
        collect = self.attach_collect()

        remito_info = """
        Nombre Empresa: %s
        Fecha de Vto: %s, Cant. Ditos: %s, Importe Total: %s""" % (
            company.party.name, start.expiration_date.strftime('%d/%m/%Y'),
            self.cantidad_registros, format_number(self.monto_total))
        remito = Attachment()
        remito.name = 'REMITO.txt'
        remito.resource = collect
        remito.data = remito_info.encode('utf8')
        remito.save()

        return [collect]

    def _formatear_importe(self, importe, digitos):
        return importe.to_eng_string().replace('.', '').rjust(digitos, '0')

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
        Configuration = pool.get('payment_collect.configuration')
        Invoice = pool.get('account.invoice')

        self.validate_return_file(self.return_file)

        config = Configuration(1)
        payment_method = None
        if config.payment_method_cabal:
            payment_method = config.payment_method_cabal

        pay_date = pool.get('ir.date').today()

        domain = self.get_domain(start.periods)
        domain.append(('paymode.type', '=', self.__name__))
        order = self.get_order()
        for line in self.return_file.decode('utf-8').splitlines():
            invoice_domain = self.get_invoice_domain(line)
            invoice = Invoice.search(domain + invoice_domain,
                order=order, limit=1)
            if not invoice:
                continue
            pay_amount = invoice[0].amount_to_pay
            result = line[115]
            if result == ' ':
                transaction = self.message_invoice(invoice, 'A',
                    'Movimiento Aceptado', pay_amount, pay_date,
                    payment_method=payment_method)
            else:
                transaction = self.message_invoice(invoice, 'R',
                    self.tabla_codigos[result], pay_amount,
                    payment_method=payment_method)
            transaction.collect = self.collect
            transaction.save()

        self.filename = "%s-%s-%s" % (start.paymode_type, self.type,
            pay_date.strftime("%Y-%m-%d"))
        collect = self.attach_collect()
        return [collect]

    @classmethod
    def validate_return_file(cls, return_file):
        if not return_file:
            raise UserError(gettext('payment_collect.msg_return_file_empty'))

    @classmethod
    def get_invoice_domain(cls, line):
        party_code = line[0:9].lstrip('0')
        domain = [
            ('party.code', '=', party_code),
            ]
        return domain
