# -*- coding: utf-8 -*-
# Report source: doc/REPORT_SOURCE_SH001.md
# Row 1 = description (type/behaviour), Row 2 = column name. Total 62 columns.
# Where Row 1 says "Text Box" or "Text box to enter amount" → field is an input field (editable, leave empty).

from odoo import models, fields, api


class SbBrcMaster(models.Model):
    _name = 'sb.brc.master'
    _description = 'SB/BRC Master Report'
    _order = 'date desc, sr_no'
    _rec_name = 'sb_no'

    # System Generated
    sr_no = fields.Integer(string='Sr. No.', default=1, readonly=True, help="System Generated")
    date = fields.Date(string='Date', default=fields.Date.today, required=True, help="System Generated")

    # Invoice (Dropdown – single selection)
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice No',
        domain=[('move_type', '=', 'out_invoice')],
        help="Dropdown to select invoice number",
    )
    sb_no = fields.Char(string='SB No', help="Text Box – input field")
    be_no = fields.Char(string='BE No', help="Text Box – input field")
    consignee = fields.Char(string='Consignee', related='invoice_id.partner_shipping_id.name', store=True, readonly=True, help="Fetched from invoice")
    buyer = fields.Char(string='Buyer', related='invoice_id.partner_id.name', store=True, readonly=True, help="Fetched from invoice")
    awb_number = fields.Char(string='AWB NUMBER', help="Text Box – input field")
    qty_kg = fields.Float(string='QTY (KG)', compute='_compute_qty_unit_rate', store=True, digits=(16, 2), help="Fetched from invoice")
    unit_rate = fields.Float(string='Unit Rate', compute='_compute_qty_unit_rate', store=True, digits=(16, 2), help="Fetched from invoice")
    currency_id = fields.Many2one('res.currency', string='Currency', related='invoice_id.currency_id', store=True, readonly=True, help="Fetched from invoice")
    calendar_date = fields.Date(string='Calendar', help="Calendar/date – input field")
    invoice_amount_usd = fields.Monetary(string='Invoice Amount (USD)', related='invoice_id.amount_total', store=True, currency_field='currency_id', readonly=True, help="Fetched from invoice")
    ex_rate = fields.Float(string='EX Rate', related='invoice_id.currency_id.rate', store=True, digits=(16, 6), readonly=True, help="Exchange rate entered during invoicing")
    sb_rate = fields.Float(string='SB Rate', digits=(16, 6), help="Fetched from invoice")
    amount_inr = fields.Monetary(string='Amount (INR)', compute='_compute_amount_inr', store=True, currency_field='company_currency_id', help="As per formula")
    fob_value_inr = fields.Monetary(string='FOB value (INR)', currency_field='company_currency_id', help="From invoice")
    gst_rate = fields.Char(string='GST Rate', help="From invoice")
    gst_amount = fields.Monetary(string='GST AMOUNT', currency_field='company_currency_id', help="From invoice")
    invoice_value = fields.Monetary(string='Invoice Value', compute='_compute_invoice_value', store=True, currency_field='company_currency_id', help="As per formula")
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    # CHA (Dropdown) and charges – "Text box to enter amount" = leave empty
    cha_id = fields.Many2one('res.partner', string='CHA', domain=[('is_company', '=', True)], help="Dropdown – many to one CHA list")
    for_calculation = fields.Monetary(string='For calculation', currency_field='company_currency_id', help="Text Box to enter amount – input field")
    other_charges = fields.Monetary(string='Other Charges', currency_field='company_currency_id', help="Text Box to enter amount – input field")
    freight = fields.Monetary(string='Freight', currency_field='company_currency_id', help="Text Box to enter amount – input field")
    agency_charges = fields.Monetary(string='Agency Charges', currency_field='company_currency_id', help="Text Box to enter amount – input field")
    bus_charges_fumigation = fields.Monetary(string='Bus Charges & FUMIGATION', currency_field='company_currency_id', help="Text Box to enter amount – input field")
    terminal_handling = fields.Monetary(string='Terminal handling', currency_field='company_currency_id', help="Text Box to enter amount – input field")
    drawback_charges = fields.Monetary(string='Drawback Charges', currency_field='company_currency_id', help="Text Box to enter amount – input field")
    mis_charges = fields.Monetary(string='MIS Charges', currency_field='company_currency_id', help="Text Box to enter amount – input field")
    gate_pass = fields.Monetary(string='Gate Pass', currency_field='company_currency_id', help="Text Box to enter amount – input field")
    transportation_to_air_cargo = fields.Monetary(string='Transportation to Air Cargo', currency_field='company_currency_id', help="Text Box to enter amount – input field")
    load_unload = fields.Monetary(string='Load / Unload', currency_field='company_currency_id', help="Text Box to enter amount – input field")
    pallet_charges = fields.Monetary(string='Pallet Charges', currency_field='company_currency_id', help="Text Box to enter amount – input field")
    other_charges_2 = fields.Monetary(string='Other Charges (2)', currency_field='company_currency_id', help="Text Box to enter amount – input field")
    local_warehouse = fields.Monetary(string='Local Warehouse', currency_field='company_currency_id', help="Text Box to enter amount – input field")
    insurance = fields.Monetary(string='Insurance', currency_field='company_currency_id', help="Text Box to enter amount – input field")
    total_charges = fields.Monetary(string='Total', compute='_compute_total_charges', store=True, currency_field='company_currency_id', help="As per formula")

    # Additional – Text box / from PL
    no_of_pallets = fields.Char(string='No. Of PALLATS', help="Text Box / from PL – input field")
    weight_as_per_awb = fields.Float(string='Weight as per AWB', digits=(16, 2), help="Text Box – input field")
    for_planning_costing = fields.Float(string='For Planing Costing', compute='_compute_planning_costing', store=True, digits=(16, 2), help="Same as per formula")
    average_for_costing = fields.Float(string='Average For Costing', compute='_compute_average_costing', store=True, digits=(16, 2), help="Same as per formula")
    airlines = fields.Char(string='Airlines', help="Text Box – input field")
    country_id = fields.Many2one('res.country', string='Country', help="Dropdown")
    port = fields.Char(string='PORT', help="Dropdown")

    # BRC
    brc_status = fields.Selection([('yes', 'YES'), ('no', 'NO')], string='BRC Status', help="Dropdown")
    brc_date = fields.Date(string='BRC DATE', help="Calendar/date – input field")
    brc_no = fields.Char(string='BRC NO', help="Text Box – input field")
    brc_amount_usd = fields.Monetary(string='BRC AMOUNT USD', currency_field='currency_id', help="Input field – enter when received")
    still_in_realization = fields.Monetary(string='Still in Realization', compute='_compute_still_in_realization', store=True, currency_field='currency_id', help="As per formula")
    sb_fob_value = fields.Monetary(string='SB FOB value', currency_field='company_currency_id', help="Text Box – input field")

    # Fresh / Activated / Other Country (from Packing list / goods outward)
    fresh = fields.Monetary(string='Fresh', currency_field='company_currency_id', help="From Packing list / goods outward – Only for goods made in India")
    activated = fields.Monetary(string='Activated', currency_field='company_currency_id', help="From Packing list / goods outward – other than Made in India")
    other_country = fields.Monetary(string='Other Country', currency_field='company_currency_id', help="From Country of Origin / Made in – other than Made in India")

    # RODTEP
    rodtep_amount = fields.Monetary(string='RODTEP Amount', compute='_compute_rodtep_amount', store=True, currency_field='company_currency_id', help="Calculated as per formula")
    rodtep_amount_per_sb = fields.Monetary(string='RODTEP AMOUNT PER SB', currency_field='company_currency_id', help="Input field")

    # Drawback (DBK)
    dbk_percentage = fields.Selection([('yes', 'YES'), ('no', 'NO')], string='DBK %', help="Dropdown (yes/no)")
    dbk_claimed = fields.Selection([('yes', 'YES'), ('no', 'NO')], string='DBK Claimed', help="DBK claimed only for fresh units")
    dbk_as_per_calculation = fields.Monetary(string='DBK as Per Calculation', compute='_compute_dbk_calculation', store=True, currency_field='company_currency_id', help="4% of FOB Value")
    dbk_amount = fields.Monetary(string='DBK Amount', currency_field='company_currency_id', help="Text Box – input field")
    application_status = fields.Char(string='Application Status', help="Text Box – input field")
    drawback_received = fields.Selection([('yes', 'YES'), ('no', 'NO')], string='Drawback Received', help="Dropdown (Yes/No)")
    received_date = fields.Date(string='Received Date', help="Text Box – input field")
    received_amount = fields.Monetary(string='Received Amount', currency_field='company_currency_id', help="Text Box – input field")
    remarks = fields.Text(string='Remarks', help="Text Box – input field")

    # FOB VALUE (column 65 in report - same as FOB value INR)
    fob_value = fields.Monetary(related='fob_value_inr', string='FOB VALUE', currency_field='company_currency_id', readonly=True)

    # CHA Invoice (fetched from invoice received from CHA for this shipment)
    tax_able_amt = fields.Monetary(string='Tax Able Amt', currency_field='company_currency_id', help="Fetched from CHA invoice – input field")
    gst_amt = fields.Monetary(string='GST Amt', currency_field='company_currency_id', help="Fetched from CHA invoice – input field")
    tds_amt = fields.Monetary(string='TDS Amt', currency_field='company_currency_id', help="Fetched from CHA invoice – input field")
    net_balance_payable = fields.Monetary(string='Net Balance Payable', compute='_compute_net_balance_payable', store=True, currency_field='company_currency_id', help="Formula = Taxable + GST")

    @api.depends('invoice_id', 'invoice_id.invoice_line_ids', 'invoice_id.invoice_line_ids.quantity', 'invoice_id.invoice_line_ids.price_subtotal')
    def _compute_qty_unit_rate(self):
        for r in self:
            if r.invoice_id and r.invoice_id.invoice_line_ids:
                lines = r.invoice_id.invoice_line_ids.filtered(lambda l: l.quantity > 0)
                r.qty_kg = sum(lines.mapped('quantity'))
                tot = sum(lines.mapped('price_subtotal'))
                r.unit_rate = tot / r.qty_kg if r.qty_kg else 0.0
            else:
                r.qty_kg = 0.0
                r.unit_rate = 0.0

    @api.depends('invoice_amount_usd', 'ex_rate')
    def _compute_amount_inr(self):
        for r in self:
            r.amount_inr = (r.invoice_amount_usd * r.ex_rate) if (r.invoice_amount_usd and r.ex_rate) else 0.0

    @api.depends('fob_value_inr', 'gst_amount')
    def _compute_invoice_value(self):
        for r in self:
            r.invoice_value = (r.fob_value_inr or 0.0) + (r.gst_amount or 0.0)

    @api.depends('for_calculation', 'other_charges', 'freight', 'agency_charges', 'bus_charges_fumigation',
                 'terminal_handling', 'drawback_charges', 'mis_charges', 'gate_pass', 'transportation_to_air_cargo',
                 'load_unload', 'pallet_charges', 'other_charges_2', 'local_warehouse', 'insurance')
    def _compute_total_charges(self):
        for r in self:
            r.total_charges = (
                (r.for_calculation or 0) + (r.other_charges or 0) + (r.freight or 0) + (r.agency_charges or 0) +
                (r.bus_charges_fumigation or 0) + (r.terminal_handling or 0) + (r.drawback_charges or 0) +
                (r.mis_charges or 0) + (r.gate_pass or 0) + (r.transportation_to_air_cargo or 0) +
                (r.load_unload or 0) + (r.pallet_charges or 0) + (r.other_charges_2 or 0) +
                (r.local_warehouse or 0) + (r.insurance or 0)
            )

    @api.depends('total_charges', 'qty_kg')
    def _compute_planning_costing(self):
        for r in self:
            r.for_planning_costing = r.total_charges / r.qty_kg if r.qty_kg else 0.0

    @api.depends('for_planning_costing')
    def _compute_average_costing(self):
        for r in self:
            r.average_for_costing = r.for_planning_costing

    @api.depends('invoice_amount_usd', 'brc_amount_usd')
    def _compute_still_in_realization(self):
        for r in self:
            r.still_in_realization = (r.invoice_amount_usd or 0.0) - (r.brc_amount_usd or 0.0)

    @api.depends('fob_value_inr')
    def _compute_rodtep_amount(self):
        for r in self:
            r.rodtep_amount = (r.fob_value_inr or 0.0) * 0.05

    @api.depends('fob_value_inr', 'fresh')
    def _compute_dbk_calculation(self):
        for r in self:
            r.dbk_as_per_calculation = (r.fob_value_inr or 0.0) * 0.04 if r.fresh else 0.0

    @api.depends('tax_able_amt', 'gst_amt')
    def _compute_net_balance_payable(self):
        for r in self:
            r.net_balance_payable = (r.tax_able_amt or 0.0) + (r.gst_amt or 0.0)

    @api.model
    def create(self, vals):
        if not vals.get('sr_no'):
            last = self.search([], order='sr_no desc', limit=1)
            vals['sr_no'] = (last.sr_no or 0) + 1
        return super().create(vals)
