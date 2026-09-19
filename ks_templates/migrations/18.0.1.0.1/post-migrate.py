# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Hide the standard 'PDF' (account_invoices) from the invoice Download menu."""
    cr.execute("""
        UPDATE ir_act_report_xml
        SET binding_model_id = NULL
        WHERE id = (
            SELECT res_id FROM ir_model_data
            WHERE module = 'account' AND name = 'account_invoices'
            LIMIT 1
        )
    """)
