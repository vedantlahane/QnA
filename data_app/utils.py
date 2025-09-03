import pandas as pd
import fitz  # PyMuPDF for PDFs

def process_file(file_path):
    if file_path.endswith(".pdf"):
        return parse_pdf(file_path)
    elif file_path.endswith(".csv"):
        return parse_csv(file_path)

def parse_pdf(path):
    text = ""
    with fitz.open(path) as doc:
        for page in doc:
            text += page.get_text()
    # do vectorization here
    return text

def parse_csv(path):
    df = pd.read_csv(path)
    # process dataframe, convert to text/vectorize
    return df.to_string()
