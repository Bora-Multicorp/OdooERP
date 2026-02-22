# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ImeiValidationWizard(models.TransientModel):
    _name = 'imei.validation.wizard'
    _description = 'IMEI Validation Wizard'

    picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string="Receipt",
        required=True,
        readonly=True,
    )
    
    line_ids = fields.One2many(
        comodel_name='imei.validation.line',
        inverse_name='wizard_id',
        string="Mismatch Lines",
    )
    
    total_mismatches = fields.Integer(
        string="Total Mismatches",
        compute='_compute_totals',
    )
    
    missing_count = fields.Integer(
        string="Missing",
        compute='_compute_totals',
    )
    
    wrong_count = fields.Integer(
        string="Wrong",
        compute='_compute_totals',
    )
    
    extra_count = fields.Integer(
        string="Extra",
        compute='_compute_totals',
    )

    def action_validate(self):
        self.ensure_one()
        return self.picking_id.with_context(
            skip_imei_validation=True
        ).button_validate()

    @api.depends('line_ids', 'line_ids.mismatch_type')
    def _compute_totals(self):
        for wizard in self:
            wizard.total_mismatches = len(wizard.line_ids)
            wizard.missing_count = len(wizard.line_ids.filtered(lambda l: l.mismatch_type == 'missing'))
            wizard.wrong_count = len(wizard.line_ids.filtered(lambda l: l.mismatch_type == 'wrong'))
            wizard.extra_count = len(wizard.line_ids.filtered(lambda l: l.mismatch_type == 'extra'))

    def action_close(self):
        """Close the wizard without any action."""
        return {'type': 'ir.actions.act_window_close'}


class ImeiValidationLine(models.TransientModel):
    _name = 'imei.validation.line'
    _description = 'IMEI Validation Line'

    wizard_id = fields.Many2one(
        comodel_name='imei.validation.wizard',
        string="Wizard",
        required=True,
        ondelete='cascade',
    )
    
    product_id = fields.Many2one(
        comodel_name='product.product',
        string="Product",
        readonly=True,
    )
    
    expected_imei = fields.Char(
        string="Expected IMEI",
        readonly=True,
    )
    
    expected_imei2 = fields.Char(
        string="Expected IMEI 2",
        readonly=True,
    )
    
    scanned_imei = fields.Char(
        string="Scanned IMEI",
        readonly=True,
    )
    
    scanned_imei2 = fields.Char(
        string="Scanned IMEI 2",
        readonly=True,
    )
    
    mismatch_type = fields.Selection([
        ('missing', 'Missing'),
        ('wrong', 'Wrong'),
        ('extra', 'Extra'),
    ], string="Mismatch Type", readonly=True)
    
    mismatch_type_display = fields.Char(
        string="Issue",
        compute='_compute_mismatch_type_display',
    )

    @api.depends('mismatch_type')
    def _compute_mismatch_type_display(self):
        type_labels = {
            'missing': _('IMEI Not Scanned'),
            'wrong': _('Wrong IMEI'),
            'extra': _('Unexpected IMEI'),
        }
        for line in self:
            line.mismatch_type_display = type_labels.get(line.mismatch_type, '')

