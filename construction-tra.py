from neo4j import GraphDatabase
import ast
import csv
from collections import defaultdict
import statistics
import json

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
    """Calculate statistics for a list of intervals"""
    if not intervals:
        return None
    return {
        'min': min(intervals),
        'max': max(intervals),
        'avg': sum(intervals) / len(intervals),
        'median': statistics.median(intervals),
        'std_dev': statistics.stdev(intervals) if len(intervals) > 1 else 0,
        'count': len(intervals),
        'q1': statistics.quantiles(intervals, n=4)[0] if len(intervals) >= 4 else None,
        'q3': statistics.quantiles(intervals, n=4)[2] if len(intervals) >= 4 else None
    }

def get_gender_prefix(gender_code):
    """Convert numeric gender codes to valid Neo4j property names"""
    gender_mapping = {
        '1111': 'male',
        '2222': 'female',
        'UNKNOWN': 'unknown'
    }
    return gender_mapping.get(gender_code, f"gender_{gender_code}")

def build_trajectory_graph(patient_csv, disease_csv):
    """Build trajectory graph with gender stratification and detailed data"""
    disease_names = load_disease_names(disease_csv)
    trajectory_data = defaultdict(lambda: defaultdict(list))
    
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
                
                # Handle missing/unknown gender
                if sex not in ['1111', '2222']:
                    sex = 'UNKNOWN'
                
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
                
                # Sort by age and record consecutive pairs with gender info
                diagnoses.sort()
                for i in range(len(diagnoses)-1):
                    from_age, from_code = diagnoses[i]
                    to_age, to_code = diagnoses[i+1]
                    time_interval = to_age - from_age
                    
                    # Store with gender stratification
                    trajectory_data[(from_code, to_code)][sex].append(time_interval)
            
            except Exception as e:
                print(f"Error processing line {line_num}: {str(e)}")
                continue
    
    # Debug print to check transitions
    print("\nDiscovered transitions:")
    for (from_code, to_code), gender_data in trajectory_data.items():
        total_transitions = sum(len(intervals) for intervals in gender_data.values())
        print(f"{from_code} -> {to_code}: {total_transitions} total transitions")
        for gender, intervals in gender_data.items():
            gender_name = get_gender_prefix(gender)
            print(f"  {gender_name}: {len(intervals)} transitions")
    
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
        
        # Create trajectory edges with gender-stratified statistics and raw data
        for (from_code, to_code), gender_data in trajectory_data.items():
            if not gender_data:
                continue
            
            # Calculate overall statistics (across all genders)
            all_intervals = []
            for intervals in gender_data.values():
                all_intervals.extend(intervals)
            
            if not all_intervals:
                continue
                
            overall_stats = calculate_stats(all_intervals)
            
            # Prepare properties for all genders
            properties = {
                'overall_frequency': overall_stats['count'],
                'overall_min_years': overall_stats['min'],
                'overall_max_years': overall_stats['max'],
                'overall_avg_years': overall_stats['avg'],
                'overall_median_years': overall_stats['median'],
                'overall_std_dev': overall_stats['std_dev'],
                'overall_q1': overall_stats['q1'],
                'overall_q3': overall_stats['q3']
            }
            
            # Add gender-specific properties
            for gender_code, intervals in gender_data.items():
                if not intervals:
                    continue
                    
                gender_stats = calculate_stats(intervals)
                gender_prefix = get_gender_prefix(gender_code)
                
                properties.update({
                    f'{gender_prefix}_frequency': gender_stats['count'],
                    f'{gender_prefix}_min_years': gender_stats['min'],
                    f'{gender_prefix}_max_years': gender_stats['max'],
                    f'{gender_prefix}_avg_years': gender_stats['avg'],
                    f'{gender_prefix}_median_years': gender_stats['median'],
                    f'{gender_prefix}_std_dev': gender_stats['std_dev'],
                    f'{gender_prefix}_q1': gender_stats['q1'],
                    f'{gender_prefix}_q3': gender_stats['q3'],
                    f'{gender_prefix}_raw_data': json.dumps(intervals)
                })
            
            # Create relationship with all properties in a single query
            query = """
            MATCH (d1:Diagnosis {code: $from_code})
            MATCH (d2:Diagnosis {code: $to_code})
            MERGE (d1)-[r:PROGRESSES_TO]->(d2)
            SET r += $properties
            """
            
            session.run(query, from_code=from_code, to_code=to_code, properties=properties)
        
        print(f"Created {len(trajectory_data)} trajectory relationships with gender stratification")

if __name__ == "__main__":
    build_trajectory_graph('data/processed.csv', 'data/BPS_pathologies_gen3.csv')
    driver.close()
    print("Trajectory KG built successfully with gender stratification!")