import os
from langchain_community.graphs import Neo4jGraph
from typing import List, Dict, Any

def initialize_neo4j_connection() -> Neo4jGraph:
    """Initialize and return Neo4j connection"""
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USERNAME = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "CAMDA@123121")
    
    try:
        graph = Neo4jGraph(url=NEO4J_URI, username=NEO4J_USERNAME, password=NEO4J_PASSWORD)
        print("✓ Neo4j connection established successfully")
        return graph
    except Exception as e:
        print(f"✗ Failed to connect to Neo4j: {e}")
        raise

def get_diagnosis_id(graph: Neo4jGraph, diagnosis_name: str, cache: dict) -> str:
    """Get diagnosis code from name with caching"""
    if diagnosis_name in cache:
        return cache[diagnosis_name]
        
    query = """
    MATCH (d:Diagnosis) 
    WHERE toLower(d.name) CONTAINS toLower($name) OR toLower(d.code) CONTAINS toLower($name)
    RETURN d.code as code, d.name as name
    LIMIT 5
    """
    
    result = graph.query(query, params={"name": diagnosis_name})
    
    if result and len(result) > 0:
        cache[diagnosis_name] = result[0]['code']
        return result[0]['code']
    return None

def get_complications_within_timeframe(graph: Neo4jGraph, diagnosis_code: str, years: int = 2) -> List[Dict]:
    """Get complications that typically progress within given years"""
    query = """
    MATCH (start:Diagnosis {code: $code})-[rel:PROGRESSES_TO]->(complication:Diagnosis)
    WHERE rel.overall_avg_years <= $years 
       OR rel.overall_median_years <= $years
       OR rel.overall_max_years <= $years
    RETURN 
        complication.code as complication_code,
        complication.name as complication_name,
        rel.overall_avg_years as avg_years,
        rel.overall_median_years as median_years,
        rel.overall_min_years as min_years,
        rel.overall_max_years as max_years,
        rel.overall_frequency as frequency
    ORDER BY rel.overall_frequency DESC
    """
    
    result = graph.query(query, params={"code": diagnosis_code, "years": years})
    return result

def get_all_possible_complications(graph: Neo4jGraph, diagnosis_code: str) -> List[Dict]:
    """Get all possible complications regardless of timeframe"""
    query = """
    MATCH (start:Diagnosis {code: $code})-[rel:PROGRESSES_TO]->(complication:Diagnosis)
    RETURN 
        complication.code as complication_code,
        complication.name as complication_name,
        rel.overall_avg_years as avg_years,
        rel.overall_median_years as median_years,
        rel.overall_min_years as min_years,
        rel.overall_max_years as max_years,
        rel.overall_frequency as frequency
    ORDER BY rel.overall_frequency DESC
    """
    
    result = graph.query(query, params={"code": diagnosis_code})
    return result