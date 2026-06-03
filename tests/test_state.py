from state.graph_state import GraphState


def test_graph_state_has_required_keys():
    state = GraphState(
        raw_articles=[],
        deduplicated_articles=[],
        article_entities={},
        sentiment_scores=[],
        events=[],
        signals=[],
        investment_plan=None,
        backtest_results=None,
        requires_interrupt=False,
        human_review_decision=None,
        error_log=[],
        run_date="2026-06-02",
    )
    assert state["signals"] == []
    assert state["error_log"] == []
