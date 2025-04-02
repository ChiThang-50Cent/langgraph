import json
import logging
import re

import markdown
import requests
from odoo import models

_logger = logging.getLogger(__name__)


class LanggraphClient(models.AbstractModel):
    _name = 'langgraph.client'
    _description = 'Langgraph Client'

    url = 'http://127.0.0.1:2024'
    assistant_id = 'agent'

    # TODO: change url to property

    def _get_or_create_thread(self, thread_id=None):
        if thread_id:
            return thread_id

        headers = {'Content-Type': 'application/json'}
        payload = {'thread_id': '', 'metadata': {}, 'if_exists': 'do_nothing'}

        response = requests.post(
            f'{self.url}/threads', json=payload, headers=headers
        )
        if response.status_code == 200:
            return response.json().get('thread_id')

        _logger.error('[LLM-Agent] - Error when getting or creating thread.')
        return None

    def _create_run_wait_output(self, thread_id, text):
        headers = {'Content-Type': 'application/json'}

        payload = {
            'assistant_id': self.assistant_id,
            'checkpoint': {
                'thread_id': thread_id,
            },
            'stream_mode': ['values'],
        }

        input = {"messages": [{"role": "user", "content": text}]}
        payload['input'] = input

        response = requests.post(
            f'{self.url}/threads/{thread_id}/runs/wait',
            json=payload,
            headers=headers,
            stream=True,
        )

        if response.status_code == 200:
            return response.json()

        _logger.error('[LLM-Agent] - Error when creating run'
                     ' and waiting for output.')
        return None

    def _get_thread_state(self, thread_id):
        if not thread_id:
            return None

        response = requests.get(
            f'{self.url}/threads/{thread_id}/state'
        )

        if response.status_code == 200:
            return response.json()

        _logger.error('[LLM-Agent] - Error when getting thread state.')
        return None

    def _get_thread_answer(self, thread_id):
        if not thread_id:
            return None

        response = self._get_thread_state(thread_id)
        if response and (ans := response.get('values', {}).get('answer')):
            return json.loads(ans)

        _logger.error('[LLM-Agent] - Error when getting thread answer.')
        return None

    def _clean_output(self, output):
        if not output or not output.get('messages'):
            _logger.error('[LLM-Agent] - No messages in output')
            return None

        messages = output.get('messages')[-1]
        if not messages.get('type') or messages.get('type') != 'ai':
            _logger.error('[LLM-Agent] - No AI message in output')
            return None

        return messages.get('content')

    def _markdown_to_html(self, md):
        if not md:
            return md
        html = markdown.markdown(
            md, extensions=['extra', 'codehilite', 'nl2br']
        )
        return html

    def _get_then_clean_output(self, thread_id, text):
        output = self._create_run_wait_output(thread_id, text)
        output = self._clean_output(output)
        return self._markdown_to_html(output)

    def _get_query_result(self, thread_id):
        res = self._get_thread_answer(thread_id)
        return self._dict_list_to_html_table(res)

    def _dict_list_to_html_table(self, dict_list):
        """Convert a list of dictionaries to HTML table format.

        Args:
            dict_list (list): List of dictionaries to convert

        Returns:
            str: HTML table representation of the data
        """
        if not dict_list or not isinstance(dict_list, list):
            return ''

        # Get all unique keys from all dictionaries
        all_keys = set()
        for d in dict_list:
            all_keys.update(d.keys())
        all_keys = sorted(list(all_keys))

        # Build HTML table with styles
        html = [
            '<table border="1" class="dataframe" style="border-collapse: collapse;">'
        ]

        # Header row
        html.append('<thead>')
        html.append('<tr>')
        for key in all_keys:
            html.append(
                f'<th style="text-align: center; border: 1px solid #ddd; padding: 8px;">{key}</th>'
            )
        html.append('</tr>')
        html.append('</thead>')

        # Data rows
        html.append('<tbody>')
        for item in dict_list[:10]:
            html.append('<tr>')
            for key in all_keys:
                value = item.get(key, '')
                html.append(
                    f'<td style="border: 1px solid #ddd; padding: 8px;">{value}</td>'
                )
            html.append('</tr>')
        html.append('</tbody>')

        html.append('</table>')
        return '\n'.join(html)
