from pydantic import BaseModel, Field
from typing import List, Optional




class SpendSummaryRequest(BaseModel):
    query: str = Field(description="The user's question")
    customer_id: str | None = None


# # query api endpoint response format
# class QueryResponse(BaseModel):
#    query: str
#    answer: str
#    policy_citations: str
#    page_no: str
#    document_name: str
#    sql_query_executed: Optional[str]

class CategoryBreakdown(BaseModel):
    category: str
    amount: float
    count: int
    pct_of_total: float


class TopMerchant(BaseModel):
    merchant_name: str
    amount: float


class InternationalSpend(BaseModel):
    amount: float
    transaction_count: int


class RewardPoints(BaseModel):
    points: int
    inr_value: float


class SpendSummaryResponse(BaseModel):
       query: str = Field(description="The given query by user")
       answer: str = Field(description="The generated response")
       policy_citations: str = Field(
            description="Policy citation for the documents retrieved"
       )
       page_no: str = Field(description="Page number in the metadata")
       document_name: str = Field(description="Name of the document")
       sql_query_executed: Optional[str] = Field(
            description="The AI generated and executed SQL query for the query"
        )
    # card_id: str
    # customer_name: str
    # billing_month: str

    # total_spend: float
    # total_transactions: int

    # category_breakdown: List[CategoryBreakdown]
    # top_merchants: List[TopMerchant]

    # international_spend: InternationalSpend
    # reward_points_earned: RewardPoints

    # mom_change_pct: float

    # summary_text: str
    # tip: str






# class AIResponse(BaseModel):
#    query: str = Field(description="The given query by user")
#    answer: str = Field(description="The generated response")
#    policy_citations: str = Field(
#        description="Policy citation for the documents retrieved"
#    )
#    page_no: str = Field(description="Page number in the metadata")
#    document_name: str = Field(description="Name of the document")
#    sql_query_executed: Optional[str] = Field(
#        description="The AI generated and executed SQL query for the query"
#    )


