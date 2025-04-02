from agent.utils import prompt, utils
from agent.utils.state import AgentState

import os
import re
import json

from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser

from typing import Literal, Sequence
from pydantic import BaseModel

from dotenv import load_dotenv
load_dotenv()


MODEL_NAME = os.getenv('MODEL_NAME')

@lru_cache(maxsize=4)
def _get_model(model_name: str):
    if model_name == "llama3.3":
        model = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0.5)
    elif model_name == "gpt-4o-mini":
        model = ChatOpenAI(model_name="gpt-4o-mini", temperature=0.5)
    else:
        raise ValueError(f"Unsupported model type: {model_name}")

    return model

# Define the schema of the output
class NextOutput(BaseModel):
    next: Literal['finalizer', 'start_generate']

class ListOutput(BaseModel):
    list_output: Sequence[str]

async def supervisor_node(state: AgentState):

    if len(state.get('user_question', [])) > 3:
        return {"next_node": "finalizer"}

    human_message = state['messages'][-1]

    llm =_get_model(MODEL_NAME)
    response = await llm.ainvoke([SystemMessage(prompt.sup_node_system_prompt)] + state['messages'])
    response = PydanticOutputParser(pydantic_object=NextOutput).parse(response.content)

    return {
        "next_node": response.next,
        "user_question": state.get('user_question', []) + [human_message.content],
        "gen_count": 0,
    }

def supervisor_route(state: AgentState):
    # Check if the temporary context exists
    next_node = state.get('next_node', None)
    if next_node == 'finalizer':
        return 'finalizer'
    
    return 'get_user_sample'

def get_user_sample_node(state: AgentState):
    # Get the user question
    # return {}
    user_question = state['user_question']
    user_question = '\n'.join((f'- {q}' for q in user_question))

    if not user_question:
        return {'samples': {}}

    query_collection_name = "sample"
    guide_collection_name = "guide"

    lang = utils.get_lang(user_question)

    query_search = utils.milvus_search(
        user_question,
        query_collection_name,
        ["description", "query", "tables"],
        lang=lang,
        limit=4
    )
    guide_search = utils.milvus_search(
        user_question,
        guide_collection_name,
        output_fields=["description", "keyword"],
        lang=lang,
        limit=5,
    )
    
    pair = ''
    tables_data = {}

    for sample in query_search:
        pair += f"Question: {sample['description']}\n"
        pair += f"Query: ```sql\n{utils.format_sql_query(sample['query'])}\n```\n"
        pair += '-' * 30 + '\n'
        
        if sample.get('tables'):
            tables_data = utils.merge_dicts_list([tables_data, sample['tables']])

    samples = {
        "samples": pair,
        "tables": tables_data,
    } if pair else {}

    return {
        "samples": samples,
        "guides": "\n".join(
            (f"- {guide['keyword']}, {guide['description']}" for guide in guide_search)
        ),
    }


# def get_user_sample_route(state: AgentState):
#     if not state.get('samples', None):
#         return 'get_relevant_tables'

#     return 'get_relevant_schema'

async def get_relevant_tables(state: AgentState):
    # Get the partial schema of the database
    # The partial schema is a CREATE TABLE statement with only the selected columns

    human_question = state['user_question']
    human_question = '\n'.join((f'- {q}' for q in human_question))

    lang = utils.get_lang(human_question)
    usage_table = utils.get_usable_table(lang)
    usage_table = (f"{table['name']}: {table['description']}" for table in usage_table)

    human_table = HumanMessage(
        "List of table: \n\n{tables}".format(tables="\n".join(usage_table))
    )
    
    llm_schema = _get_model(MODEL_NAME)
    tables = await llm_schema.ainvoke(
        [SystemMessage(prompt.get_relevant_tables_system_prompt)]
        + [human_question, human_table]
    )
    tables = PydanticOutputParser(pydantic_object=ListOutput).parse(tables.content)

    samples = state.get('samples', {})

    return {
        "relevant_tables": list(
            set(
                [
                    "medical_patient",
                    "medical_treatment",
                    *tables.list_output,
                ] + (list(samples.get('tables', {}).keys()) if samples else [])
            )
        ),
        "queries": None,
        "answer": None,
    }

async def get_relevant_schema(state: AgentState):
    # Get the partial schema of the database
    # The partial schema is a CREATE TABLE statement with only the selected columns
    
    human_question = state['user_question']
    human_question = '\n'.join((f'- {q}' for q in human_question))

    human_table_column = "Tables: {table_name}\n\nColumns:\n{columns}"
    samples = state.get('samples', {})
    schemas = []

    human_guide = HumanMessage(f"Term explaination :\n\n{state.get('guides', '')}")
    
    list_tables = state.get('relevant_tables', [])
    llm_schema = _get_model(MODEL_NAME)

    for table_name in list_tables:
        columns = utils.get_table_columns(table_name)

        if len(columns) > 10:
            temp_columns = utils.get_all_field_with_des(table_name)
            columns = await llm_schema.ainvoke(
                [SystemMessage(prompt.get_relevant_columns_system_prompt)]
                + [human_question]
                + (
                    [AIMessage("Please provide term explaination"), human_guide]
                    if state.get("guides", {})
                    else []
                )
                + [ AIMessage("Please provide table columns"),
                    HumanMessage(
                        human_table_column.format(
                            table_name=table_name, columns="\n".join(temp_columns)
                        )
                    )
                ]
            )
            columns = PydanticOutputParser(pydantic_object=ListOutput).parse(
            columns.content
            )
            columns = columns.list_output
        if not columns:
            continue
        if 'active' in utils.get_table_columns(table_name) and 'active' not in columns:
            columns.append('active')
        if samples.get('tables', {}).keys():
            columns = list(set([*columns, *samples['tables'].get(table_name, [])]))
        
        partial_schema = utils.get_partial_schema(table_name, columns)
        schemas.append(partial_schema)
    
    return {'relevant_schema': '\n'.join(schemas)}

async def sql_query_gen_node(state: AgentState):
    # Generate SQL query
    
    human_schema = HumanMessage(f"Additional Table Schema:\n\n{state['relevant_schema']}")
    human_sample = HumanMessage(f"Sample Data:\n\n{state.get('samples', {}).get('samples', '')}")
    human_guide = HumanMessage(f"Term explaination :\n\n{state.get('guides', '')}")
    
    llm = _get_model(MODEL_NAME)
    response = await llm.ainvoke(
        [SystemMessage(prompt.sql_query_gen_system_prompt)]
        + state["messages"]
        + [AIMessage("Please provide additional table schema")]
        + [human_schema]
        + (
            [AIMessage('Please provide term explaination'), human_guide]
            if state.get("guides", {})
            else []
        )
        + (
            [AIMessage('Please provide sample data'), human_sample]
            if state.get("samples", {})
            else []
        )
    )

    # Use regex to extract JSON output
    sql_pattern = re.compile(r"```sql\n(.*?)\n```", re.DOTALL)
    matches = sql_pattern.findall(response.content)

    if not matches:
        return {'queries': None}

    return {
        "queries": matches[-1],
        "gen_count": state.get("gen_count", 0) + 1,
    }


async def review_query_node(state: AgentState):
    # Review the generated query

    ai_query = state.get('queries', '')
    ai_query = utils.format_sql_query(ai_query)

    # human_question = state['user_question']
    # human_question = '\n'.join((f'- {q}' for q in human_question))

    # human_message = HumanMessage(human_question)
    human_query = HumanMessage(f"Generated SQL Query:\n```sql\n{ai_query}\n```")

    llm = _get_model(MODEL_NAME)
    response = await llm.ainvoke(
      [SystemMessage(prompt.review_query_system_prompt)]
    #   + [human_message]
    #   + [AIMessage('Please provide generated SQL query')]
      + [human_query]
    )

    # Use regex to extract JSON output
    sql_pattern = re.compile(r"```sql\n(.*?)\n```", re.DOTALL)
    matches = sql_pattern.findall(response.content)

    if not matches:
        return {'queries': None}

    return {'queries': matches[-1]}

def execute_query_node(state: AgentState):
    # Execute the generated query
    queries = state.get('queries', '')
    
    if not queries:
        return {}
    
    responses = utils.execute_query(queries)
    
    return {'answer': responses}


def execute_query_route(state: AgentState):
    # Check if the query was successfully generated
    query = state.get('queries', '')
    answer = state.get('answer', '')
    count = state.get('gen_count', 0)

    if count > 3:
        return 'finalizer'

    if not query or 'SELECT NULL' in query:
        return 'get_user_sample'
    if 'errors' in answer:
        return 'gen_query_node' 
    
    return 'finalizer'

async def finalizer_node(
    state: AgentState,
):
    # Generate final response
    if len(state.get('user_question', [])) > 3 or state.get('gen_count', 0) > 3:
        return {"messages": [AIMessage("Đã quá số lần tạo câu hỏi, bạn vui lòng tạo một cuộc trò chuyện mới!")]}

    conversation = state['messages']
    tool_query = state.get('queries', '')
    tool_query = utils.format_sql_query(tool_query)

    tool_answer = state.get('answer', '')
    if tool_answer:
        tool_answer = json.loads(tool_answer)
        tool_answer = tool_answer[:10]
        tool_answer = json.dumps(tool_answer, indent=4, default=str, ensure_ascii=False)

    tool_answer = utils.create_tool_message(tool_answer)
    tool_query = utils.create_tool_message(f'```sql\n{tool_query}\n```')
    
    llm = _get_model(MODEL_NAME)
    response = await llm.ainvoke(
        [SystemMessage(prompt.finalizer_system_prompt)]
        + conversation
        + ([tool_query] if state.get('answer', '') else [])
        + ([tool_answer] if state.get('queries', '') else [])
    )

    message = [tool_query, tool_answer] if state.get('answer', '') else []

    return {"messages": message + [response]}
