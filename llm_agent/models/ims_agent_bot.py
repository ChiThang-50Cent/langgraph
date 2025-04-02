# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailBot(models.AbstractModel):
    _name = 'ims.agent.bot'
    _description = 'IMS Agent Bot'

    _client = None

    def _apply_logic(self, record, values, command=None):
        """Apply bot logic to generate an answer (or not) for the user
        The logic will only be applied if agent is in a chat with a user or
        if someone pinged agent.

         :param record: the mail_thread (or mail_channel) where the user
            message was posted/agent will answer.
         :param values: msg_values of the message_post or other values needed\
             by logic
         :param command: the name of the called command if the logic is not\
             triggered by a message_post
        """
        ims_agent_bot_id = self.env['ir.model.data']._xmlid_to_res_id(
            'llm_agent.partner_ims_agent_bot'
        )
        if (
            len(record) != 1
            or values.get('author_id') == ims_agent_bot_id
            or values.get('message_type') != 'comment'
            and not command
        ):
            return

        if not self._is_bot_in_private_channel(record):
            return

        body = (
            values.get('body', '')
            .replace('\xa0', ' ')
            .strip()
            # .lower()
            .strip('.!')
        )

        if self._process_custom_command(record, body):
            return

        message_type = 'comment'
        subtype_id = self.env['ir.model.data']._xmlid_to_res_id(
            'mail.mt_comment'
        )

        if hasattr(self, 'with_delay') and False:
            self.with_delay().get_then_post_answer(
                record, body, ims_agent_bot_id, message_type, subtype_id
            )
        else:
            self.get_then_post_answer(
                record, body, ims_agent_bot_id, message_type, subtype_id
            )

    def get_then_post_answer(self, record, body, author_id, message_type, subtype_id):
        answer = self._get_answer(record, body)
        query_result = self._get_query_result(record, body)
        if query_result:
            record.with_context(
                mail_create_nosubscribe=True
            ).sudo().message_post(
                body=query_result,
                author_id=author_id,
                message_type=message_type,
                subtype_id=subtype_id,
            )
        if answer:
            record.with_context(
                mail_create_nosubscribe=True
            ).sudo().message_post(
                body=answer,
                author_id=author_id,
                message_type=message_type,
                subtype_id=subtype_id,
            )

    def _get_answer(self, record, body):
        client = self.env['langgraph.client']
        thread_id = client._get_or_create_thread(record.thread_number)
        record.thread_number = thread_id
        output = client._get_then_clean_output(thread_id, body)
        if output:
            return output
        return "I'm sorry, I cannot help you with that."

    def _get_query_result(self, record, body):
        client = self.env['langgraph.client']
        thread_id = client._get_or_create_thread(record.thread_number)
        record.thread_number = thread_id
        output = client._get_query_result(thread_id)
        return output

    def _is_bot_pinged(self, values):
        ims_agent_bot_id = self.env['ir.model.data']._xmlid_to_res_id(
            'llm_agent.partner_ims_agent_bot'
        )
        return ims_agent_bot_id in values.get('partner_ids', [])

    def _is_bot_in_private_channel(self, record):
        ims_agent_bot_id = self.env['ir.model.data']._xmlid_to_res_id(
            'llm_agent.partner_ims_agent_bot'
        )
        if record._name == 'mail.channel' and record.channel_type == 'chat':
            return (
                ims_agent_bot_id
                in record.with_context(
                    active_test=False
                ).channel_partner_ids.ids
            )
        return False

    def _process_custom_command(self, record, body):
        """Process custom commands and return the output if any.
        """
        if body == '/new':
            # Clear chat history and start a new thread
            self._create_new_conversation(record)
            return True
        elif body == '/clear':
            # Clear chat history
            self._create_new_conversation(record, clear_history=True)
            return True

        return False

    def _create_new_conversation(self, record, clear_history=False):
        thread_id = self.env['langgraph.client']._get_or_create_thread()
        record.thread_number = thread_id
        if clear_history:
            self._clear_conversation(record)

    def _get_last_conversation(self, record):
        return (
            self.env['mail.channel']
            .search([('id', '=', record.id)])
            .message_ids.ids
        )

    def _clear_conversation(self, record):
        last_conversation = self._get_last_conversation(record)
        self.env['mail.message'].search(
            [('id', 'in', last_conversation[1:])], order='id desc'
        ).unlink()

    # def _is_help_requested(self, body):
    #     """Returns whether a message linking to the documentation and videos
    #     should be sent back to the user.
    #     """
    #     return (
    #         any(token in body for token in ['help', _('help'), '?']) or False
    #     )
