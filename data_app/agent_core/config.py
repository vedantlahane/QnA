# data_app/agent_core/config.py

import os
import yaml
from dotenv import load_dotenv
from pyprojroot import here

# Load environment variables from .env file
load_dotenv()

class LoadToolsConfig:
    """
    A singleton class to load configuration parameters from tools_config.yml.
    This ensures that the configuration is loaded only once and is accessible
    throughout the application.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LoadToolsConfig, cls).__new__(cls, *args, **kwargs)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """
        Loads settings from the YAML file and sets them as instance attributes.
        """
        try:
            # Use pyprojroot to find the project root and then the config file
            config_path = here("configs/tools_config.yml")
            with open(config_path, 'r') as cfg_file:
                app_config = yaml.safe_load(cfg_file)

            # Set environment variables from .env
            os.environ['OPENAI_API_KEY'] = os.getenv("OPEN_AI_API_KEY")
            os.environ['TAVILY_API_KEY'] = os.getenv("TAVILY_API_KEY")

            # --- Primary agent settings ---
            self.primary_agent_llm = app_config["primary_agent"]["llm"]
            self.primary_agent_llm_temperature = float(app_config["primary_agent"]["llm_temperature"])

            # --- Internet Search configs ---
            self.tavily_search_max_results = int(app_config["tavily_search_api"]["tavily_search_max_results"])

            # --- PDF RAG configs ---
            self.pdf_rag_llm = app_config["pdf_rag"]["llm"]
            self.pdf_rag_llm_temperature = float(app_config["pdf_rag"]["llm_temperature"])
            self.pdf_rag_embedding_model = app_config["pdf_rag"]["embedding_model"]
            self.pdf_rag_chunk_size = app_config["pdf_rag"]["chunk_size"]
            self.pdf_rag_chunk_overlap = app_config["pdf_rag"]["chunk_overlap"]
            self.pdf_rag_k = app_config["pdf_rag"]["k"]

            # NOTE: Add similar configurations for your SQL and CSV tools here

            print("Configuration loaded successfully.")

        except FileNotFoundError:
            print("Error: tools_config.yml not found. Please ensure it's in the configs directory.")
            raise
        except KeyError as e:
            print(f"Error: Missing key in tools_config.yml: {e}")
            raise

# Create a single global instance for easy access
TOOLS_CFG = LoadToolsConfig()