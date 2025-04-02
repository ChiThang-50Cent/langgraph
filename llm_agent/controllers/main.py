import json
import logging

from odoo import SUPERUSER_ID, http
from odoo.api import Environment
from odoo.http import request
from odoo.modules.registry import Registry

_logger = logging.getLogger(__name__)


class LLMAgent(http.Controller):

    @http.route(
        '/llm_agent/table_info/<db_name>/<db_table>',
        auth='public',
        type='http',
        methods=['GET'],
        csrf=False,
    )
    def get_table_info(self, db_name, db_table, **kw):
        try:
            resigtry = Registry(db_name)
            with resigtry.cursor() as cr:
                env = Environment(cr, SUPERUSER_ID, {})
                RES_MODEL = env[db_table.replace('_', '.')]
                res = {}
                res['status'] = 'success'
                res['data'] = {}
                for field, values in RES_MODEL.fields_get(
                    RES_MODEL._fields
                ).items():
                    s_values = [
                        item[0] for item in values.get('selection', [])
                    ]
                    res['data'][field] = (
                        {
                            # 'field_name': field,
                            'field_description': values.get('string', ''),
                            # 'field_type': 'char'
                            # if values.get('type', '') == 'selection'
                            # else values.get('type', ''),
                            'value': s_values[:10],
                            # 'relation': values.get('relation', ''),
                            'help': values.get('help', ''),
                            # 'table_name': db_table,
                            # 'table_description': RES_MODEL._description,
                        }
                    )
                return json.dumps(res, ensure_ascii=False)
        except Exception:
            _logger.error('Database not found: %s', db_name, exc_info=True)
            return json.dumps(
                {'status': 'error', 'error': db_table}
            )

    @http.route(
        '/llm_agent/patient/<db_name>/<patient_code>',
        auth='public',
        type='http',
        methods=['GET'],
        csrf=False,
    )
    def get_patient_infomation(self, db_name, patient_code, **kw):
        try:
            resigtry = Registry(db_name)
            with resigtry.cursor() as cr:
                env = Environment(cr, SUPERUSER_ID, {})
                patient_all = env['medical.patient'].sudo()
                patient = patient_all.search(
                    [('code', '=', patient_code)], limit=1
                ).read(
                    [
                        'id',
                        'name',
                        'code',
                        'mobile',
                        'gender',
                        'age',
                    ]
                )
                res = {
                    'status': {'error': 'Patient not found'},
                }
                if patient:
                    res['status'] = 'success'
                    res['data'] = patient[0]

                return json.dumps(res, ensure_ascii=False)
        except Exception as e:
            _logger.error('Database not found: %s', db_name, exc_info=True)
            return json.dumps(
                {'status': 'error', 'error': str(e)}
            )

    @http.route(
        '/llm_agent/treatment/<db_name>/<patient_id>',
        auth='public',
        type='http',
        methods=['GET'],
        csrf=False,
    )
    def get_patient_treatment(self, db_name, patient_id, **kw):
        try:
            resigtry = Registry(db_name)
            with resigtry.cursor() as cr:
                env = Environment(cr, SUPERUSER_ID, {})
                treatment_all = env['medical.treatment'].sudo()
                treatment = treatment_all.search(
                    [('patient_id.id', '=', patient_id)]
                ).read(
                    [
                        'id',
                        'patient_id',
                        'name',
                        'technique_id',
                    ]
                )
                res = {
                    'status': {'error': 'Patient not found'},
                }
                if treatment:
                    res['status'] = 'success'
                    res['data'] = treatment

                return json.dumps(res, ensure_ascii=False)
        except Exception as e:
            _logger.error('Database not found: %s', db_name, exc_info=True)
            return json.dumps(
                {'status': 'error', 'error': str(e)}
            )
