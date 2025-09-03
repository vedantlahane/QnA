# data_app/agent_core/config.py

import os
import yaml
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
from dotenv import load_dotenv
from pyprojroot import here

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

class LoadToolsConfig:
    """
    A singleton class to load configuration parameters from tools_config.yml.
    This ensures that the configuration is loaded only once and is accessible
    throughout the application with enhanced validation and error handling.
    """
    _instance = None
    _config_loaded = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LoadToolsConfig, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        if not self._config_loaded:
            self._load_config()
            LoadToolsConfig._config_loaded = True

    def _validate_api_keys(self) -> Dict[str, str]:
        """Validate and retrieve API keys from environment variables."""
        api_keys = {}
        
        # OpenAI API Key
        openai_key = os.getenv("OPEN_AI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not openai_key:
            raise ValueError(
                "OpenAI API key not found. Please set either OPEN_AI_API_KEY or OPENAI_API_KEY "
                "in your environment or .env file."
            )
        api_keys['openai'] = openai_key
        
        # Tavily API Key
        tavily_key = os.getenv("TAVILY_API_KEY")
        if not tavily_key:
            raise ValueError(
                "TAVILY_API_KEY is not set in the environment or .env file."
            )
        api_keys['tavily'] = tavily_key
        
        return api_keys

    def _find_config_file(self) -> Path:
        """Find the configuration file with fallback locations."""
        possible_paths = [
            here("configs/tools_config.yml"),
            here("configs/tools_config.yaml"), 
            here("config/tools_config.yml"),
            here("config/tools_config.yaml"),
            Path("configs/tools_config.yml"),
            Path("configs/tools_config.yaml"),
        ]
        
        for path in possible_paths:
            if path.exists():
                logger.info(f"Found configuration file at: {path}")
                return path
        
        raise FileNotFoundError(
            f"Configuration file not found. Searched in: {[str(p) for p in possible_paths]}"
        )

    def _validate_config_structure(self, config: Dict[str, Any]) -> None:
        """Validate the basic structure of the configuration."""
        required_sections = [
            "primary_agent",
            "tavily_search_api", 
            "pdf_rag",
            "csv_rag",
            "sql"
        ]
        
        for section in required_sections:
            if section not in config:
                raise KeyError(f"Missing required configuration section: {section}")

    def _validate_numeric_value(self, value: Any, name: str, min_val: float = None, max_val: float = None) -> Union[int, float]:
        """Validate and convert numeric configuration values."""
        try:
            if isinstance(value, (int, float)):
                num_value = value
            else:
                num_value = float(value)
            
            if min_val is not None and num_value < min_val:
                raise ValueError(f"{name} must be >= {min_val}, got {num_value}")
            
            if max_val is not None and num_value > max_val:
                raise ValueError(f"{name} must be <= {max_val}, got {num_value}")
            
            # Return as int if it's a whole number and was originally an int
            if isinstance(value, int) or (isinstance(num_value, float) and num_value.is_integer()):
                return int(num_value)
            
            return num_value
            
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid numeric value for {name}: {value}. Error: {e}")

    def _load_primary_agent_config(self, config: Dict[str, Any]) -> None:
        """Load and validate primary agent configuration."""
        agent_config = config["primary_agent"]
        
        self.primary_agent_llm = agent_config.get("llm", "gpt-4")
        self.primary_agent_llm_temperature = self._validate_numeric_value(
            agent_config.get("llm_temperature", 0.1),
            "primary_agent.llm_temperature",
            min_val=0.0,
            max_val=2.0
        )
        
        logger.info(f"Primary agent: {self.primary_agent_llm} (temp: {self.primary_agent_llm_temperature})")

    def _load_tavily_config(self, config: Dict[str, Any]) -> None:
        """Load and validate Tavily search configuration."""
        tavily_config = config["tavily_search_api"]
        
        self.tavily_search_max_results = self._validate_numeric_value(
            tavily_config.get("tavily_search_max_results", 5),
            "tavily_search_api.tavily_search_max_results",
            min_val=1,
            max_val=20
        )
        
        logger.info(f"Tavily search max results: {self.tavily_search_max_results}")

    def _load_pdf_rag_config(self, config: Dict[str, Any]) -> None:
        """Load and validate PDF RAG configuration."""
        pdf_config = config["pdf_rag"]
        
        self.pdf_rag_llm = pdf_config.get("llm", "gpt-4")
        self.pdf_rag_llm_temperature = self._validate_numeric_value(
            pdf_config.get("llm_temperature", 0.1),
            "pdf_rag.llm_temperature",
            min_val=0.0,
            max_val=2.0
        )
        self.pdf_rag_embedding_model = pdf_config.get("embedding_model", "text-embedding-3-small")
        self.pdf_rag_chunk_size = self._validate_numeric_value(
            pdf_config.get("chunk_size", 1000),
            "pdf_rag.chunk_size",
            min_val=100,
            max_val=4000
        )
        self.pdf_rag_chunk_overlap = self._validate_numeric_value(
            pdf_config.get("chunk_overlap", 200),
            "pdf_rag.chunk_overlap",
            min_val=0,
            max_val=self.pdf_rag_chunk_size // 2
        )
        self.pdf_rag_k = self._validate_numeric_value(
            pdf_config.get("k", 4),
            "pdf_rag.k",
            min_val=1,
            max_val=20
        )
        
        logger.info(f"PDF RAG: {self.pdf_rag_llm}, chunks: {self.pdf_rag_chunk_size}, k: {self.pdf_rag_k}")

    def _load_csv_rag_config(self, config: Dict[str, Any]) -> None:
        """Load and validate CSV RAG configuration."""
        csv_config = config["csv_rag"]
        
        self.csv_rag_llm = csv_config.get("llm", "gpt-4")
        self.csv_rag_llm_temperature = self._validate_numeric_value(
            csv_config.get("llm_temperature", 0.1),
            "csv_rag.llm_temperature",
            min_val=0.0,
            max_val=2.0
        )
        self.csv_rag_embedding_model = csv_config.get("embedding_model", "text-embedding-3-small")
        self.csv_rag_chunk_size = self._validate_numeric_value(
            csv_config.get("chunk_size", 1000),
            "csv_rag.chunk_size",
            min_val=100,
            max_val=4000
        )
        self.csv_rag_chunk_overlap = self._validate_numeric_value(
            csv_config.get("chunk_overlap", 200),
            "csv_rag.chunk_overlap",
            min_val=0,
            max_val=self.csv_rag_chunk_size // 2
        )
        self.csv_rag_k = self._validate_numeric_value(
            csv_config.get("k", 4),
            "csv_rag.k",
            min_val=1,
            max_val=20
        )
        
        logger.info(f"CSV RAG: {self.csv_rag_llm}, chunks: {self.csv_rag_chunk_size}, k: {self.csv_rag_k}")

    def _load_sql_config(self, config: Dict[str, Any]) -> None:
        """Load and validate SQL configuration."""
        sql_config = config["sql"]
        
        self.sql_llm = sql_config.get("llm", "gpt-4")
        self.sql_llm_temperature = self._validate_numeric_value(  # Fixed the typo here
            sql_config.get("llm_temperature", 0.0),
            "sql.llm_temperature",
            min_val=0.0,
            max_val=2.0
        )
        
        logger.info(f"SQL: {self.sql_llm} (temp: {self.sql_llm_temperature})")

    def _load_config(self) -> None:
        """
        Loads settings from the YAML file and sets them as instance attributes.
        """
        try:
            logger.info("Loading configuration...")
            
            # Validate and set API keys
            api_keys = self._validate_api_keys()
            os.environ['OPENAI_API_KEY'] = api_keys['openai']
            os.environ['TAVILY_API_KEY'] = api_keys['tavily']
            
            # Find and load configuration file
            config_path = self._find_config_file()
            
            with open(config_path, 'r', encoding='utf-8') as cfg_file:
                app_config = yaml.safe_load(cfg_file)
            
            if not app_config:
                raise ValueError("Configuration file is empty or invalid")
            
            # Validate configuration structure
            self._validate_config_structure(app_config)
            
            # Load each configuration section
            self._load_primary_agent_config(app_config)
            self._load_tavily_config(app_config)
            self._load_pdf_rag_config(app_config)
            self._load_csv_rag_config(app_config)
            self._load_sql_config(app_config)
            
            # Store original config for reference
            self._raw_config = app_config
            self._config_file_path = str(config_path)
            
            logger.info("Configuration loaded successfully")
            
        except FileNotFoundError as e:
            logger.error(f"Configuration file not found: {e}")
            raise
        except KeyError as e:
            logger.error(f"Missing key in configuration: {e}")
            raise
        except ValueError as e:
            logger.error(f"Configuration validation error: {e}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {e}")
            raise ValueError(f"Invalid YAML in configuration file: {e}")
        except Exception as e:
            logger.error(f"Unexpected error loading configuration: {e}")
            raise

    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the current configuration."""
        try:
            return {
                "config_file": getattr(self, '_config_file_path', 'Unknown'),
                "primary_agent": {
                    "llm": self.primary_agent_llm,
                    "temperature": self.primary_agent_llm_temperature
                },
                "tavily_search": {
                    "max_results": self.tavily_search_max_results
                },
                "pdf_rag": {
                    "llm": self.pdf_rag_llm,
                    "embedding_model": self.pdf_rag_embedding_model,
                    "chunk_size": self.pdf_rag_chunk_size,
                    "k": self.pdf_rag_k
                },
                "csv_rag": {
                    "llm": self.csv_rag_llm,
                    "embedding_model": self.csv_rag_embedding_model,
                    "chunk_size": self.csv_rag_chunk_size,
                    "k": self.csv_rag_k
                },
                "sql": {
                    "llm": self.sql_llm,
                    "temperature": self.sql_llm_temperature
                }
            }
        except AttributeError as e:
            return {"error": f"Configuration not fully loaded: {e}"}

    def validate_openai_models(self) -> Dict[str, bool]:
        """Validate that the configured OpenAI models are available."""
        models_to_check = [
            self.primary_agent_llm,
            self.pdf_rag_llm,
            self.csv_rag_llm,
            self.sql_llm
        ]
        
        # Common OpenAI models (this could be expanded or made dynamic)
        valid_models = {
            "gpt-4", "gpt-4-turbo", "gpt-4-turbo-preview",
            "gpt-3.5-turbo", "gpt-3.5-turbo-16k",
            "text-embedding-3-small", "text-embedding-3-large",
            "text-embedding-ada-002"
        }
        
        validation_results = {}
        for model in set(models_to_check):  # Remove duplicates
            validation_results[model] = model in valid_models
        
        return validation_results

    def reload_config(self) -> bool:
        """Reload configuration from file."""
        try:
            LoadToolsConfig._config_loaded = False
            self._load_config()
            LoadToolsConfig._config_loaded = True
            logger.info("Configuration reloaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")
            return False

# Create a single global instance for easy access
try:
    TOOLS_CFG = LoadToolsConfig()
except Exception as e:
    logger.error(f"Failed to initialize global configuration: {e}")
    raise

# Utility functions
def get_config() -> LoadToolsConfig:
    """Get the global configuration instance."""
    return TOOLS_CFG

def validate_environment() -> Dict[str, Any]:
    """Validate the entire environment setup."""
    try:
        config = get_config()
        return {
            "config_loaded": True,
            "config_summary": config.get_config_summary(),
            "model_validation": config.validate_openai_models(),
            "api_keys_set": {
                "openai": bool(os.getenv("OPENAI_API_KEY")),
                "tavily": bool(os.getenv("TAVILY_API_KEY"))
            }
        }
    except Exception as e:
        return {
            "config_loaded": False,
            "error": str(e)
        }

# Export main classes and functions
__all__ = [
    'LoadToolsConfig',
    'TOOLS_CFG', 
    'get_config',
    'validate_environment'
]
