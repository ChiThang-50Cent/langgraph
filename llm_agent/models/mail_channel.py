# -*- coding: utf-8 -*-
# Part of Invitech. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Channel(models.Model):
    _inherit = 'mail.channel'

    thread_number = fields.Char(string='Thread ID')

    def execute_command_help(self, **kwargs):
        super().execute_command_help(**kwargs)
        self.env['ims.agent.bot']._apply_logic(self, kwargs, command="help")
