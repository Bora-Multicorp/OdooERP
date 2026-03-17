# -*- coding: utf-8 -*-

def migrate(cr, version):
    """
    Remove the old global blocking rule that was blocking all users
    """
    cr.execute("""
        DELETE FROM ir_rule 
        WHERE name = 'Payments: Block All Except KS Payment Access'
        AND model_id IN (SELECT id FROM ir_model WHERE model = 'account.payment')
    """)
    cr.execute("""
        DELETE FROM ir_model_data 
        WHERE name = 'payment_rule_block_all_except_ks_access'
        AND module = 'ks_payment_access_control'
    """)

