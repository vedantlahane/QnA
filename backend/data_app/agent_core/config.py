"""
Configuration Management Module for Q&A Agent System

This module provides centralized configuration management for the Q&A agent system.
It implements a singleton pattern to ensure configuration is loaded once and shared
across all components of the application.

The module loads configuration parameters from a YAML file (tools_config.yml) and
environment variables, providing a clean separation between code and configuration.

Key Features:
- Singleton pattern for efficient configuration management
- YAML-based configuration files for easy maintenance
- Environment variable integration for sensitive data (API keys)
- Comprehensive error handling and validation
- Type conversion and validation for configuration values

Author: Q&A Agent System
Created: 2025
"""

import os
from typing import Optional, Dict, Any
import yaml
from dotenv import load_dotenv
from pyprojroot import here
import logging

logger = logging.getLogger('data_app.agent_core.config')

# Load environment variables from .env file at module import time
load_dotenv()


class LoadToolsConfig:
    """
    Singleton configuration loader for the Q&A agent system.

    Loads configuration from:
    1. YAML configuration file (configs/tools_config.yml)
    2. Environment variables (.env file and system environment)

    Exposes attributes for:
    - Primary Agent
      * primary_agent_llm (str)
      * primary_agent_llm_temperature (float)
    - Tavily Search API
      * tavily_search_max_results (int)
    - PDF RAG
      * pdf_rag_llm (str)
      * pdf_rag_llm_temperature (float)
      * pdf_rag_embedding_model (str)
      * pdf_rag_chunk_size (int)
      * pdf_rag_chunk_overlap (int)
      * pdf_rag_k (int)
    - CSV RAG
      * csv_rag_llm (str)
      * csv_rag_llm_temperature (float)
      * csv_rag_embedding_model (str)
      * csv_rag_chunk_size (int)
      * csv_rag_chunk_overlap (int)
      * csv_rag_k (int)
    - SQL Tool
      * sql_llm (str)
      * sql_llm_temperature (float)
    """

    _instance: Optional['LoadToolsConfig'] = None

    def __new__(cls, *args, **kwargs) -> 'LoadToolsConfig':
        if not cls._instance:
            cls._instance = super(LoadToolsConfig, cls).__new__(cls, *args, **kwargs)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        """
        Load and validate configuration from YAML file and environment variables.
        Sets environment variables expected by libraries and attaches config values as attributes.
        """
        try:
            # Locate configuration file using project root detection
            config_path = here('configs/tools_config.yml')

            # Parse YAML configuration file with safe loading
            with open(config_path, 'r', encoding='utf-8') as cfg_file:
                app_config: Dict[str, Any] = yaml.safe_load(cfg_file)

            # Validate and load required API keys from environment
            openai_api_key = os.getenv('OPEN_AI_API_KEY')
            tavily_api_key = os.getenv('TAVILY_API_KEY')

            if not openai_api_key:
                raise ValueError(
                    "OPEN_AI_API_KEY is not set in the environment or .env file. "
                    "Please check your .env file or environment variables."
                )

            if not tavily_api_key:
                raise ValueError(
                    "TAVILY_API_KEY is not set in the environment or .env file. "
                    "Please check your .env file or environment variables."
                )

            # Set environment variables that downstream libraries expect
            # OpenAI SDK expects OPENAI_API_KEY (without underscore between OPEN and AI)
            os.environ['OPENAI_API_KEY'] = openai_api_key
            os.environ['TAVILY_API_KEY'] = tavily_api_key

            # --- Primary Agent Configuration ---
            self.primary_agent_llm = app_config['primary_agent']['llm']
            self.primary_agent_llm_temperature = float(app_config['primary_agent']['llm_temperature'])

            # --- Internet Search Configuration ---
            self.tavily_search_max_results = int(app_config['tavily_search_api']['tavily_search_max_results'])

            # --- PDF RAG Configuration ---
            self.pdf_rag_llm = app_config['pdf_rag']['llm']
            self.pdf_rag_llm_temperature = float(app_config['pdf_rag']['llm_temperature'])
            self.pdf_rag_embedding_model = app_config['pdf_rag']['embedding_model']
            self.pdf_rag_chunk_size = int(app_config['pdf_rag']['chunk_size'])
            self.pdf_rag_chunk_overlap = int(app_config['pdf_rag']['chunk_overlap'])
            self.pdf_rag_k = int(app_config['pdf_rag']['k'])

            # --- CSV RAG Configuration ---
            self.csv_rag_llm = app_config['csv_rag']['llm']
            self.csv_rag_llm_temperature = float(app_config['csv_rag']['llm_temperature'])
            self.csv_rag_embedding_model = app_config['csv_rag']['embedding_model']
            self.csv_rag_chunk_size = int(app_config['csv_rag']['chunk_size'])
            self.csv_rag_chunk_overlap = int(app_config['csv_rag']['chunk_overlap'])
            self.csv_rag_k = int(app_config['csv_rag']['k'])

            # --- SQL Tool Configuration ---
            self.sql_llm = app_config['sql']['llm']
            self.sql_llm_temperature = float(app_config['sql']['llm_temperature'])

            logger.info('Configuration loaded successfully.')

        except FileNotFoundError as e:
            error_msg = (
                "Configuration file not found. Please ensure 'tools_config.yml' "
                f"exists in the 'configs' directory. Error: {str(e)}"
            )
            logger.info(f"Error: {error_msg}")
            raise FileNotFoundError(error_msg) from e
        except KeyError as e:
            error_msg = (
                f"Missing configuration key in tools_config.yml: {str(e)}. "
                "Please check your configuration file structure."
            )
            logger.info(f"Error: {error_msg}")
            raise KeyError(error_msg) from e
        except ValueError as e:
            error_msg = f"Configuration validation error: {str(e)}"
            logger.info(f"Error: {error_msg}")
            raise ValueError(error_msg) from e
        except yaml.YAMLError as e:
            error_msg = f"YAML parsing error in tools_config.yml: {str(e)}"
            logger.info(f"Error: {error_msg}")
            raise yaml.YAMLError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during configuration loading: {str(e)}"
            logger.info(f"Error: {error_msg}")
            raise RuntimeError(error_msg) from e


# --- Global Configuration Instance ---
TOOLS_CFG = LoadToolsConfig()
