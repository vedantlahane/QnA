import os
from pathlib import Path
from dotenv import load_dotenv

from langchain.chat_models import init_chat_model
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain import hub
from langgraph.prebuilt import create_react_agent

# 1) Env
load_dotenv()
if os.getenv("OPENAI_API_KEY") is None:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# 2) Model (pick one)
# Option A: Provider-prefixed via init_chat_model (recommended with LangGraph)
llm = init_chat_model("openai:gpt-4o", temperature=0)

# Option B: Direct OpenAI wrapper (requires `pip install -U langchain-openai`)
# from langchain_openai import ChatOpenAI
# llm = ChatOpenAI(model="gpt-4o", temperature=0)

# 3) Database and toolkit
backend_dir = Path(__file__).resolve().parents[2]
sqldb_path = backend_dir / "db.sqlite3"
db = SQLDatabase.from_uri(f"sqlite:///{sqldb_path}")

toolkit = SQLDatabaseToolkit(db=db, llm=llm)

# 4) Prompt from hub
prompt_template = hub.pull("langchain-ai/sql-agent-system-prompt")
system_message = prompt_template.format(dialect="SQLite", top_k=5)

# 5) Agent
agent_executor = create_react_agent(
    model=llm,
    tools=toolkit.get_tools(),
    prompt=system_message,  # static system prompt
    # checkpointer=InMemorySaver(),  # optional for memory
)

# 6) Streaming
example_query = "Which country's customers spent the most?"
events = agent_executor.stream(
    {"messages": [("user", example_query)]},
    stream_mode="values",  # alternatives: "values", "messages"
)
for event in events:
    # event is a state update chunk when using stream_mode="updates"
    # for "messages", iterate (message_chunk, metadata)
    event["messages"][-1].pretty_print()  # print the latest message chunk
