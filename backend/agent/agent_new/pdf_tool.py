from langchain.tools import tool
from langchain_ch



def build_pdf_search_tool(pdf_path:str) -> 
@tool
def search_pdf( query: str) -> str:
    """
    Searches the given PDF file for the specified query and returns relevant text.
    
    Args:
        query (str): The search query.

    Returns:
        str: The text extracted from the PDF that matches the query.
    """

    try:
        vector_store = build_pdf_search_tool()
    except FileNotFoundError:
        return "No PDF documents are available for search."
    results = vector_store.similarity_search(query, k=3)
    if not results:
        return "No relevant text found in the PDF."
    return f"Found {len(results)} results in the PDF.\n\n" + "\n\n".join([doc.page_content for doc in results])