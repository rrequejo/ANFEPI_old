# -*- coding: utf-8 -*-

from . import models

from odoo import _
from odoo import api, SUPERUSER_ID


# TODO: Apply proper fix & remove in master
def pre_init_hook(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    cr.execute("""
    			alter table account_move add column stored_sat_uuid text;
    			""")