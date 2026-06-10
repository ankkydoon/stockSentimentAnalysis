import operator
from typing import Annotated, Any, TypedDict

from models.article import Article
from models.entity import Entity
from models.sentiment import SentimentScore
from models.event import Event
from models.signal import InvestmentSignal
from models.recommendation import InvestmentPlan, UserProfile


class GraphState(TypedDict):
    raw_articles: list[Article]
    deduplicated_articles: list[Article]
    article_entities: dict[str, list[Entity]]
    sentiment_scores: list[SentimentScore]
    events: list[Event]
    signals: list[InvestmentSignal]
    investment_plan: InvestmentPlan | None
    user_profile: UserProfile | None
    backtest_results: dict[str, Any] | None
    requires_interrupt: bool
    human_review_decision: str | None
    error_log: Annotated[list[str], operator.add]
    run_date: str
