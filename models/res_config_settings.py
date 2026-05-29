from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    mrp_material_check_mode = fields.Selection(
        selection=[
            ('warn', 'Warn — show popup but allow anyone to continue'),
            ('block', 'Block — only Manufacturing Managers can bypass'),
        ],
        string='Insufficient Material Behaviour',
        default='warn',
        config_parameter='mrp_material_check.mode',
    )
