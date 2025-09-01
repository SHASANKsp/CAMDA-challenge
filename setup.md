After installing **Neo4j Desktop**, follow these essential steps to set up your project's database and environment:

---

### **1. Create a New Database**
1. Open Neo4j Desktop.
2. Click **"New Project"**  and name it.
3. Under your project, click **"Add Database"** → **"Local DBMS"**.
   - Set a name.
   - Choose Neo4j version.
   - Set password.
4. Click **"Start"** to launch the database.

---

### **2. Configure Database Settings**
1. Go to your database → **"Settings"** tab.
2. Add these lines to `neo4j.conf` (critical for analytics):
   ```ini
   dbms.security.procedures.unrestricted=apoc.*,gds.*
   dbms.memory.heap.max_size=2G  # Adjust based on your RAM
   ```
3. Restart the database after changes.

---

### **3. Install Plugins**
1. Go to your database → **"Plugins"** tab.
2. Install:
   - **APOC**: For utility functions (e.g., data import/export).
   - **Graph Data Science (GDS)**: If you plan to run algorithms (e.g., centrality, community detection).

---

### **4. Verify Connection**
1. Open Neo4j Browser (click **"Open"** next to your DB).
2. Run a test query to confirm it works:
   ```cypher
   RETURN 'Hello, Neo4j!' AS message
   ```
3. Check APOC/GDS installation:
   ```cypher
   CALL apoc.help("apoc")
   CALL gds.list() 
   ```

---

### **5. Set Up Python Connection**
1. Note your connection details:
   - **Bolt URI**: `bolt://localhost:7687` (default).
   - **Username**: `neo4j` (default).
   - **Password**: What you set during DB creation.
2. Test connectivity in Python:
   ```python
   from neo4j import GraphDatabase

   driver = GraphDatabase.driver(
       "bolt://localhost:7687", 
       auth=("neo4j", "your_password")
   driver.verify_connectivity() 
   driver.close()
   ```
---