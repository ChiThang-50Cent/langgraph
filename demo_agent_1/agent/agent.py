import os
import logging

from typing import TypedDict, Literal

from langgraph.graph import StateGraph, END
from agent.utils import nodes
from agent.utils.state import AgentState
from langgraph.checkpoint.postgres import PostgresSaver

from dotenv import load_dotenv

_logger = logging.getLogger(__name__)

load_dotenv()

# DATABASE_URI = os.environ.get("DATABASE_URI")
# DATABASE_URI = "postgres://postgres:postgres@localhost:5433/postgres?sslmode=disable"
DATABASE_URI = "postgres://odoo16:ims@localhost:5432/ims_agent?sslmode=disable"

_logger.info(f"Using database URI: {DATABASE_URI}")

# Define the config
class GraphConfig(TypedDict):
    model_name: Literal["llama3.3"]

with PostgresSaver.from_conn_string(DATABASE_URI) as checkpointer:
    checkpointer.setup()

    workflow = StateGraph(AgentState)

    workflow.add_node("supervisor", nodes.supervisor_node)
    # workflow.add_node("temp_node", temp_node)
    workflow.add_node("get_user_sample", nodes.get_user_sample_node)
    workflow.add_node("get_relevant_tables", nodes.get_relevant_tables)
    workflow.add_node("get_relevant_schema", nodes.get_relevant_schema)
    workflow.add_node("gen_query_node", nodes.sql_query_gen_node)
    workflow.add_node("review_query_node", nodes.review_query_node)
    workflow.add_node("execute_node", nodes.execute_query_node)
    workflow.add_node("finalizer", nodes.finalizer_node)

    workflow.set_entry_point("supervisor")

    workflow.add_conditional_edges("supervisor", nodes.supervisor_route, ["finalizer", "get_user_sample"])
    # workflow.add_edge("temp_node", "get_user_sample")
    # workflow.add_edge("get_user_sample", "get_relevant_tables")
    # workflow.add_conditional_edges("get_user_sample", nodes.get_user_sample_route, ["get_relevant_tables", "get_relevant_schema"])
    workflow.add_edge("get_user_sample", "get_relevant_tables")
    workflow.add_edge("get_relevant_tables", "get_relevant_schema")
    workflow.add_edge("get_relevant_schema", "gen_query_node")
    workflow.add_edge("gen_query_node", "review_query_node")
    workflow.add_edge("review_query_node", "execute_node")
    workflow.add_conditional_edges("execute_node", nodes.execute_query_route, ["get_user_sample", "gen_query_node", "finalizer"])
    # workflow.add_edge("gen_query_node", "quality_checker")
    # workflow.add_conditional_edges("quality_checker", quality_checker_route, ["finalizer", "gen_query_node", "get_relevant_tables"])
    workflow.add_edge("finalizer", END)

    graph = workflow.compile(
        checkpointer=checkpointer,
        # interrupt_after=["finalizer"]
    )
