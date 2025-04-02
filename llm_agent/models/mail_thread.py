# -*- coding: utf-8 -*-
# Part of Invitech. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _message_post_after_hook(self, message, msg_vals):
        self.env['ims.agent.bot']._apply_logic(self, msg_vals)
        return super(MailThread, self)._message_post_after_hook(
            message, msg_vals
        )
