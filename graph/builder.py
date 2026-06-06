from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from state.graph_state import GraphState
from agents.news_ingestion import news_ingestion_node
from agents.entity_recognition import entity_recognition_node
from agents.sentiment_analysis import sentiment_analysis_node
from agents.event_detection import event_detection_node
from agents.earnings_subagent import earnings_subagent_node
from agents.signal_generation import signal_generation_node
from agents.briefing_report import briefing_report_node
from agents.recommendation import recommendation_node
from graph.router import (
    route_after_ingestion,
    route_after_ner,
    route_after_event_detection,
    route_after_earnings,
    human_review_node,
)


def build_graph():
    builder = StateGraph(GraphState)

    builder.add_node("news_ingestion", news_ingestion_node)
    builder.add_node("entity_recognition", entity_recognition_node)
    builder.add_node("sentiment_analysis", sentiment_analysis_node)
    builder.add_node("event_detection", event_detection_node)
    builder.add_node("earnings_subagent", earnings_subagent_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("signal_generation", signal_generation_node)
    builder.add_node("briefing_report", briefing_report_node)
    builder.add_node("recommendation", recommendation_node)

    builder.set_entry_point("news_ingestion")

    builder.add_conditional_edges(
        "news_ingestion",
        route_after_ingestion,
        {
            "entity_recognition": "entity_recognition",
            "end": END,
        },
    )

    builder.add_conditional_edges(
        "entity_recognition",
        route_after_ner,
        {
            "sentiment_analysis": "sentiment_analysis",
            "end": END,
        },
    )

    builder.add_edge("sentiment_analysis", "event_detection")

    builder.add_conditional_edges(
        "event_detection",
        route_after_event_detection,
        {
            "earnings_subagent": "earnings_subagent",
            "human_review": "human_review",
            "signal_generation": "signal_generation",
        },
    )

    builder.add_conditional_edges(
        "earnings_subagent",
        route_after_earnings,
        {
            "human_review": "human_review",
            "signal_generation": "signal_generation",
        },
    )

    builder.add_edge("human_review", "signal_generation")
    builder.add_edge("signal_generation", "briefing_report")
    builder.add_edge("briefing_report", "recommendation")
    builder.add_edge("recommendation", END)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)
