# models/account_move.py
from odoo import models, fields

class AccountMove(models.Model):
    _inherit = "account.move"

    delivery_note_date = fields.Date(string="Delivery Note Date")
    delivery_note = fields.Char(string="Delivery Note")
    despatch_doc_no = fields.Char(string="Dispatch Document no.")
    buyer_date = fields.Date(string="Buyer Date")
