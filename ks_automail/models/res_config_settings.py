# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # These fields are used to display/manage configurations in settings
    # The actual configurations are stored in ks.automail.config model
    ks_automail_config_ids = fields.Many2many(
        'ks.automail.config',
        string='Email Configurations',
        compute='_compute_ks_automail_config_ids',
        inverse='_inverse_ks_automail_config_ids',
        help='Global email configurations for different zones',
    )

    @api.depends()
    def _compute_ks_automail_config_ids(self):
        """Load all active configurations"""
        for record in self:
            record.ks_automail_config_ids = self.env['ks.automail.config'].search([
                ('active', '=', True)
            ])

    def _inverse_ks_automail_config_ids(self):
        """This is a display-only field, so inverse does nothing"""
        pass

