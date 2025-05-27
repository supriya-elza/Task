from odoo import models, fields, api,_
from lxml import etree
from datetime import date
from odoo.exceptions import UserError
import time




class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    manager_reference = fields.Text(string="Manager Reference")
    auto_work_flow = fields.Boolean(string="Auto Workflow")


    @api.model
    def get_views(self, views, options=None):
        res = super().get_views(views, options)
        views_type = ['list', 'form']
        for type in views_type:
            arch = res['views'].get(type, {}).get('arch')
            if arch:
                doc = etree.fromstring(arch)
                for field in doc.xpath("//field[@name='manager_reference']"):
                    if self.env.user.has_group('bi_sale_order.sale_admin'):
                        field.set('readonly', '0')
                    else:
                        field.set('readonly', '1')
                arch = etree.tostring(doc, encoding='unicode')
                res['views'].setdefault(type, {})['arch'] = arch 
        return res

    

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for rec in self:
            sale_order_limit = self.env['res.config.settings'].sudo().search([]).sale_order_limit
            if rec.amount_total > sale_order_limit and not self.env.user.has_group('bi_sale_order.sale_admin'):
                raise UserError(_('Confirmation of orders exceeding the limit is exclusively allowed for Sales Admins.'))
            if rec.auto_work_flow == True:
                invoice = rec._create_invoices()
                invoice.action_post()
                picking_ids = rec.picking_ids
                for line in rec.order_line:
                    if line.product_id.type == 'product' and line.product_uom_qty > line.product_id.free_qty:
                        return res 
                    for picking in picking_ids:
                        if picking.state == 'assigned': 
                            picking.button_validate()
                ctx = {"active_model": "account.move", "active_ids": [invoice.id]}
                register_payments = self.env['account.payment.register'].with_context(**ctx).create(
                    {
                        'payment_date': date.today(),
                    }
                )
                action = register_payments.action_create_payments()
        return res
        
