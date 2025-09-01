import re
from langchain_ollama import OllamaLLM
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from typing import List, Dict, Any
import database

class MedicalQueryProcessor:
    def __init__(self, graph, llm):
        self.graph = graph
        self.llm = llm
        self.diagnosis_cache = {}
        
    def extract_diagnosis_info(self, user_query: str) -> tuple:
        """Extract diagnosis name and timeframe from user query"""
        diagnosis_keywords = ["diagnosed with", "have", "suffering from"]
        diagnosis_name = None
        
        for keyword in diagnosis_keywords:
            if keyword in user_query.lower():
                parts = user_query.lower().split(keyword)
                if len(parts) > 1:
                    diagnosis_name = parts[1].split(".")[0].strip()
                    break
        
        # Extract timeframe (look for numbers followed by "year(s)")
        timeframe_match = re.search(r'(\d+)\s*year', user_query.lower())
        timeframe = int(timeframe_match.group(1)) if timeframe_match else None
        
        return diagnosis_name, timeframe
    
    def get_complications_data(self, diagnosis_name: str, timeframe: int = None) -> List[Dict]:
        """Get complications data based on diagnosis and timeframe"""
        diagnosis_code = database.get_diagnosis_id(self.graph, diagnosis_name, self.diagnosis_cache)
        if not diagnosis_code:
            return None
        
        if timeframe:
            complications = database.get_complications_within_timeframe(self.graph, diagnosis_code, timeframe)
        else:
            complications = database.get_all_possible_complications(self.graph, diagnosis_code)
            
        # Round average years to 3 decimal places
        for comp in complications:
            if 'avg_years' in comp and comp['avg_years'] is not None:
                comp['avg_years'] = round(comp['avg_years'], 3)
            
        return complications
    
    def generate_response(self, query: str, complications_data: List[Dict], timeframe: int = None) -> str:
        """Generate natural language response from retrieved data"""
        formatted_data = ""
        for comp in complications_data:
            formatted_data += f"- {comp['complication_name']}: Typically occurs in {comp['avg_years']} years on average (frequency: {comp['frequency']})\n"
        
        system_prompt = """You are a medical assistant that helps patients understand potential complications from their diagnoses. 
        Provide clear, compassionate, and factual information based on the data provided.
        Be specific about timeframes and probabilities when available.
        Always remind the user that this is general information and they should consult their doctor."""
        
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""
            Patient Query: {query}
            
            Medical Data:
            {formatted_data}
            
            Please provide a helpful response about potential complications within {timeframe} years if specified.
            """)
        ])
        
        response = self.llm.invoke(prompt_template.format_messages())
        return response
    
    def process_query(self, user_query: str) -> dict:
        """Main method to process user queries and return comprehensive results"""
        diagnosis_name, timeframe = self.extract_diagnosis_info(user_query)
        
        if not diagnosis_name:
            return {
                "success": False,
                "error": "I couldn't identify the diagnosis from your query. Please specify what condition you're asking about."
            }
        
        complications = self.get_complications_data(diagnosis_name, timeframe)
        
        if complications is None:
            return {
                "success": False,
                "error": f"I couldn't find information about '{diagnosis_name}' in our database. Please check the spelling or try a different term."
            }
            
        if not complications:
            if timeframe:
                return {
                    "success": False,
                    "error": f"Based on our data, there are no common complications from {diagnosis_name} that typically occur within {timeframe} years."
                }
            else:
                return {
                    "success": False,
                    "error": f"No complication data found for {diagnosis_name} in our database."
                }
        
        response = self.generate_response(user_query, complications, timeframe)
        
        return {
            "success": True,
            "diagnosis": diagnosis_name,
            "timeframe": timeframe,
            "complications": complications,
            "response": response
        }