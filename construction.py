#imports
from neo4j import GraphDatabase
import ast
import csv

#connecting neo4j
uri = "bolt://localhost:7687"
user = "neo4j"
password = "your_password"
driver = GraphDatabase.driver(uri, auth=(user, password))

#indexing
def create_indexes(session):
    """Create indexes and constraints"""
    #nodes
    session.run("CREATE INDEX patient_id_index IF NOT EXISTS FOR (p:Patient) ON (p.id)")
    session.run("CREATE INDEX diagnosis_code_index IF NOT EXISTS FOR (d:Diagnosis) ON (d.code)")
    session.run("CREATE INDEX diagnosis_name_index IF NOT EXISTS FOR (d:Diagnosis) ON (d.name)")
    
    #edge properties
    session.run("CREATE INDEX has_diagnosis_age_index IF NOT EXISTS FOR ()-[r:HAS_DIAGNOSIS]-() ON (r.age)")
    session.run("CREATE INDEX visit_identifier_index IF NOT EXISTS FOR ()-[r:HAS_DIAGNOSIS]-() ON (r.visit_identifier)")
    
    #constraints(uniqueness)
    session.run("CREATE CONSTRAINT patient_id_unique IF NOT EXISTS FOR (p:Patient) REQUIRE p.id IS UNIQUE")
    session.run("CREATE CONSTRAINT diagnosis_code_unique IF NOT EXISTS FOR (d:Diagnosis) REQUIRE d.code IS UNIQUE")

def process_age(age_code):
    """Convert age codes (unchanged)"""
    return int(str(age_code)[1:])

def load_disease_names(csv_file):
    """Load disease code-name mappings"""
    disease_names = {}
    with open(csv_file, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            disease_names[row['CODE_BPS']] = row['BPS_PATHOLOGY']
    return disease_names

def load_data_to_neo4j(csv_file, disease_names):
    with driver.session() as session:
        create_indexes(session) #indexing
        
        with open(csv_file, 'r') as file:
            next(file)
            for line in file:
                parts = line.strip().split(',', 2)
                if len(parts) < 3:
                    continue
                
                patient_id = parts[0]
                sex = parts[1] if parts[1] != 'NA' else None
                visits = ast.literal_eval(parts[2])
                
                #patient node
                session.run(
                    "MERGE (p:Patient {id: $id}) "
                    "SET p.sex = $sex",
                    id=patient_id, sex=sex
                )
                
                for visit in visits:
                    if not visit or len(visit) < 2:
                        continue
                    
                    age_code = visit[0]
                    age = process_age(age_code)
                    diagnoses = visit[1:] 
                    visit_identifier = f"{patient_id}_{age_code}"
                    
                    for code in diagnoses:
                        name = disease_names.get(code, 'Unknown')
                        session.run(
                            "MERGE (p:Patient {id: $patient_id}) "
                            "MERGE (d:Diagnosis {code: $code}) "
                            "SET d.name = $name "
                            "MERGE (p)-[r:HAS_DIAGNOSIS {visit_identifier: $visit_identifier}]->(d) "
                            "SET r.age = $age",
                            patient_id=patient_id,
                            code=code,
                            name=name,
                            visit_identifier=visit_identifier,
                            age=age
                        )

disease_names = load_disease_names('BPS_pathologies_gen3.csv')
load_data_to_neo4j('processed.csv', disease_names)
driver.close()