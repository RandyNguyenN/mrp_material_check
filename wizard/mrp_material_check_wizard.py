from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MrpMaterialCheckWizardLine(models.TransientModel):
    _name = 'mrp.material.check.wizard.line'
    _description = 'Material shortage detail line'

    wizard_id = fields.Many2one('mrp.material.check.wizard', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Component', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='Unit', readonly=True)
    qty_needed = fields.Float(string='Needed', readonly=True, digits='Product Unit of Measure')
    qty_available = fields.Float(string='Available', readonly=True, digits='Product Unit of Measure')
    shortage = fields.Float(string='Shortage', readonly=True, digits='Product Unit of Measure')


class MrpMaterialCheckWizard(models.TransientModel):
    _name = 'mrp.material.check.wizard'
    _description = 'Insufficient materials confirmation wizard'

    production_id = fields.Many2one('mrp.production', string='Production Order', readonly=True)
    mode = fields.Selection(
        selection=[('warn', 'Warn'), ('block', 'Block')],
        readonly=True,
    )
    line_ids = fields.One2many(
        'mrp.material.check.wizard.line', 'wizard_id', string='Shortages', readonly=True
    )
    can_bypass = fields.Boolean(compute='_compute_can_bypass')

    @api.depends('mode')
    def _compute_can_bypass(self):
        is_manager = self.env.user.has_group('mrp.group_mrp_manager')
        for wiz in self:
            wiz.can_bypass = wiz.mode == 'warn' or is_manager

    def action_proceed(self):
        self.ensure_one()
        if not self.can_bypass:
            raise UserError(
                _('Only Manufacturing Managers can bypass the material check in Block mode.')
            )
        result = self.production_id.with_context(skip_material_check=True).button_mark_done()
        if result and isinstance(result, dict) and result.get('type'):
            return result
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}
