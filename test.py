from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "bolt://localhost:7687", 
    auth=("neo4j", "CAMDA@123121"))
driver.verify_connectivity()
driver.close()