{
    'name': 'MRP Material Check',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing',
    'summary': 'Block or warn before producing when components are insufficient — popup lists each shortage.',
    'description': """
MRP Material Check for Odoo 18 (Free / LGPL-3)
===============================================
- Intercepts the "Produce" button on manufacturing orders
- Checks if every component has enough stock at the source location
- Shows a popup listing each short component: needed / available / shortage
- Two modes (set in Manufacturing > Configuration > Settings):
    * Warn — shows the popup but lets anyone continue
    * Block — only users with the Manufacturing Manager role can bypass
    """,
    'author': 'SunMesa Labs',
    'website': 'https://odoo.sunmesalabs.com',
    'support': 'randy@sunmesalabs.com',
    'license': 'LGPL-3',
    'depends': ['mrp'],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp-material-check-wizard-views.xml',
        'views/res-config-settings-views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'images': ['static/description/banner.gif'],
}
