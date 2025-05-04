#imports
from neo4j import GraphDatabase
import ast
import csv

#connecting neo4j
uri = "bolt://localhost:7687"
user = "neo4j"
password = "CAMDA@123121"
driver = GraphDatabase.driver(uri, auth=(user, password))

#indexing
def create_indexes(session):
    """Create indexes and constraints"""
    # Clear any existing conflicting indexes
    session.run("DROP INDEX patient_id_index IF EXISTS")
    session.run("DROP INDEX diagnosis_code_index IF EXISTS")
    
    # Create constraints (will auto-create indexes)
    session.run("CREATE CONSTRAINT patient_id_unique IF NOT EXISTS FOR (p:Patient) REQUIRE p.id IS UNIQUE")
    session.run("CREATE CONSTRAINT diagnosis_code_unique IF NOT EXISTS FOR (d:Diagnosis) REQUIRE d.code IS UNIQUE")
    
    # Create other indexes
    session.run("CREATE INDEX IF NOT EXISTS FOR (d:Diagnosis) ON (d.name)")
    session.run("CREATE INDEX IF NOT EXISTS FOR ()-[r:HAS_DIAGNOSIS]-() ON (r.age)")
    session.run("CREATE INDEX IF NOT EXISTS FOR ()-[r:HAS_DIAGNOSIS]-() ON (r.visit_identifier)")

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
        with open(csv_file, 'r') as file:
            next(file)  # Skip header
            for line in file:
                try:
                    # Split the line while preserving the relation structure
                    parts = line.strip().split(',', 2)
                    if len(parts) < 3:
                        continue
                    
                    patient_id, sex, visits_str = parts
                    
                    # Clean and parse the visits list
                    visits_str = visits_str.strip(' "')  # Remove outer quotes if present
                    visits = ast.literal_eval(visits_str)
                    
                    print(f"\nProcessing Patient {patient_id}:")
                    print(f"Raw visits data: {visits_str}")
                    print(f"Parsed visits: {visits}")
                    
                    # Create patient node
                    session.run(
                        "MERGE (p:Patient {id: $id}) SET p.sex = $sex",
                        id=patient_id, sex=sex if sex != 'NA' else None
                    )
                    
                    # Process each visit
                    for visit in visits:
                        if not visit or len(visit) < 2:
                            print(f"  ⚠️ Skipping invalid visit: {visit}")
                            continue
                        
                        age_code, *diagnoses = visit
                        try:
                            age = int(age_code[1:])  # Convert "9070" to 70
                        except:
                            print(f"  ⚠️ Invalid age code: {age_code}")
                            continue
                        
                        print(f"  Visit at age {age}: Diagnoses {diagnoses}")
                        
                        # Process each diagnosis in the visit
                        for code in diagnoses:
                            name = disease_names.get(code, 'UNKNOWN_CODE')
                            
                            # Create Diagnosis node
                            session.run(
                                "MERGE (d:Diagnosis {code: $code}) SET d.name = $name",
                                code=code, name=name
                            )
                            
                            # Create relationship
                            result = session.run(
                                """
                                MATCH (p:Patient {id: $patient_id})
                                MATCH (d:Diagnosis {code: $code})
                                MERGE (p)-[r:HAS_DIAGNOSIS {
                                    age: $age,
                                    visit_identifier: $visit_id
                                }]->(d)
                                RETURN id(r) AS rel_id
                                """,
                                patient_id=patient_id,
                                code=code,
                                age=age,
                                visit_id=f"{patient_id}_{age_code}"
                            )
                            
                            if not result.single():
                                print(f"    ❗ Failed to create relationship for {code}")
                            else:
                                print(f"    ✅ Created relationship for {code}")
                
                except Exception as e:
                    print(f"🔥 Error processing line: {str(e)}")
                    print(f"Problematic line: {line[:100]}...")
                    continue  # Skip to next line

disease_names = load_disease_names('data/BPS_pathologies_gen3.csv')
load_data_to_neo4j('data/processed.csv', disease_names)
driver.close()