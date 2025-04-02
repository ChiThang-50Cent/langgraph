import os
import re
import requests
import json
import sqlparse
import logging

from collections import defaultdict
from functools import lru_cache
from langchain_core.messages import ToolMessage
from uuid import uuid4

from sqlalchemy import create_engine, inspect, text
from langchain_community.utilities import SQLDatabase

from dotenv import load_dotenv
load_dotenv()

_logger = logging.getLogger(__name__)

IMS_DB_URI = os.environ.get('IMS_DB_URI')
IMS_DB_NAME = os.environ.get('IMS_DB_NAME')
IMS_BASE_URL = os.environ.get('IMS_BASE_URL')
MILVUS_URL = os.environ.get('MILVUS_URL')

# usage_table = [
#     "action_update_appointment_follicle_note: Cập nhật số lượng nang trứng và ghi chú cho một thủ thuật y tế.",
#     "add_cryostraw_to_renew: Wizard chọn ống đông lạnh cần gia hạn.",
#     "check_sperm_donate_history: Wizard kiểm tra lịch sử hiến tinh của bệnh nhân qua thông tin định danh.",
#     "history_medical_treatment_iui: Lưu trữ lịch sử điều trị IUI",
#     "history_medical_treatment_ivf: Lưu trữ thông tin điều trị IVF",
#     "hr_contract_type: Quản lý các loại hợp đồng lao động",
#     "hr_department: Quản lý các phòng ban trong công ty",
#     "hr_departure_reason: Quản lý lý do nghỉ việc của nhân viên",
#     "hr_employee: Quản lý thông tin nhân viên",
#     "hr_employee_category: Quản lý thẻ (tags) gán cho nhân viên",
#     "hr_job: Quản lý các vị trí công việc trong công ty",
#     "medical_appointment_check_foetus: Quản lý khám thai định kỳ",
#     "medical_appointment_procedure: Quản lý thủ thuật y tế",
#     "medical_appointment_re_examination: Quản lý tái khám bệnh nhân",
#     "medical_beta_hcg_pregnant: Quản lý xét nghiệm beta HCG và theo dõi thai kỳ",
#     "medical_birth_info: Quản lý thông tin em bé sau điều trị",
#     "medical_blood_type: Quản lý danh mục nhóm máu",
#     "medical_bottle_medium: Quản lý lọ môi trường nuôi cấy trong phòng lab IVF",
#     "medical_canes: Quản lý ống đựng mẫu sinh học trong hệ thống bảo quản lạnh",
#     "medical_canes_position: Quản lý vị trí lưu trữ mẫu sinh học trong ống đựng",
#     "medical_canister: Quản lý thông tin của canister trong hệ thống bảo quản lạnh",
#     "medical_canister_layer: Quản lý các tầng trong canister",
#     "medical_canister_position: Quản lý từng vị trí cụ thể trong canister",
#     "medical_cassette: Quản lý thông tin về cassette trong hệ thống bảo quản mẫu sinh học",
#     "medical_cause_infertility: Danh mục nguyên nhân vô sinh",
#     "medical_create_culture: Tạo và cập nhật thông tin nuôi cấy phôi/trứng",
#     "medical_create_relation_popup: Tạo và quản lý mối quan hệ giữa các bệnh nhân",
#     "medical_cryopreserv_straw: Quản lý bảo quản lạnh các mẫu sinh học",
#     "medical_day_of_embryo: Quản lý thông tin về các ngày phát triển của phôi",
#     "medical_department: Quản lý các khoa/phòng trong bệnh viện hoặc trung tâm y tế",
#     "medical_detail_embryo_frozen: Theo dõi chi tiết các phôi đã đông lạnh",
#     "medical_diagnostic: Quản lý danh mục các chẩn đoán y tế",
#     "medical_document_type: Quản lý danh mục các loại tài liệu trong hệ thống y tế",
#     "medical_embryo_biopsy_detail: Lưu trữ thông tin chi tiết về mẫu sinh thiết phôi",
#     "medical_embryo_culture: Theo dõi và quản lý quá trình nuôi cấy phôi",
#     "medical_embryo_detail: Thống kê số lượng phôi theo ngày",
#     "medical_embryo_grading: Phân loại chất lượng phôi",
#     "medical_embryonic_stage: Quản lý các giai đoạn phát triển của phôi",
#     "medical_embryonic_stage_condition: Định nghĩa điều kiện đánh giá phôi",
#     "medical_ex_husband: Quản lý thông tin tiền sử sinh sản",
#     "medical_follicular_monitoring_decision: Quản lý quyết định theo dõi nang noãn",
#     "medical_follicular_size: Lưu trữ thông tin kích thước nang noãn",
#     "medical_follow_follicular: Quản lý theo dõi nang noãn",
#     "medical_group_embryo: Quản lý nhóm đông lạnh phôi/trứng",
#     "medical_history_embryo_culture: Ghi nhận lịch sử nuôi cấy phôi",
#     "medical_history_relationship: Quản lý lịch sử mối quan hệ bệnh nhân",
#     "medical_hr_department_line: Liên kết nhân viên và bộ phận",
#     "medical_icd: Quản lý danh mục bệnh tật quốc tế",
#     "medical_image_embryo: Quản lý hình ảnh phôi",
#     "medical_indication: Quản lý chỉ định xét nghiệm y tế",
#     "medical_indication_detail: Chi tiết chỉ định xét nghiệm",
#     "medical_indication_detail_select: Lựa chọn chỉ số xét nghiệm",
#     "medical_indication_reference: Tham chiếu chỉ định xét nghiệm",
#     "medical_indication_trigger: Quản lý trigger cho chỉ định xét nghiệm",
#     "medical_initial_evaluation: Đánh giá ban đầu bệnh nhân",
#     "medical_initial_evaluation_prescription: Đơn thuốc đánh giá ban đầu",
#     "medical_location: Vị trí lưu trữ mẫu sinh học",
#     "medical_location_room: Thông tin phòng lưu trữ mẫu vật y tế",
#     "medical_outpatient_examination: Khám bệnh ngoại trú",
#     "medical_patient: Thông tin cơ bản bệnh nhân",
#     "medical_patient_action_reference_bank: Cập nhật mã tham chiếu ngân hàng mô",
#     "medical_patient_documen: Quản lý giấy tờ bệnh nhân",
#     "medical_patient_document_submit: Theo dõi nộp giấy tờ bệnh nhân",
#     "medical_patient_partner: Thông tin người thân/người đại diện bệnh nhân",
#     "medical_patient_printed_report_event: Lịch sử in báo cáo bệnh nhân",
#     "medical_patient_record: Hồ sơ bệnh án",
#     "medical_patient_relationship: Mối quan hệ điều trị giữa bệnh nhân",
#     "medical_patient_report_wizard_line: Quản lý in báo cáo y tế",
#     "medical_pgs_info: Thông tin quy trình PGS",
#     "medical_pgs_info_line: chi tiết của quy trình PGS",
#     "medical_prepare_medium: chuẩn bị môi trường nuôi cấy",
#     "medical_prepare_medium_detail: chi tiết chuẩn bị môi trường nuôi cấy",
#     "medical_prescription_order: quản lý đơn thuốc y tế",
#     "medical_prescription_order_line: quản lý chi tiết đơn thuốc",
#     "medical_prescription_usage: quản lý cách dùng thuốc",
#     "medical_procedure_room: quản lý thông tin về phòng thủ thuật",
#     "medical_process_pgt: quản lý quy trình PGT",
#     "medical_process_storage: quản lý quy trình lưu trữ phôi/noãn",
#     "medical_process_transfer: quản lý quá trình chuyển phôi thai",
#     "medical_protocol: quản lý các quy trình y tế",
#     "medical_record_document: định nghĩa cấu trúc hồ sơ y tế",
#     "medical_record_type: quản lý các loại hồ sơ y tế",
#     "medical_renewal: quản lý việc gia hạn thời gian lưu trữ mẫu y tế",
#     "medical_renewal_line: theo dõi chi tiết việc gia hạn lưu trữ mẫu sinh học",
#     "medical_renewal_reminder: quản lý việc nhắc nhở gia hạn lưu trữ mẫu sinh học",
#     "medical_renewal_reminder_log: ghi nhận lịch sử các hoạt động nhắc nhở gia hạn",
#     "medical_renewal_reminder_log_line: ghi lại chi tiết các hoạt động nhắc nhở gia hạn",
#     "medical_renewal_reminder_queue: quản lý hàng đợi nhắc nhở gia hạn dịch vụ y tế",
#     "medical_storage_configuration: cấu hình các thông số cho việc lưu trữ và nhắc nhở",
#     "medical_storage_history: theo dõi lịch sử lưu trữ mẫu sinh học",
#     "medical_storage_process: quản lý quy trình lưu trữ các mẫu sinh học",
#     "medical_storage_tool: Quản lý dụng cụ và thiết bị lưu trữ mẫu sinh học",
#     "medical_tank: Quản lý bình chứa lạnh",
#     "medical_tank_information_record: Ghi nhận thông tin theo dõi bình chứa",
#     "medical_test: Quản lý phiếu xét nghiệm y tế",
#     "medical_test_category: Phân loại xét nghiệm y tế",
#     "medical_test_group: Nhóm xét nghiệm y tế",
#     "medical_test_indices: Định nghĩa chỉ số xét nghiệm",
#     "medical_test_indices_result_selection: Định nghĩa lựa chọn kết quả xét nghiệm",
#     "medical_test_result: Quản lý kết quả xét nghiệm",
#     "medical_thaw_bank_popup: Quản lý quy trình rã đông mẫu sinh học",
#     "medical_thaw_popup: Quản lý quy trình rã đông mẫu sinh học",
#     "medical_thaw_popup_detail: Chi tiết quy trình rã đông mẫu sinh học",
#     "medical_thawing_process: Quản lý quy trình rã đông mẫu sinh học",
#     "medical_transfer_bank: Chuyển mẫu vật y tế vào ngân hàng lưu trữ",
#     "medical_treatment: Quản lý quy trình điều trị y tế",
#     "medical_treatment_document: Quản lý tài liệu điều trị y tế",
#     "medical_treatment_medium: Quản lý môi trường nuôi cấy điều trị y tế",
#     "medical_treatment_result: Quản lý kết quả điều trị y tế",
#     "medical_treatment_result_beta: Theo dõi kết quả xét nghiệm beta HCG",
#     "medical_treatment_stage: Quản lý giai đoạn điều trị y tế",
#     "medical_treatment_technique: Quản lý kỹ thuật điều trị y tế",
#     "medical_update_relation_popup: Cập nhật thông tin mối quan hệ bệnh nhân",
#     "medical_waiting_procedure: Quản lý hàng đợi thủ tục y tế",
#     "medium_type: Quản lý loại môi trường nuôi cấy",
#     "patient_fingerprint: Lưu trữ thông tin vân tay bệnh nhân",
#     "patient_fingerprint_history: Lịch sử xác thực vân tay bệnh nhân",
#     "patient_recognition_history: Lịch sử nhận diện bệnh nhân",
#     "process_storage_line: Lưu trữ quá trình cấp đông mẫu",
#     "process_storage_popup: Quản lý lưu trữ mẫu y sinh học",
#     "product_attribute: Quản lý thuộc tính sản phẩm",
#     "product_attribute_custom_value: Lưu trữ giá trị tùy chỉnh thuộc tính sản phẩm",
#     "product_attribute_value: Lưu trữ giá trị thuộc tính sản phẩm",
#     "product_category: Quản lý danh mục sản phẩm",
#     "product_label_layout: Tạo và in nhãn sản phẩm",
#     "product_packaging: Quản lý đóng gói sản phẩm",
#     "product_pricelist: Quản lý bảng giá sản phẩm",
#     "product_pricelist_item: Định nghĩa quy tắc tính giá sản phẩm",
#     "product_product: Quản lý biến thể sản phẩm",
#     "product_supplierinfo: Quản lý bảng giá sản phẩm từ nhà cung cấp",
#     "product_tag: Quản lý thẻ sản phẩm",
#     "product_template: Quản lý thông tin sản phẩm",
#     "product_template_attribute_exclusion: Định nghĩa quy tắc loại trừ thuộc tính sản phẩm",
#     "product_template_attribute_line: Quản lý thuộc tính sản phẩm",
#     "product_template_attribute_value: Lưu trữ mối quan hệ thuộc tính sản phẩm",
#     "range_years_old: Định nghĩa khoảng tuổi",
#     "relation_contact: Quản lý thông tin mối quan hệ tạm thời",
#     "renew_cryostraw_group: Nhóm ống đông lạnh cần gia hạn",
#     "res_partner: Quản lý thông tin nhân viên",
#     "res_users: Quản lý người dùng hệ thống",
#     "treatment_test_subscriber: Đăng ký theo dõi xét nghiệm điều trị",
#     "uom_category: Quản lý đơn vị đo lường sản phẩm",
#     "uom_uom: Phân loại đơn vị đo lường"
# ]

@lru_cache(maxsize=4)
def get_db() -> SQLDatabase:
    """Get SQLDatabase instance."""
    return SQLDatabase.from_uri(IMS_DB_URI)

def create_tool_message(content):
    return ToolMessage(content=content, tool_call_id=str(uuid4()))

def milvus_query(
    collection_name: str,
    output_fields: list[str],
    lang: str = 'vi',
) -> list[dict]:
    """Query Milvus collection.
    
    Args:
        collection_name: Name of collection to query
        output_fields: Fields to return in results
        lang: Language of the query
    Returns:
        List of matching documents
    """  
    try:
        res = requests.post(f'{MILVUS_URL}/query', json={
            "collection_name": collection_name,
            "output_fields": output_fields,
            "lang": lang,
        })

        return res.json().get('data', [])
    except Exception as e:
        _logger.error(f"Milvus query failed: {e}", exc_info=True)
        return []

def milvus_search(
    question: str,
    collection_name: str, 
    output_fields: list[str],
    lang: str = 'vi',
    limit: int = 2,
) -> list[dict]:
    """Search vectors in Milvus collection.
    
    Args:
        question: Query
        collection_name: Name of collection to search
        output_fields: Fields to return in results
        limit: Maximum number of results        
    Returns:
        List of matching documents
    """

    try:
        res = requests.post(f'{MILVUS_URL}/search', json={
            "question": question,
            "collection_name": collection_name,
            "output_fields": output_fields,
            "lang": lang,
            "limit": limit,
        })

        return res.json().get('data', [])
    except Exception as e:
        _logger.error(f"Milvus search failed: {e}", exc_info=True)
        return []    

def get_lang(text: str) -> str:
    """Detect the language of the text."""
    vietnamese_chars = re.compile(r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]', re.IGNORECASE)
    lang = 'vi' if vietnamese_chars.search(text) else 'en'
    return lang

def get_usable_table(lang: str = 'vi') -> list[dict]:
    """Get all usable table names from the database."""
    usage_table = milvus_query('table', ['name', 'description'], lang=lang)
    return usage_table

def run_query_with_exception(query):
    """Execute a database query and handle exceptions."""
    try:
        db = get_db()
        result = db.run(query, include_columns=True)
    except Exception as e:
        result = e.args[0]
    return result

def execute_query(query):
    """Execute a database query."""
    engine = create_engine(IMS_DB_URI)

    try:
        with engine.connect() as connection:
            result = connection.execute(text(query))
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in result]
        json_data = json.dumps(data, indent=4, default=str, ensure_ascii=False)
    except Exception as e:
        json_data = e.args[0]
    return json_data

def format_sql_query(query):
    """Format a SQL query."""
    formatted_query = sqlparse.format(query, reindent=True, keyword_case='upper')
    return formatted_query

def get_table_columns(table_name):
    """Get all column names for a specified table."""
    engine = create_engine(IMS_DB_URI)
    inspector = inspect(engine)
    db = get_db()
    if table_name not in db.get_usable_table_names():
        return []
    columns = inspector.get_columns(table_name)
    return [col['name'] for col in columns]

def format_sample_data(table_name, columns, rows, sample_count):
    """Format sample data for display."""
    header = f'{sample_count} sample rows from {table_name}:\n'
    column_header = ', '.join(columns) + '\n'
    
    formatted_rows = '\n'.join(str(row) for row in rows)
    return header + column_header + formatted_rows + '\n'

def get_sample_rows(table_name: str, columns: list[str], sample_rows: int = 3) -> str:
    """Get sample rows from database table.
    
    Args:
        table_name: Name of table
        columns: List of column names
        sample_rows: Number of rows to return
        
    Returns:
        Formatted string of sample data
    """
    query = f'SELECT {", ".join(columns)} FROM "{table_name}" LIMIT {sample_rows}'
    db = get_db()
    result = db.run(query)
    
    tuple_pattern = re.compile(r'\((?:[^)(]+|\((?:[^)(]+|\([^)(]*\))*\))*\)')
    matches = tuple_pattern.findall(result)
    
    return format_sample_data(table_name, columns, matches, sample_rows)

def get_column_description(field_info: dict) -> str:
    """Format field description.
    
    Args:
        field_info: Dictionary containing field metadata
        
    Returns:
        Formatted description string
    """
    if not field_info:
        return ""
        
    parts = [
        f"Des: {field_info['field_description']}" if field_info['field_description'] else "",
        f"Value: {field_info['value']}" if field_info['value'] else "",
        f"Help: {field_info['help']}" if field_info['help'] else ""
    ]
    parts = [p for p in parts if p]
        
    return f" -- {', '.join(parts)}" if parts else ""

def get_table_field_descriptions(table_name):
    """Fetch field descriptions from the API."""
    response = requests.get(f'{IMS_BASE_URL}/table_info/{IMS_DB_NAME}/{table_name}')
    if response.json().get('status') == 'success':
        return response.json().get('data', {})
    return {}

def get_all_field_with_des(table_name: str) -> list[str]:
    """Get all fields with their descriptions for a given table.
    
    Args:
        table_name: Name of the database table
        
    Returns:
        List of strings containing field names and descriptions in format "field: description"
    """

    des = get_table_field_descriptions(table_name)
    cols = get_table_columns(table_name)

    return [
        f"{col}: {des.get(col, {}).get('field_description')}"
        for col in cols
        if des.get(col, {})
    ]

def get_partial_schema(table_name, selected_columns):
    """Generate partial schema definition for a table with selected columns."""
    engine = create_engine(IMS_DB_URI)
    inspector = inspect(engine)

    # Get table metadata
    columns = inspector.get_columns(table_name)
    primary_keys = inspector.get_pk_constraint(table_name)['constrained_columns']
    foreign_keys = inspector.get_foreign_keys(table_name)
    
    # Filter columns based on selection
    filtered_columns = [col for col in columns if col['name'] in selected_columns]
    field_descriptions = get_table_field_descriptions(table_name)
    
    # Build column definitions
    column_defs = []
    for col in filtered_columns:
        col_name = col["name"]
        col_def = f'    "{col_name}" {col["type"]}'
        
        if col_name in primary_keys:
            col_def += " NOT NULL"
            
        col_def += get_column_description(field_descriptions.get(col_name, {}))
        column_defs.append(col_def)

    # Add primary key constraint
    if primary_keys:
        pk_def = f'    PRIMARY KEY ({", ".join(pk for pk in primary_keys)})'
        column_defs.append(pk_def)

    # Process foreign keys and collect sample data
    foreign_samples = []
    for fk in foreign_keys:
        fk_column = fk["constrained_columns"][0]
        if fk_column in selected_columns:
            ref_table = fk["referred_table"]
            ref_column = fk["referred_columns"][0]
            
            # Add foreign key constraint
            fk_def = f'    FOREIGN KEY ("{fk_column}") REFERENCES "{ref_table}" ("{ref_column}")'
            column_defs.append(fk_def)
            
            # Get sample data from referenced table if it's small enough
            ref_columns = inspector.get_columns(ref_table)
            if len(ref_columns) <= 15:
                important_columns = [
                    col["name"] for col in ref_columns
                    if col["name"] not in ["create_uid", "write_uid", "create_date", "write_date"]
                ]
                foreign_samples.append(get_sample_rows(ref_table, important_columns, sample_rows=5))

    # Build the final schema
    create_table_stmt = f'```sql\nCREATE TABLE "{table_name}" (\n'
    create_table_stmt += ",\n".join(column_defs) + "\n);\n```\n"
    
    # Add sample data
    create_table_stmt += get_sample_rows(
        table_name, 
        [col["name"] for col in filtered_columns]
    )
    
    # Add foreign table samples if any
    if foreign_samples:
        create_table_stmt += "\n".join(foreign_samples) + "\n\n"
    
    return create_table_stmt

def merge_dicts_list(dict_list):
    """Merge a list of dictionaries where each dictionary contains tables as keys and lists of columns as values.
    
    Args:
        dict_list: List of dictionaries, where each dictionary maps table names to lists of column names
        
    Returns:
        A merged dictionary with all tables and their combined columns
    """
    merged_tables = defaultdict(set)
    
    # Process each dictionary in the list
    for d in dict_list:
        # For each table in the dictionary
        for table_name, columns in d.items():
            # Add all columns to the set for this table
            merged_tables[table_name].update(columns)
    
    # Convert sets back to lists in the final result
    return {k: list(v) for k, v in merged_tables.items()}
