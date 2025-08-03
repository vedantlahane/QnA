"""
CSV Agent for File Data Analysis
This agent handles CSV file processing, data analysis, and spreadsheet operations.
"""

from typing import Dict, Any, List, Optional, Union
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain.agents.agent_types import AgentType
import pandas as pd
import numpy as np
import io
import logging
from pathlib import Path
import chardet
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64

logger = logging.getLogger(__name__)

class CSVAgent:
    """
    CSV Agent that processes CSV files and performs data analysis using pandas.
    Handles file loading, data exploration, statistical analysis, and visualization.
    """
    
    def __init__(
        self, 
        llm: ChatOpenAI = None,
        max_iterations: int = 15,
        verbose: bool = True
    ):
        self.llm = llm or ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1
        )
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.dataframes = {}  # Store multiple dataframes
        self.current_df = None
        self.current_df_name = None
        self.agent = None
    
    def detect_encoding(self, file_path: str) -> str:
        """
        Detect file encoding
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            Detected encoding string
        """
        try:
            with open(file_path, 'rb') as file:
                raw_data = file.read(10000)  # Read first 10KB
                result = chardet.detect(raw_data)
                return result.get('encoding', 'utf-8')
        except Exception as e:
            logger.warning(f"Could not detect encoding: {e}, defaulting to utf-8")
            return 'utf-8'
    
    def load_csv_file(
        self, 
        file_path: str, 
        name: str = None,
        **pandas_kwargs
    ) -> Dict[str, Any]:
        """
        Load CSV file into pandas DataFrame
        
        Args:
            file_path: Path to the CSV file
            name: Name to store the dataframe under
            **pandas_kwargs: Additional arguments for pandas.read_csv()
            
        Returns:
            Dictionary with loading results and basic info
        """
        try:
            # Auto-detect encoding if not specified
            if 'encoding' not in pandas_kwargs:
                pandas_kwargs['encoding'] = self.detect_encoding(file_path)
            
            # Load CSV
            df = pd.read_csv(file_path, **pandas_kwargs)
            
            # Generate name if not provided
            if name is None:
                name = Path(file_path).stem
            
            # Store dataframe
            self.dataframes[name] = df
            self.current_df = df
            self.current_df_name = name
            
            # Create agent for this dataframe
            self._create_agent()
            
            # Get basic info
            info = self.get_dataframe_info(name)
            
            logger.info(f"CSV file loaded: {file_path} -> {name} ({df.shape[0]} rows, {df.shape[1]} columns)")
            
            return {
                "success": True,
                "name": name,
                "shape": df.shape,
                "columns": df.columns.tolist(),
                "info": info,
                "sample_data": df.head().to_dict('records')
            }
            
        except Exception as e:
            logger.error(f"Error loading CSV file {file_path}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def load_csv_from_string(
        self, 
        csv_content: str, 
        name: str,
        **pandas_kwargs
    ) -> Dict[str, Any]:
        """
        Load CSV from string content
        
        Args:
            csv_content: CSV content as string
            name: Name to store the dataframe under
            **pandas_kwargs: Additional arguments for pandas.read_csv()
            
        Returns:
            Dictionary with loading results
        """
        try:
            # Load CSV from string
            df = pd.read_csv(io.StringIO(csv_content), **pandas_kwargs)
            
            # Store dataframe
            self.dataframes[name] = df
            self.current_df = df
            self.current_df_name = name
            
            # Create agent
            self._create_agent()
            
            logger.info(f"CSV loaded from string: {name} ({df.shape[0]} rows, {df.shape[1]} columns)")
            
            return {
                "success": True,
                "name": name,
                "shape": df.shape,
                "columns": df.columns.tolist(),
                "sample_data": df.head().to_dict('records')
            }
            
        except Exception as e:
            logger.error(f"Error loading CSV from string: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_agent(self) -> None:
        """Create pandas dataframe agent for current dataframe"""
        if self.current_df is not None:
            self.agent = create_pandas_dataframe_agent(
                llm=self.llm,
                df=self.current_df,
                verbose=self.verbose,
                agent_type=AgentType.OPENAI_FUNCTIONS,
                max_iterations=self.max_iterations,
                allow_dangerous_code=True  # Allow code execution for data analysis
            )
    
    def switch_dataframe(self, name: str) -> bool:
        """
        Switch to a different loaded dataframe
        
        Args:
            name: Name of the dataframe to switch to
            
        Returns:
            True if successful, False otherwise
        """
        if name in self.dataframes:
            self.current_df = self.dataframes[name]
            self.current_df_name = name
            self._create_agent()
            logger.info(f"Switched to dataframe: {name}")
            return True
        else:
            logger.warning(f"Dataframe '{name}' not found")
            return False
    
    def get_dataframe_info(self, name: str = None) -> Dict[str, Any]:
        """
        Get comprehensive information about a dataframe
        
        Args:
            name: Name of the dataframe (uses current if None)
            
        Returns:
            Dictionary with dataframe information
        """
        df = self.dataframes.get(name, self.current_df) if name else self.current_df
        
        if df is None:
            return {"error": "No dataframe available"}
        
        try:
            # Basic info
            info = {
                "shape": df.shape,
                "columns": df.columns.tolist(),
                "dtypes": df.dtypes.to_dict(),
                "memory_usage": df.memory_usage(deep=True).sum(),
                "null_counts": df.isnull().sum().to_dict(),
                "duplicate_rows": df.duplicated().sum()
            }
            
            # Statistical summary for numeric columns
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                info["numeric_summary"] = df[numeric_cols].describe().to_dict()
            
            # Sample data
            info["sample_data"] = {
                "head": df.head().to_dict('records'),
                "tail": df.tail().to_dict('records')
            }
            
            # Column types analysis
            info["column_analysis"] = {}
            for col in df.columns:
                col_info = {
                    "type": str(df[col].dtype),
                    "unique_values": df[col].nunique(),
                    "null_count": df[col].isnull().sum(),
                    "null_percentage": (df[col].isnull().sum() / len(df)) * 100
                }
                
                # Add value counts for categorical columns
                if df[col].dtype == 'object' or df[col].nunique() < 20:
                    col_info["value_counts"] = df[col].value_counts().head(10).to_dict()
                
                info["column_analysis"][col] = col_info
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting dataframe info: {e}")
            return {"error": str(e)}
    
    def perform_basic_analysis(self, name: str = None) -> Dict[str, Any]:
        """
        Perform basic data analysis
        
        Args:
            name: Name of the dataframe (uses current if None)
            
        Returns:
            Dictionary with analysis results
        """
        df = self.dataframes.get(name, self.current_df) if name else self.current_df
        
        if df is None:
            return {"error": "No dataframe available"}
        
        try:
            analysis = {}
            
            # Data quality metrics
            analysis["data_quality"] = {
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "missing_values": df.isnull().sum().sum(),
                "missing_percentage": (df.isnull().sum().sum() / (len(df) * len(df.columns))) * 100,
                "duplicate_rows": df.duplicated().sum(),
                "complete_rows": len(df.dropna())
            }
            
            # Numeric analysis
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            if len(numeric_cols) > 0:
                analysis["numeric_analysis"] = {
                    "correlation_matrix": df[numeric_cols].corr().to_dict(),
                    "outliers": {}
                }
                
                # Simple outlier detection using IQR
                for col in numeric_cols:
                    Q1 = df[col].quantile(0.25)
                    Q3 = df[col].quantile(0.75)
                    IQR = Q3 - Q1
                    outliers = df[(df[col] < Q1 - 1.5 * IQR) | (df[col] > Q3 + 1.5 * IQR)]
                    analysis["numeric_analysis"]["outliers"][col] = len(outliers)
            
            # Categorical analysis
            categorical_cols = df.select_dtypes(include=['object']).columns
            if len(categorical_cols) > 0:
                analysis["categorical_analysis"] = {}
                for col in categorical_cols:
                    analysis["categorical_analysis"][col] = {
                        "unique_values": df[col].nunique(),
                        "most_frequent": df[col].mode().iloc[0] if not df[col].mode().empty else None,
                        "top_values": df[col].value_counts().head(5).to_dict()
                    }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error performing basic analysis: {e}")
            return {"error": str(e)}
    
    async def process_natural_language_query(
        self, 
        query: str, 
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Process natural language query about the CSV data
        
        Args:
            query: Natural language question about the data
            context: Additional context for the query
            
        Returns:
            Dictionary with analysis results and answer
        """
        if not self.agent or self.current_df is None:
            return {"error": "No CSV data loaded. Please load a CSV file first."}
        
        try:
            # Add context to the query if provided
            enhanced_query = query
            if context:
                if context.get("column_hints"):
                    enhanced_query += f"\n\nFocus on these columns: {', '.join(context['column_hints'])}"
                if context.get("analysis_type"):
                    enhanced_query += f"\n\nType of analysis: {context['analysis_type']}"
            
            # Add dataframe info to help the agent
            df_info = f"\n\nDataFrame info: Shape {self.current_df.shape}, Columns: {', '.join(self.current_df.columns[:10])}..."
            enhanced_query += df_info
            
            # Execute the agent
            result = await self.agent.arun(enhanced_query)
            
            return {
                "success": True,
                "answer": result,
                "dataframe_name": self.current_df_name,
                "dataframe_shape": self.current_df.shape,
                "original_query": query
            }
            
        except Exception as e:
            logger.error(f"Error processing natural language query: {e}")
            return {
                "error": f"Failed to process query: {str(e)}",
                "original_query": query
            }
    
    def execute_pandas_code(self, code: str) -> Dict[str, Any]:
        """
        Execute pandas code on the current dataframe
        
        Args:
            code: Python/pandas code to execute
            
        Returns:
            Dictionary with execution results
        """
        if self.current_df is None:
            return {"error": "No dataframe available"}
        
        try:
            # Create a safe execution environment
            local_vars = {
                'df': self.current_df,
                'pd': pd,
                'np': np
            }
            
            # Execute the code
            exec(code, {"__builtins__": {}}, local_vars)
            
            # Get the result (if any)
            result = local_vars.get('result', "Code executed successfully")
            
            # Convert result to string if it's a DataFrame or Series
            if isinstance(result, (pd.DataFrame, pd.Series)):
                result = result.to_string()
            
            return {
                "success": True,
                "result": str(result),
                "code": code
            }
            
        except Exception as e:
            logger.error(f"Error executing pandas code: {e}")
            return {
                "error": str(e),
                "code": code
            }
    
    def generate_visualization(
        self, 
        chart_type: str, 
        columns: List[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate data visualization
        
        Args:
            chart_type: Type of chart ('histogram', 'scatter', 'bar', 'line', 'heatmap')
            columns: Columns to use for visualization
            **kwargs: Additional matplotlib/seaborn arguments
            
        Returns:
            Dictionary with base64 encoded image
        """
        if self.current_df is None:
            return {"error": "No dataframe available"}
        
        try:
            plt.figure(figsize=(10, 6))
            
            if chart_type == 'histogram':
                if columns and len(columns) >= 1:
                    self.current_df[columns[0]].hist(**kwargs)
                    plt.title(f"Histogram of {columns[0]}")
                else:
                    return {"error": "Histogram requires at least 1 column"}
            
            elif chart_type == 'scatter':
                if columns and len(columns) >= 2:
                    plt.scatter(self.current_df[columns[0]], self.current_df[columns[1]], **kwargs)
                    plt.xlabel(columns[0])
                    plt.ylabel(columns[1])
                    plt.title(f"Scatter plot: {columns[0]} vs {columns[1]}")
                else:
                    return {"error": "Scatter plot requires at least 2 columns"}
            
            elif chart_type == 'bar':
                if columns and len(columns) >= 1:
                    value_counts = self.current_df[columns[0]].value_counts().head(10)
                    value_counts.plot(kind='bar', **kwargs)
                    plt.title(f"Bar chart of {columns[0]}")
                    plt.xticks(rotation=45)
                else:
                    return {"error": "Bar chart requires at least 1 column"}
            
            elif chart_type == 'line':
                if columns and len(columns) >= 1:
                    self.current_df[columns].plot(kind='line', **kwargs)
                    plt.title(f"Line chart of {', '.join(columns)}")
                else:
                    return {"error": "Line chart requires at least 1 column"}
            
            elif chart_type == 'heatmap':
                numeric_cols = self.current_df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) >= 2:
                    sns.heatmap(self.current_df[numeric_cols].corr(), annot=True, **kwargs)
                    plt.title("Correlation Heatmap")
                else:
                    return {"error": "Heatmap requires at least 2 numeric columns"}
            
            else:
                return {"error": f"Unsupported chart type: {chart_type}"}
            
            plt.tight_layout()
            
            # Convert plot to base64 string
            img_buffer = BytesIO()
            plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
            img_buffer.seek(0)
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
            plt.close()
            
            return {
                "success": True,
                "chart_type": chart_type,
                "columns": columns,
                "image_base64": img_base64
            }
            
        except Exception as e:
            logger.error(f"Error generating visualization: {e}")
            plt.close()  # Ensure plot is closed even on error
            return {"error": str(e)}
    
    def get_query_suggestions(self) -> List[str]:
        """
        Get query suggestions based on current dataframe
        
        Returns:
            List of suggested queries
        """
        if self.current_df is None:
            return ["No CSV data loaded"]
        
        suggestions = [
            "What are the basic statistics of this dataset?",
            "Show me the first 10 rows of data",
            "What columns have missing values?",
            "How many rows and columns are in this dataset?",
            "What are the data types of each column?",
            "Show me a summary of each column",
            "Are there any duplicate rows?",
            "What are the unique values in each categorical column?"
        ]
        
        # Add column-specific suggestions
        numeric_cols = self.current_df.select_dtypes(include=[np.number]).columns
        categorical_cols = self.current_df.select_dtypes(include=['object']).columns
        
        if len(numeric_cols) > 0:
            col = numeric_cols[0]
            suggestions.extend([
                f"What is the average value of {col}?",
                f"Show me the distribution of {col}",
                f"Find outliers in {col}"
            ])
        
        if len(categorical_cols) > 0:
            col = categorical_cols[0]
            suggestions.extend([
                f"What are the most common values in {col}?",
                f"How many unique values are in {col}?",
                f"Show me the frequency distribution of {col}"
            ])
        
        if len(numeric_cols) >= 2:
            suggestions.append(f"What is the correlation between {numeric_cols[0]} and {numeric_cols[1]}?")
        
        return suggestions[:15]  # Return top 15 suggestions
    
    def list_dataframes(self) -> Dict[str, Any]:
        """
        List all loaded dataframes
        
        Returns:
            Dictionary with dataframe information
        """
        return {
            "dataframes": {
                name: {
                    "shape": df.shape,
                    "columns": df.columns.tolist()
                }
                for name, df in self.dataframes.items()
            },
            "current_dataframe": self.current_df_name
        }

# Factory function for easy instantiation
def create_csv_agent(llm: ChatOpenAI = None) -> CSVAgent:
    """Create a configured CSV agent instance"""
    return CSVAgent(llm=llm)

# Example usage and testing
if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    
    load_dotenv()
    
    async def test_csv_agent():
        # Create sample CSV data
        sample_data = """Name,Age,City,Salary,Department
John Doe,25,New York,50000,Engineering
Jane Smith,30,London,60000,Marketing
Bob Wilson,35,Toronto,55000,Engineering
Alice Brown,28,Sydney,58000,Sales
Charlie Davis,32,Berlin,62000,Marketing
Eva Johnson,29,Tokyo,59000,Engineering
Mike Brown,31,Paris,61000,Sales
Sarah Wilson,27,Madrid,57000,Marketing
Tom Garcia,33,Rome,63000,Engineering
Lisa Wang,26,Beijing,56000,Sales"""
        
        # Initialize CSV agent
        agent = CSVAgent()
        
        # Load sample data
        result = agent.load_csv_from_string(sample_data, "employees")
        print("Load result:", result)
        
        # Get dataframe info
        info = agent.get_dataframe_info()
        print("\nDataframe info:")
        print(f"Shape: {info['shape']}")
        print(f"Columns: {info['columns']}")
        
        # Test natural language queries
        test_queries = [
            "How many employees are there?",
            "What's the average salary?",
            "Which department has the most employees?",
            "Show me employees older than 30",
            "What's the salary range in the Engineering department?"
        ]
        
        for query in test_queries:
            print(f"\nQuery: {query}")
            result = await agent.process_natural_language_query(query)
            if result.get("success"):
                print(f"Answer: {result['answer']}")
            else:
                print(f"Error: {result.get('error')}")
    
    # Run test
    # asyncio.run(test_csv_agent())
