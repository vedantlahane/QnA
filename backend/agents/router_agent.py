"""
Router Agent for Query Classification and Routing
This agent determines which specialized agent should handle the user's query.
"""

from typing import Dict, Any, Literal
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)

class QueryClassification(BaseModel):
    """Model for query classification output"""
    agent_type: Literal["sql", "csv", "rag", "general"] = Field(
        description="The type of agent that should handle this query"
    )
    confidence: float = Field(
        description="Confidence score between 0 and 1",
        ge=0.0,
        le=1.0
    )
    reasoning: str = Field(
        description="Brief explanation of why this agent was chosen"
    )
    query_intent: str = Field(
        description="The main intent of the user's query"
    )

class RouterAgent:
    """
    Router Agent that classifies user queries and routes them to appropriate specialized agents.
    """
    
    def __init__(self, llm: ChatOpenAI = None):
        self.llm = llm or ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1
        )
        self.parser = PydanticOutputParser(pydantic_object=QueryClassification)
        self.prompt = self._create_prompt()
        self.chain = self.prompt | self.llm | self.parser
        
    def _create_prompt(self) -> ChatPromptTemplate:
        """Create the classification prompt template"""
        return ChatPromptTemplate.from_messages([
            ("system", """You are an intelligent query router that classifies user questions and determines which specialized agent should handle them.

Available Agents:
1. **SQL Agent**: Handles queries about structured database data, tables, records, analytics, and business metrics
   - Examples: "Show me sales data", "What's the total revenue?", "List all customers from NY"
   
2. **CSV Agent**: Handles queries about CSV file data, spreadsheet analysis, and tabular data operations
   - Examples: "Analyze this CSV file", "What's the average in column X?", "Show me the top 10 rows"
   
3. **RAG Agent**: Handles questions about documents, PDFs, knowledge base content, and general information retrieval
   - Examples: "What does this document say about X?", "Summarize the PDF", "Find information about Y"
   
4. **General**: For greetings, general conversation, system questions, or unclear queries
   - Examples: "Hello", "How are you?", "What can you do?", "Help me understand this system"

Classification Guidelines:
- SQL: Keywords like "database", "table", "records", "analytics", "metrics", "sales", "revenue", specific column names
- CSV: Keywords like "CSV", "spreadsheet", "file", "column", "row", "average", "sum", data analysis terms
- RAG: Keywords like "document", "PDF", "explain", "summarize", "information about", knowledge-seeking questions
- General: Greetings, system questions, ambiguous queries, conversational exchanges

Consider context, keywords, and intent. Be confident in your classification.

{format_instructions}"""),
            ("human", "User Query: {query}\n\nPlease classify this query and determine which agent should handle it.")
        ]).partial(format_instructions=self.parser.get_format_instructions())
    
    async def classify_query(self, query: str, context: Dict[str, Any] = None) -> QueryClassification:
        """
        Classify a user query and determine which agent should handle it.
        
        Args:
            query: The user's question or request
            context: Additional context about available data sources
            
        Returns:
            QueryClassification with agent type, confidence, and reasoning
        """
        try:
            # Add context information to help with classification
            enhanced_query = query
            if context:
                if context.get("has_sql_data"):
                    enhanced_query += f"\n[Context: SQL database available]"
                if context.get("has_csv_data"):
                    enhanced_query += f"\n[Context: CSV files available]"
                if context.get("has_documents"):
                    enhanced_query += f"\n[Context: Document knowledge base available]"
            
            classification = await self.chain.ainvoke({"query": enhanced_query})
            
            logger.info(f"Query classified: {query[:50]}... -> {classification.agent_type} (confidence: {classification.confidence})")
            
            return classification
            
        except Exception as e:
            logger.error(f"Error classifying query: {e}")
            # Fallback to general agent
            return QueryClassification(
                agent_type="general",
                confidence=0.5,
                reasoning=f"Classification failed, defaulting to general agent. Error: {str(e)}",
                query_intent="Unknown due to classification error"
            )
    
    def route_query(self, classification: QueryClassification) -> str:
        """
        Get the routing decision based on classification.
        
        Args:
            classification: The query classification result
            
        Returns:
            The agent name that should handle the query
        """
        agent_mapping = {
            "sql": "sql_agent",
            "csv": "csv_agent", 
            "rag": "rag_agent",
            "general": "general_agent"
        }
        
        return agent_mapping.get(classification.agent_type, "general_agent")
    
    async def process_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Complete query processing: classify and route.
        
        Args:
            query: The user's question
            context: Additional context about available data sources
            
        Returns:
            Dictionary with classification results and routing decision
        """
        classification = await self.classify_query(query, context)
        route = self.route_query(classification)
        
        return {
            "classification": classification.dict(),
            "route": route,
            "should_route_to": classification.agent_type,
            "confidence": classification.confidence,
            "reasoning": classification.reasoning
        }

# Factory function for easy instantiation
def create_router_agent(llm: ChatOpenAI = None) -> RouterAgent:
    """Create a configured router agent instance"""
    return RouterAgent(llm=llm)

# Example usage and testing
if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    
    load_dotenv()
    
    async def test_router():
        router = create_router_agent()
        
        test_queries = [
            "What's the total sales for Q4?",
            "Analyze the customer data in this CSV file",
            "What does the documentation say about API usage?",
            "Hello, how are you?",
            "Show me the top 10 customers by revenue",
            "Calculate the average price from the product spreadsheet",
            "Summarize the research paper about AI",
        ]
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            result = await router.process_query(query)
            print(f"Route: {result['route']}")
            print(f"Confidence: {result['confidence']}")
            print(f"Reasoning: {result['reasoning']}")
    
    # Run test
    # asyncio.run(test_router())
