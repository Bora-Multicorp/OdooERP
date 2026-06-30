# -*- coding: utf-8 -*-
import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """
    Post-installation hook:
    1. Recompute is_parent_account and layered_depth for all existing accounts.
    2. Log installation message.
    """
    _logger.info('layered_coa: Running post_init_hook — recomputing hierarchy fields...')

    AccountAccount = env['account.account']
    all_accounts = AccountAccount.search([])

    _logger.info('layered_coa: Recomputing is_parent_account for %d accounts...', len(all_accounts))
    all_accounts._compute_is_parent_account()

    _logger.info('layered_coa: Recomputing layered_depth for %d accounts...', len(all_accounts))
    all_accounts._compute_layered_depth()

    _logger.info('layered_coa: post_init_hook complete.')
