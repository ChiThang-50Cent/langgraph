from typing import (
    Annotated,
    Sequence,
    TypedDict,
    Optional
)
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """The state of the agent."""

    # add_messages is a reducer
    # See https://langchain-ai.github.io/langgraph/concepts/low_level/#reducers
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_question: Sequence[str]
    relevant_tables: Optional[Sequence[str]]
    relevant_schema: Optional[str]
    next_node: Optional[str]
    context: Optional[str]
    answer: Optional[str]
    queries: Optional[Sequence[str]]
    quality: Optional[str]
    samples: Optional[dict]
    guides: Optional[str]
    gen_count: Optional[int]