# Temporal Knowledge Graph - Neo4j-Based Implementation for Disease Progression Analysis

## Overview  
This project constructs a **temporal knowledge graph** from diabetes patient records using **Neo4j**, enabling the analysis of disease progression, complication pathways, and early risk prediction.  
The graph models:  
- **Patients**   
- **Diagnoses**  
- **Temporal relationships**  

**Key Features:**  
- Age aware analysis (e.g., retinopathy risk at age 50+)  
- Disease trajectory modeling (e.g., diabetes → kidney disease)  
- Comorbidity detection (frequent co-occurring conditions)  



## Data Structure  
| Column       | Description                                                                 |
|--------------|-----------------------------------------------------------------------------|
| `id`         | Unique patient identifier                                                   |
| `sex`        | `1111` (Male), `2222` (Female), `NA` (Unknown)                             |
| `relation`   | Nested lists of visits: `[ [age_code, diag1, diag2, ...], ... ]`           |

**Example:**  
- `"relation": [ [9045, "401", "703"], [9050, "1401"] ]`  
  → Age **45**: Diagnosed with diabetes (`401`) and retinopathy (`703`)  
  → Age **50**: Developed kidney disease (`1401`)  

---
## Prerequisites  
- Neo4j  
- Python   
- Neo4j Python Driver (`pip install neo4j`)  

## KG Schema
- Nodes

| Label	|Properties	|Example|  
|---|---|---|  
| Patient|	id, sex	|{id: "P001", sex: "1111"}|
| Diagnosis|	code, name|{code: "703", name: "Retinopathy"}|

- Relationships

|Type	|Direction	|Properties|
|---|---|---|
|HAS_DIAGNOSIS	|Patient→Diagnosis	|age, visit_identifier|

Example: Cypher Query to find instances where a patient above the age of 50 has been diagnosed with Retinopathy(703):
```
MATCH (p:Patient)-[r:HAS_DIAGNOSIS]->(d:Diagnosis)
WHERE d.code = "703" AND r.age > 50
RETURN p.id, r.age, d.code
```


## Key Analytical - Examples

|Finding|	Query |
|---|---| 
|Avg. time from diabetes → retinopathy	|5.2 years (SD: 3.1)|
|Top 3 comorbidities with diabetes	|Hypertension (402), Obesity (278), CKD (1401)|