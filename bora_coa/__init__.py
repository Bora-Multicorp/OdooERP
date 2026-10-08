# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """
    Executed automatically when the module is installed.
    Updates existing accounts (600292->900001, 600291->900002),
    creates new accounts (900003, 900004), updates default mappings (ir.default),
    and updates existing contact receivable/payable accounts based on country match.
    """
    env['account.account'].sudo()._setup_bora_coa_all()
