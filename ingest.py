import pandas as pd
from py2neo import Graph, Node, Relationship
import ast

# Connect to Neo4j (default: http://localhost:7474)
neo4j_graph = Graph("bolt://localhost:7687", auth=("neo4j", "password"))

# Load the CSV
df = pd.read_csv("processed.csv")

# Clear existing data (optional)
neo4j_graph.delete_all()

# Iterate through each patient
for _, row in df.iterrows():
    patient_id = row["id"]
    sex = row["sex"] if pd.notna(row["sex"]) else "NA"

    # Create patient node
    patient = Node("Patient", id=patient_id, sex=sex)
    neo4j_graph.create(patient)

    # Parse visits
    if pd.notna(row["relation"]):
        visits = ast.literal_eval(row["relation"])
        for visit_idx, visit in enumerate(visits):
            if not visit:
                continue
            age = visit[0]
            diagnoses = visit[1:]

            # Create visit node
            visit_node = Node("Visit", id=f"{patient_id}_{visit_idx}", age=age)
            neo4j_graph.create(visit_node)
            neo4j_graph.create(Relationship(patient, "HAS_VISIT", visit_node))

            # Link diagnoses
            for diag in diagnoses:
                diagnosis = Node("Diagnosis", code=diag)
                neo4j_graph.merge(diagnosis, "Diagnosis", "code")
                neo4j_graph.create(Relationship(visit_node, "HAS_DIAGNOSIS", diagnosis))

print("Neo4j graph populated successfully.")