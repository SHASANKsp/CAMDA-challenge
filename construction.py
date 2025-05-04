#import
from neo4j import GraphDatabase
import ast

#neo4j connection
uri = "bolt://localhost:7687"
user = "neo4j"
password = "your_password"
driver = GraphDatabase.driver(uri, auth=(user, password))


def process_age(age_code):
    """Convert age codes"""
    return int(str(age_code)[1:])


def load_data_to_neo4j(csv_file):
    with driver.session() as session:
        with open(csv_file, 'r') as file:
            next(file)  #skip header
            for line in file:
                parts = line.strip().split(',', 2)
                if len(parts) < 3:
                    continue
                
                patient_id = parts[0]
                sex = parts[1] if parts[1] != 'NA' else None
                visits = ast.literal_eval(parts[2])
                
                #create/update patient node
                session.run(
                    "MERGE (p:Patient {id: $id}) "
                    "SET p.sex = $sex",
                    id=patient_id, sex=sex
                )
                
                #process each each sub-list in relations
                for visit in visits:
                    if not visit or len(visit) < 2:
                        continue
                    
                    age_code = visit[0]
                    age = process_age(age_code)
                    diagnoses = visit[1:]  #all elements after age
                    
                    #visit identifier
                    visit_identifier = f"{patient_id}_{age_code}"
                    
                    #create relationships for each diagnosis
                    for code in diagnoses:
                        session.run(
                            "MERGE (p:Patient {id: $patient_id}) "
                            "MERGE (d:Diagnosis {code: $code}) "
                            "MERGE (p)-[r:HAS_DIAGNOSIS {visit_identifier: $visit_identifier}]->(d) "
                            "SET r.age = $age",
                            patient_id=patient_id,
                            code=code,
                            visit_identifier=visit_identifier,
                            age=age
                        )

load_data_to_neo4j('processed.csv')
driver.close()