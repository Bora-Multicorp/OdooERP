-- SQL script to remove the old blocking rule
-- Run this in your database to fix the access issue

-- Delete the old global blocking rule
DELETE FROM ir_rule 
WHERE name = 'Payments: Block All Except KS Payment Access'
AND model_id IN (SELECT id FROM ir_model WHERE model = 'account.payment');

-- Delete the ir_model_data entry for the old rule
DELETE FROM ir_model_data 
WHERE name = 'payment_rule_block_all_except_ks_access'
AND module = 'ks_payment_access_control';

-- Refresh the rule cache
UPDATE ir_rule SET active = active;

