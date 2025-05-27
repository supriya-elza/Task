from odoo import models
from odoo.tools import float_compare
from odoo.tools.misc import groupby

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _assign_picking(self):
        grouped_moves = groupby(self, key=lambda m: m._key_assign_picking())
        for group, moves in grouped_moves:
            moves = self.env['stock.move'].concat(*moves)
            new_picking = False
            picking = moves[0]._search_picking_for_assignation()
            if picking:
                vals = {}
                if any(picking.partner_id.id != m.partner_id.id
                       for m in moves):
                    vals['partner_id'] = False
                if any(picking.origin != m.origin for m in moves):
                    vals['origin'] = False
                if vals:
                    picking.write(vals)
            else:
                moves = moves.filtered(lambda m: float_compare(
                    m.product_uom_qty, 0.0, precision_rounding=
                    m.product_uom.rounding) >= 0)
                if not moves:
                    continue
                new_picking = True
                pick_values = moves._get_new_picking_values()
                sale_order = self.env['sale.order'].search([
                    ('name', '=', pick_values['origin'])])
                if sale_order:
                    move_line = sorted(moves,key=lambda x: x.product_id.id)
                    for product_id, lines in groupby(move_line,
                                                       key=lambda
                                                               x: x.product_id):
                        new_moves = self.env['stock.move'].concat(*lines)
                        picking = picking.create(
                            new_moves._get_new_picking_values())
                        new_moves.write({'picking_id': picking.id})
                        new_moves._assign_picking_post_process(new=new_picking)

                else:
                    picking = picking.create(moves._get_new_picking_values())
                    moves.write({'picking_id': picking.id,
                                 'partner_id': sale_order.partner_id.id})
                    moves._assign_picking_post_process(new=new_picking)
        return True
