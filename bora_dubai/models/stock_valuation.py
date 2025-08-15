from odoo import models, fields, api

class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    usd_currency_id = fields.Many2one('res.currency', string="USD Currency",
                                      default=lambda self: self.env.ref('base.USD'), readonly=True)
    usd_value = fields.Monetary(string="Value in USD", currency_field='usd_currency_id', compute='_compute_usd_value', store=True)

    is_aed_company = fields.Boolean(
        string="Is AED Company",
        compute='_compute_is_aed_company',
        store=True
    )

    @api.depends('value', 'create_date')
    def _compute_usd_value(self):
        usd_currency = self.env.ref('base.USD')
        for record in self:
            company_currency = record.company_id.currency_id
            date = record.create_date.date() if record.create_date else fields.Date.today()
            record.usd_value = company_currency._convert(
                record.value,
                usd_currency,
                record.company_id,
                date,
            )

    @api.depends('company_id.currency_id')
    def _compute_is_aed_company(self):
        for record in self:
            record.is_aed_company = record.company_id.currency_id.name == 'AED'
