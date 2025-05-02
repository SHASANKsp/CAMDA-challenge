# CAMDA-challenge
Challenge: The Synthetic Clinical Health Records

## Aim: To create a temporal knowledge graph from the given dataset
Need to structure the data in a way that captures the temporal sequence of visits, diagnoses, and patient attributes.

## Proposed approach
### 1. The Graph Schema
The knowledge graph will consist of:
- **Nodes**:
  - Patient (with attributes: id, sex)
  - Diagnosis (code)
  - Age (at time of visit)
- **Edges**:
  - `HAS_VISIT` (between Patient and Visit, with timestamp)
  - `HAS_DIAGNOSIS` (between Visit and Diagnosis)
  - `AT_AGE` (between Visit and Age)

### 2. Transform the Data
The `relation` column contains nested lists where each sublist represents a visit with age and diagnosis codes.  
We need to parse this into structured records:
#### Example Transformation for One Patient:
For the first row:
```python
id: 0, 
sex: 2222, 
relation: "[['9070', '913'], ['9070', '401'], ['9072', '1302'], ['9074', '1401'], ['9075', '402'], ['9078', '507'], ['9080', '506', '212']]"
```

This would become:
```
Patient (ID: 0, Sex: 2222)
  |- Visit 1 (Age: 9070)
  |    |- Diagnosis: 913
  |- Visit 2 (Age: 9070)
  |    |- Diagnosis: 401
  |- Visit 3 (Age: 9072)
  |    |- Diagnosis: 1302
  ...
```

### 3. Temporal Aspect
To make the graph temporal:
- Use the `age` field as a timestamp.
- Add temporal attributes to edges.

### 4. Tools for Implementation
- **Python Libraries**: Using `py2neo` for Neo4j.
- **Processing Steps**:
  1. Parse the CSV.
  2. For each patient, extract visits and diagnoses.
  3. Create nodes and edges in the graph.

Refer to `ingest.py` for TKG constructuion



## Challange
1) Finding some strong relationships in diabetes-associated pathologies that allows to predict any pathology before this is diagnosed. Some well-known pathological diabetes consequences, which can be considered relevant endpoints to predict, can be:  
   a) Retinopathy (Code “703”),  
   b) Chronic kidney disease (Code “1401”),  
   c) Ischemic heart disease (Code “910”),  
   d) Amputations (Code “1999”)  
2) Another proposed challenge is the prediction of disease trajectories in diabetes patients (see for example: Jensen et al. Nat Commun. 2014)

---

### **1. Predicting Diabetes-Associated Pathologies**
#### **Schema Enhancements**
- **Add a `:Diabetes` node** to explicitly tag diabetic patients:
  ```cypher
  MERGE (d:Diagnosis {code: "250"}) // ICD-10 code for diabetes
  ```
- **Flag key pathologies** with relationships:
  ```cypher
  // Example: Link diabetes to retinopathy as a known complication
  MATCH (diab:Diagnosis {code: "250"}), (ret:Diagnosis {code: "703"})
  MERGE (diab)-[:PREDISPOSES_TO]->(ret)
  ```

#### **Prediction Queries**
```cypher
// Find patients who developed retinopathy AFTER diabetes diagnosis
MATCH (p:Patient)-[:HAS_VISIT]->(v1:Visit)-[:HAS_DIAGNOSIS]->(diab:Diagnosis {code: "250"})
MATCH (p)-[:HAS_VISIT]->(v2:Visit)-[:HAS_DIAGNOSIS]->(ret:Diagnosis {code: "703"})
WHERE toInteger(v2.age) > toInteger(v1.age) // Ensure retinopathy occurs later
RETURN p.id, v1.age AS diabetes_age, v2.age AS retinopathy_age
```

---

### **2. Predicting Disease Trajectories**
#### **Schema Enhancements**
- **Add temporal edges** between diagnoses:
  ```cypher
  // Link consecutive diagnoses in a patient's history
  MATCH (p:Patient)-[:HAS_VISIT]->(v1:Visit)-[:HAS_DIAGNOSIS]->(d1:Diagnosis)
  MATCH (p)-[:HAS_VISIT]->(v2:Visit)-[:HAS_DIAGNOSIS]->(d2:Diagnosis)
  WHERE toInteger(v2.age) > toInteger(v1.age)
  MERGE (d1)-[:PROGRESSES_TO {time_interval: toInteger(v2.age) - toInteger(v1.age)}]->(d2)
  ```

#### **Trajectory Analysis Queries**
```cypher
// Find common progression paths in diabetes patients
MATCH (diab:Diagnosis {code: "250"})-[:PROGRESSES_TO*1..3]->(target:Diagnosis)
WHERE target.code IN ["703", "1401", "910", "1999"]
RETURN diab.code AS start, [d IN nodes(path) | d.code] AS trajectory, 
       sum(relationships(path)[0].time_interval) AS total_time
ORDER BY total_time
```

#### **Jensen et al.-Style Analysis**
- **Temporal patterns**: Use Neo4j’s APML library for sequence mining.
- **Survival analysis**: Export time-to-event data (e.g., diabetes → CKD onset).

---

### **Key Advantages of Your TKG**
| Feature                          | Application 1 (Pathology Prediction) | Application 2 (Trajectories) |
|----------------------------------|--------------------------------------|-------------------------------|
| **Temporal Visits**              | ✅ Track diagnosis order             | ✅ Model progression timing   |
| **Diagnosis Relationships**      | ✅ Link comorbidities                | ✅ Extract causal pathways    |
| **Graph Algorithms**             | ✅ Centrality to find key nodes      | ✅ Pathfinding for trajectories|

---

### **Tools to Implement This**
1. **Neo4j Graph Algorithms**:
   ```cypher
   CALL gds.alpha.pipeline.linkPrediction.train(...) // Predict edges (e.g., diabetes → retinopathy)
   ```
2. **Python Integration**:
   ```python
   from py2neo import Graph
   import pandas as pd
   # Query and convert to DataFrame for scikit-learn
   df = neo4j_graph.run("""
       MATCH (p:Patient)-[:HAS_VISIT]->(v:Visit)-[:HAS_DIAGNOSIS]->(d:Diagnosis)
       RETURN p.id, d.code, v.age
   """).to_data_frame()
   ```
