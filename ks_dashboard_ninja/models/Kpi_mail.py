# -*- coding: utf-8 -*-

from odoo import models, fields


class KpSendMail(models.Model):
    _name = 'ks_dashboard_ninja.kpi_mail'
    _description = 'Dashboard Ninja Kpi mail'

    name = fields.Char(string="Email To:")
