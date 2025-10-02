class BroadcastConfig(BaseModel):
    chat_id: str
    chat_name: str
    news_types: List[NewsType]
    sources: List[NewsSource]
    min_confidence: float = 0.5
    active: bool = True


class ClassifiedNews(BaseModel):
    id: str
    title: str
    content: str
    source: NewsSource
    news_type: NewsType
    confidence: float
    url: Optional[str] = None
    published_at: datetime
    classified_at: datetime
