==============================
Payment Collect CABAL Scenario
==============================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.tools import file_open
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.currency.tests.tools import get_currency
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences
    >>> from trytond.modules.account_invoice_ar.tests.tools import \
    ...     create_pos, get_invoice_types, get_pos, create_tax_groups
    >>> today = datetime.date.today()

Install payment_collect_cabal::

    >>> config = activate_modules('payment_collect_cabal')

Create company::

    >>> currency = get_currency('ARS')
    >>> currency.afip_code = 'PES'
    >>> currency.save()
    >>> _ = create_company(currency=currency)
    >>> company = get_company()
    >>> tax_identifier = company.party.identifiers.new()
    >>> tax_identifier.type = 'ar_cuit'
    >>> tax_identifier.code = '30710158254' # gcoop CUIT
    >>> company.party.iva_condition = 'responsable_inscripto'
    >>> company.party.save()

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company, datetime.date(2019, 1, 1)))
    >>> fiscalyear.click('create_period')
    >>> period = fiscalyear.periods[0]

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> receivable = accounts['receivable']
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> account_tax = accounts['tax']
    >>> account_cash = accounts['cash']

Create point of sale::

    >>> _ = create_pos(company)
    >>> pos = get_pos()
    >>> invoice_types = get_invoice_types()

Create tax groups::

    >>> tax_groups = create_tax_groups()

Create tax::

    >>> TaxCode = Model.get('account.tax.code')
    >>> tax = create_tax(Decimal('.10'))
    >>> tax.group = tax_groups['gravado']
    >>> tax.save()

Create payment method::

    >>> Journal = Model.get('account.journal')
    >>> PaymentMethod = Model.get('account.invoice.payment.method')
    >>> journal_cash, = Journal.find([('type', '=', 'cash')])
    >>> payment_method = PaymentMethod()
    >>> payment_method.name = 'Payment Method CABAL'
    >>> payment_method.journal = journal_cash
    >>> payment_method.credit_account = account_cash
    >>> payment_method.debit_account = account_cash
    >>> payment_method.save()

Create party::

    >>> Party = Model.get('party.party')
    >>> party = Party(name='Party')
    >>> party.iva_condition='responsable_inscripto'
    >>> party.vat_number='33333333339'
    >>> party.save()

Create a bank::

    >>> Bank = Model.get('bank')
    >>> bank = Bank()
    >>> bank.party = party
    >>> bank.save()

Create paymode method::

    >>> Paymode = Model.get('payment.paymode')
    >>> paymode = Paymode()
    >>> paymode.party = party
    >>> paymode.type = 'payment.paymode.cabal'
    >>> paymode.credit_number = '5896570000000008'
    >>> paymode.save()

Create account category::

    >>> ProductCategory = Model.get('product.category')
    >>> account_category = ProductCategory(name="Account Category")
    >>> account_category.accounting = True
    >>> account_category.account_expense = expense
    >>> account_category.account_revenue = revenue
    >>> account_category.customer_taxes.append(tax)
    >>> account_category.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.default_uom = unit
    >>> template.type = 'service'
    >>> template.list_price = Decimal('40')
    >>> template.account_category = account_category
    >>> template.save()
    >>> product, = template.products

Create invoices::

    >>> Invoice = Model.get('account.invoice')
    >>> InvoiceLine = Model.get('account.invoice.line')
    >>> invoice = Invoice()
    >>> invoice.party = party
    >>> invoice.pos = pos
    >>> invoice.invoice_date = period.start_date
    >>> invoice.paymode = paymode
    >>> line = InvoiceLine()
    >>> invoice.lines.append(line)
    >>> line.product = product
    >>> line.quantity = 5
    >>> line.unit_price = Decimal('40')
    >>> invoice.click('post')
    >>> invoice.untaxed_amount
    Decimal('200.00')
    >>> invoice.tax_amount
    Decimal('20.00')
    >>> invoice.total_amount
    Decimal('220.00')
    >>> invoice = Invoice()
    >>> invoice.party = party
    >>> invoice.pos = pos
    >>> invoice.invoice_date = period.start_date
    >>> invoice.paymode = paymode
    >>> line = InvoiceLine()
    >>> invoice.lines.append(line)
    >>> line.product = product
    >>> line.quantity = 5
    >>> line.unit_price = Decimal('20')
    >>> invoice.click('post')
    >>> invoice.total_amount
    Decimal('110.00')

Configure cabal collect::

    >>> CollectConfig = Model.get('payment_collect.configuration')
    >>> collect_config = CollectConfig(1)
    >>> collect_config.payment_method_cabal = payment_method
    >>> collect_config.cabal_company_code = '98765432112'
    >>> collect_config.save()

Generate cabal collect::

    >>> Period = Model.get('account.period')
    >>> payment_collect = Wizard('payment.collect.send')
    >>> payment_collect.form.csv_format = False
    >>> payment_collect.form.periods.append(Period(period.id))
    >>> payment_collect.form.expiration_date = datetime.date(2021, 1, 15)
    >>> payment_collect.form.paymode_type = 'payment.paymode.cabal'
    >>> fecha = datetime.date(2021, 1, 1)
    >>> context = {
    ...     'company': company.id,
    ...     'date': period.end_date,
    ...     }
    >>> with config.set_context(context):
    ...     payment_collect.execute('generate_collect')
    >>> collect, = payment_collect.actions[0]
    >>> collect.monto_total
    Decimal('330.00')
    >>> collect.cantidad_registros == 2
    True
    >>> attachment = collect.attachments[1]
    >>> with file_open('payment_collect_cabal/tests/COPYTAPS.txt', 'rb') as f:
    ...     attachment.data == f.read()
    True
