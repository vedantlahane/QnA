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

Configuration Structure:
    The module loads settings for multiple tools and components:
    - Primary Agent: Main LLM settings
    - PDF RAG: PDF document processing and retrieval
    - CSV RAG: CSV document processing and retrieval
    - SQL Tool: Database query generation
    - Tavily Search: Internet search capabilities

Dependencies:
    - PyYAML: For YAML file parsing
    - python-dotenv: For environment variable loading
    - pyprojroot: For project root detection

Environment Variables Required:
    - OPEN_AI_API_KEY: OpenAI API key for LLM services
    - TAVILY_API_KEY: Tavily API key for internet search

Configuration File:
    - Location: configs/tools_config.yml (relative to project root)
    - Format: YAML with nested structure for different tools

Author: Q&A Agent System
Created: 2025
"""

import os
from typing import Optional, Dict, Any
import yaml
from dotenv import load_dotenv
from pyprojroot import here

# Load environment variables from .env file at module level
load_dotenv()


class LoadToolsConfig:
    """
    Singleton configuration loader for the Q&A agent system.

    This class implements the singleton pattern to ensure that configuration
    is loaded only once during the application lifecycle, improving performance
    and ensuring consistency across all components.

    The class loads configuration from:
    1. YAML configuration file (tools_config.yml)
    2. Environment variables (.env file and system environment)

    Attributes are dynamically set based on the YAML configuration structure,
    providing easy access to all configuration parameters throughout the application.

    Class Attributes:
        _instance: Singleton instance reference (internal use only)

    Instance Attributes (dynamically loaded):
        Primary Agent Settings:
            - primary_agent_llm: LLM model name for main agent
            - primary_agent_llm_temperature: Temperature setting for main agent

        PDF RAG Settings:
            - pdf_rag_llm: LLM model for PDF processing
            - pdf_rag_llm_temperature: Temperature for PDF LLM
            - pdf_rag_embedding_model: Embedding model for PDF chunks
            - pdf_rag_chunk_size: Size of text chunks for PDF processing
            - pdf_rag_chunk_overlap: Overlap between PDF chunks
            - pdf_rag_k: Number of similar chunks to retrieve

        CSV RAG Settings:
            - csv_rag_llm: LLM model for CSV processing
            - csv_rag_llm_temperature: Temperature for CSV LLM
            - csv_rag_embedding_model: Embedding model for CSV chunks
            - csv_rag_chunk_size: Size of text chunks for CSV processing
            - csv_rag_chunk_overlap: Overlap between CSV chunks
            - csv_rag_k: Number of similar chunks to retrieve

        SQL Tool Settings:
            - sql_llm: LLM model for SQL query generation
            - sql_llm_temperature: Temperature for SQL LLM

        Tavily Search Settings:
            - tavily_search_max_results: Maximum search results to return

    Example:
        >>> config = LoadToolsConfig()
        >>> print(config.primary_agent_llm)
        'gpt-4'
        >>> print(config.pdf_rag_chunk_size)
        1000
    """

    _instance = None  # Singleton instance reference

    def __new__(cls, *args, **kwargs) -> 'LoadToolsConfig':
        """
        Create or return the singleton instance of LoadToolsConfig.

        This method ensures only one instance of the configuration class
        exists throughout the application lifecycle.

        Args:
            *args: Variable positional arguments (passed to __init__)
            **kwargs: Variable keyword arguments (passed to __init__)

        Returns:
            LoadToolsConfig: The singleton instance of the configuration class
        """
        if not cls._instance:
            cls._instance = super(LoadToolsConfig, cls).__new__(cls, *args, **kwargs)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        """
        Load and validate configuration from YAML file and environment variables.

        This method performs the following operations:
        1. Locates the configuration file using project root
        2. Parses the YAML configuration file
        3. Validates required environment variables (API keys)
        4. Sets environment variables for library access
        5. Loads and converts configuration parameters
        6. Performs type validation and conversion

        The method uses comprehensive error handling to provide clear
        feedback about configuration issues.

        Raises:
            FileNotFoundError: If tools_config.yml is not found
            KeyError: If required configuration keys are missing
            ValueError: If environment variables or configuration values are invalid
            yaml.YAMLError: If YAML file parsing fails

        Note:
            This method is called automatically during singleton instantiation.
            Manual calling is not required and may cause configuration reloading.
        """
        try:
            # Locate configuration file using project root detection
            # This ensures the config file is found regardless of working directory
            config_path = here("configs/tools_config.yml")

            # Parse YAML configuration file with safe loading
            with open(config_path, 'r', encoding='utf-8') as cfg_file:
                app_config = yaml.safe_load(cfg_file)

            # Validate and load required API keys from environment
            # These are critical for the application to function
            openai_api_key = os.getenv("OPEN_AI_API_KEY")
            tavily_api_key = os.getenv("TAVILY_API_KEY")

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

            # Set environment variables for library access
            # This ensures libraries can access the API keys
            os.environ['OPENAI_API_KEY'] = openai_api_key
            os.environ['TAVILY_API_KEY'] = tavily_api_key

            # --- Primary Agent Configuration ---
            # Main LLM settings for the primary agent
            self.primary_agent_llm = app_config["primary_agent"]["llm"]
            self.primary_agent_llm_temperature = float(app_config["primary_agent"]["llm_temperature"])

            # --- Internet Search Configuration ---
            # Settings for Tavily search API integration
            self.tavily_search_max_results = int(app_config["tavily_search_api"]["tavily_search_max_results"])

            # --- PDF RAG Configuration ---
            # Settings for PDF document processing and retrieval-augmented generation
            self.pdf_rag_llm = app_config["pdf_rag"]["llm"]
            self.pdf_rag_llm_temperature = float(app_config["pdf_rag"]["llm_temperature"])
            self.pdf_rag_embedding_model = app_config["pdf_rag"]["embedding_model"]
            self.pdf_rag_chunk_size = int(app_config["pdf_rag"]["chunk_size"])
            self.pdf_rag_chunk_overlap = int(app_config["pdf_rag"]["chunk_overlap"])
            self.pdf_rag_k = int(app_config["pdf_rag"]["k"])

            # --- CSV RAG Configuration ---
            # Settings for CSV document processing and retrieval-augmented generation
            self.csv_rag_llm = app_config["csv_rag"]["llm"]
            self.csv_rag_llm_temperature = float(app_config["csv_rag"]["llm_temperature"])
            self.csv_rag_embedding_model = app_config["csv_rag"]["embedding_model"]
            self.csv_rag_chunk_size = int(app_config["csv_rag"]["chunk_size"])
            self.csv_rag_chunk_overlap = int(app_config["csv_rag"]["chunk_overlap"])
            self.csv_rag_k = int(app_config["csv_rag"]["k"])

            # --- SQL Tool Configuration ---
            # Settings for SQL query generation and database interaction
            self.sql_llm = app_config["sql"]["llm"]
            self.sql_llm_temperature = float(app_config["sql"]["llm_temperature"])

            # Configuration loading completed successfully
            print("Configuration loaded successfully.")

        except FileNotFoundError as e:
            error_msg = (
                "Configuration file not found. Please ensure 'tools_config.yml' "
                f"exists in the 'configs' directory. Error: {str(e)}"
            )
            print(f"Error: {error_msg}")
            raise FileNotFoundError(error_msg) from e

        except KeyError as e:
            error_msg = (
                f"Missing configuration key in tools_config.yml: {str(e)}. "
                "Please check your configuration file structure."
            )
            print(f"Error: {error_msg}")
            raise KeyError(error_msg) from e

        except ValueError as e:
            error_msg = f"Configuration validation error: {str(e)}"
            print(f"Error: {error_msg}")
            raise ValueError(error_msg) from e

        except yaml.YAMLError as e:
            error_msg = f"YAML parsing error in tools_config.yml: {str(e)}"
            print(f"Error: {error_msg}")
            raise yaml.YAMLError(error_msg) from e

        except Exception as e:
            error_msg = f"Unexpected error during configuration loading: {str(e)}"
            print(f"Error: {error_msg}")
            raise RuntimeError(error_msg) from e


# --- Global Configuration Instance ---
# Create a single global instance for easy access throughout the application
# This follows the singleton pattern and ensures consistent configuration access
TOOLS_CFG = LoadToolsConfig()

"""
USAGE INFORMATION:

This module provides a global configuration instance (TOOLS_CFG) that can be
imported and used throughout the application:

    from data_app.agent_core.config import TOOLS_CFG

    # Access configuration parameters
    llm_model = TOOLS_CFG.primary_agent_llm
    chunk_size = TOOLS_CFG.pdf_rag_chunk_size

The configuration is loaded once when first imported and cached for performance.

CONFIGURATION FILE STRUCTURE (tools_config.yml):

primary_agent:
  llm: "gpt-4"
  llm_temperature: 0.7

tavily_search_api:
  tavily_search_max_results: 5

pdf_rag:
  llm: "gpt-4"
  llm_temperature: 0.3
  embedding_model: "text-embedding-ada-002"
  chunk_size: 1000
  chunk_overlap: 200
  k: 4

csv_rag:
  llm: "gpt-4"
  llm_temperature: 0.3
  embedding_model: "text-embedding-ada-002"
  chunk_size: 1000
  chunk_overlap: 200
  k: 4

sql:
  llm: "gpt-4"
  llm_temperature: 0.1

TROUBLESHOOTING:

1. "Configuration file not found":
   - Ensure tools_config.yml exists in configs/ directory
   - Check project root detection with pyprojroot

2. "Missing API key":
   - Verify .env file exists with correct variable names
   - Check environment variable names match exactly

3. "YAML parsing error":
   - Validate YAML syntax in tools_config.yml
   - Check for proper indentation and structure

4. "Type conversion error":
   - Ensure numeric values in config are proper numbers
   - Check for string values where numbers are expected
"""
