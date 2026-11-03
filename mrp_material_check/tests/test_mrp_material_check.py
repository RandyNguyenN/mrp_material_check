from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('mrp_material_check', 'post_install', '-at_install')
class TestMrpMaterialCheck(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        # Storable product (finished good) — Odoo 18: type='consu' + is_storable=True
        cls.product_finished = cls.env['product.product'].create({
            'name': 'Test Finished Product',
            'type': 'consu',
            'is_storable': True,
        })

        # Storable component — must be storable so qty_available is tracked
        cls.component = cls.env['product.product'].create({
            'name': 'Test Component',
            'type': 'consu',
            'is_storable': True,
        })

        cls.uom_unit = cls.env.ref('uom.product_uom_unit')

        # BOM: 1 finished product needs 5 components
        cls.bom = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.product_finished.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [(0, 0, {
                'product_id': cls.component.id,
                'product_qty': 5.0,
            })],
        })

        cls.location_stock = cls.env.ref('stock.stock_location_stock')

    def _make_production(self, qty=1.0):
        production = self.env['mrp.production'].create({
            'product_id': self.product_finished.id,
            'product_qty': qty,
            'bom_id': self.bom.id,
        })
        production.action_confirm()
        return production

    def _set_stock(self, product, qty):
        """Set on-hand stock via quant create (qty > 0 only — 0 = no quant needed)."""
        if qty <= 0:
            return
        existing = self.env['stock.quant'].search([
            ('product_id', '=', product.id),
            ('location_id', '=', self.location_stock.id),
        ], limit=1)
        if existing:
            existing.sudo().write({'quantity': qty})
        else:
            self.env['stock.quant'].sudo().create({
                'product_id': product.id,
                'location_id': self.location_stock.id,
                'quantity': qty,
            })

    def _set_mode(self, mode):
        self.env['ir.config_parameter'].sudo().set_param(
            'mrp_material_check.mode', mode
        )

    # ------------------------------------------------------------------
    # Warn mode
    # ------------------------------------------------------------------

    def test_warn_mode_sufficient_stock_opens_no_wizard(self):
        """When stock is sufficient, button_mark_done must NOT open our wizard."""
        self._set_stock(self.component, 10.0)
        self._set_mode('warn')
        production = self._make_production()
        production.action_assign()

        # Set done quantities so Odoo doesn't block on immediate transfer
        for move in production.move_raw_ids:
            move.quantity = move.product_uom_qty

        result = production.button_mark_done()
        if isinstance(result, dict):
            self.assertNotEqual(
                result.get('res_model'), 'mrp.material.check.wizard',
                'Wizard must not appear when stock is sufficient',
            )

    def test_warn_mode_insufficient_stock_opens_wizard(self):
        """Warn mode: shortage opens wizard with can_bypass=True for any user."""
        # No stock → all shortage
        self._set_mode('warn')
        production = self._make_production()

        result = production.button_mark_done()

        self.assertIsInstance(result, dict)
        self.assertEqual(result.get('res_model'), 'mrp.material.check.wizard')
        wizard = self.env['mrp.material.check.wizard'].browse(result['res_id'])
        self.assertEqual(wizard.mode, 'warn')
        self.assertTrue(wizard.can_bypass)
        self.assertGreater(len(wizard.line_ids), 0)

    def test_warn_mode_wizard_shows_correct_shortage(self):
        """Wizard line reports needed=5, available=2, shortage=3."""
        self._set_stock(self.component, 2.0)
        self._set_mode('warn')
        production = self._make_production(qty=1.0)  # BOM: 5 units needed

        result = production.button_mark_done()
        wizard = self.env['mrp.material.check.wizard'].browse(result['res_id'])
        line = wizard.line_ids[0]

        self.assertAlmostEqual(line.qty_needed, 5.0, places=2)
        self.assertAlmostEqual(line.qty_available, 2.0, places=2)
        self.assertAlmostEqual(line.shortage, 3.0, places=2)

    # ------------------------------------------------------------------
    # Block mode
    # ------------------------------------------------------------------

    def test_block_mode_regular_user_cannot_bypass(self):
        """Block mode: regular MRP user gets can_bypass=False."""
        self._set_mode('block')
        production = self._make_production()

        mrp_user = self.env['res.users'].create({
            'name': 'MRP User',
            'login': 'mrp_user_test_block@test.com',
            'groups_id': [(6, 0, [self.env.ref('mrp.group_mrp_user').id])],
        })
        result = production.with_user(mrp_user).button_mark_done()

        self.assertIsInstance(result, dict)
        wizard = self.env['mrp.material.check.wizard'].browse(result['res_id'])
        self.assertFalse(wizard.with_user(mrp_user).can_bypass)

    def test_block_mode_manager_can_bypass(self):
        """Block mode: Manufacturing Manager gets can_bypass=True."""
        self._set_mode('block')
        production = self._make_production()

        manager = self.env['res.users'].create({
            'name': 'MRP Manager',
            'login': 'mrp_manager_test_block@test.com',
            'groups_id': [(6, 0, [self.env.ref('mrp.group_mrp_manager').id])],
        })
        result = production.with_user(manager).button_mark_done()

        self.assertIsInstance(result, dict)
        wizard = self.env['mrp.material.check.wizard'].browse(result['res_id'])
        self.assertTrue(wizard.with_user(manager).can_bypass)

    # ------------------------------------------------------------------
    # Skip context
    # ------------------------------------------------------------------

    def test_skip_context_bypasses_wizard(self):
        """skip_material_check context must never open our wizard."""
        self._set_mode('block')
        production = self._make_production()

        for move in production.move_raw_ids:
            move.quantity = move.product_uom_qty

        result = production.with_context(skip_material_check=True).button_mark_done()
        if isinstance(result, dict):
            self.assertNotEqual(result.get('res_model'), 'mrp.material.check.wizard')
