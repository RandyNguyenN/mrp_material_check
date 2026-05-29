from odoo import models, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def button_mark_done(self):
        if self.env.context.get('skip_material_check'):
            return super().button_mark_done()

        for production in self:
            shortages = production._get_material_shortages()
            if shortages:
                return production._open_material_check_wizard(shortages)

        return super().button_mark_done()

    def _get_material_shortages(self):
        """Return list of dicts for components with insufficient stock."""
        shortages = []
        moves = self.move_raw_ids.filtered(
            lambda m: m.state not in ('done', 'cancel')
        )
        for move in moves:
            qty_needed = move.product_uom_qty

            # Quantity on-hand at the source location in the product's base UoM
            qty_in_loc = move.product_id.with_context(
                location=move.location_id.id
            ).qty_available

            # Convert to the move's UoM if different
            if move.product_uom != move.product_id.uom_id:
                qty_in_loc = move.product_id.uom_id._compute_quantity(
                    qty_in_loc, move.product_uom
                )

            if qty_in_loc < qty_needed:
                shortages.append({
                    'product_id': move.product_id.id,
                    'qty_needed': qty_needed,
                    'qty_available': max(qty_in_loc, 0.0),
                    'shortage': qty_needed - max(qty_in_loc, 0.0),
                    'uom_id': move.product_uom.id,
                })

        return shortages

    def _open_material_check_wizard(self, shortages):
        mode = self.env['ir.config_parameter'].sudo().get_param(
            'mrp_material_check.mode', 'warn'
        )
        wizard = self.env['mrp.material.check.wizard'].create({
            'production_id': self.id,
            'mode': mode,
            'line_ids': [(0, 0, line) for line in shortages],
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.material.check.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
            'name': _('Insufficient Materials'),
        }
