from neo4j import GraphDatabase
import ast
import csv
from collections import defaultdict
import statistics

# Neo4j connection
uri = "bolt://localhost:7687"
user = "neo4j"
password = "CAMDA@123121"
driver = GraphDatabase.driver(uri, auth=(user, password))

def load_disease_names(csv_file):
    """Load disease code-name mappings"""
    disease_names = {}
    with open(csv_file, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            disease_names[row['CODE_BPS']] = row['BPS_PATHOLOGY']
    return disease_names

def process_age(age_code):
    """Convert age codes (unchanged)"""
    return int(str(age_code)[1:])  # Convert "9070" to 70

def calculate_stats(intervals):
    """Calculate statistics in Python instead of using APOC"""
    if not intervals:
        return None
    return {
        'min': min(intervals),
        'max': max(intervals),
        'avg': sum(intervals) / len(intervals),
        'median': statistics.median(intervals),
        'count': len(intervals)
    }

def build_trajectory_graph(patient_csv, disease_csv):
    """Build simplified trajectory graph with age stats"""
    disease_names = load_disease_names(disease_csv)
    trajectory_data = defaultdict(list)
    
    # Process patient data
    with open(patient_csv, 'r') as file:
        next(file)  # Skip header
        for line_num, line in enumerate(file, 2):
            try:
                parts = line.strip().split(',', 2)
                if len(parts) < 3:
                    print(f"Skipping line {line_num}: Not enough columns")
                    continue
                
                patient_id, sex, visits_str = parts
                visits_str = visits_str.strip(' "')  # Clean string
                visits = ast.literal_eval(visits_str)
                
                # Extract all diagnoses with ages
                diagnoses = []
                for visit in visits:
                    if not visit or len(visit) < 2:
                        continue
                    
                    age_code, *codes = visit
                    try:
                        age = process_age(age_code)
                        diagnoses.extend((age, code) for code in codes if code in disease_names)
                    except Exception as e:
                        print(f"Error processing visit {visit}: {str(e)}")
                        continue
                
                # Sort by age and record consecutive pairs
                diagnoses.sort()
                for i in range(len(diagnoses)-1):
                    from_age, from_code = diagnoses[i]
                    to_age, to_code = diagnoses[i+1]
                    trajectory_data[(from_code, to_code)].append(to_age - from_age)
            
            except Exception as e:
                print(f"Error processing line {line_num}: {str(e)}")
                continue
    
    # Debug print to check transitions
    print("\nDiscovered transitions:")
    for (from_code, to_code), intervals in trajectory_data.items():
        print(f"{from_code} -> {to_code}: {len(intervals)} transitions")
    
    # Build the graph
    with driver.session() as session:
        # Clear existing data
        session.run("MATCH (n) DETACH DELETE n")
        
        # Create all diagnosis nodes
        for code, name in disease_names.items():
            session.run(
                "MERGE (d:Diagnosis {code: $code}) SET d.name = $name",
                code=code, name=name
            )
        
        # Create trajectory edges with statistics
        for (from_code, to_code), intervals in trajectory_data.items():
            if not intervals:
                continue
                
            stats = calculate_stats(intervals)
            session.run(
                """
                MATCH (d1:Diagnosis {code: $from_code})
                MATCH (d2:Diagnosis {code: $to_code})
                MERGE (d1)-[r:PROGRESSES_TO]->(d2)
                SET r.frequency = $count,
                    r.min_years = $min,
                    r.max_years = $max,
                    r.avg_years = $avg,
                    r.median_years = $median
                """,
                from_code=from_code,
                to_code=to_code,
                count=stats['count'],
                min=stats['min'],
                max=stats['max'],
                avg=stats['avg'],
                median=stats['median']
            )
        
        print(f"Created {len(trajectory_data)} trajectory relationships")

if __name__ == "__main__":
    build_trajectory_graph('data/processed.csv', 'data/BPS_pathologies_gen3.csv')
    driver.close()
    print("Trajectory KG built successfully!")