"""
Database Module for Quality Control System
Optimized version with pagination, caching, batch inserts, and enhanced performance.
Includes: Permission-based access control system
"""

import pyodbc, re, hashlib, secrets, uuid, logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from contextlib import contextmanager
from functools import wraps
from config import DB_CONFIG

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DatabaseError(Exception): pass

def handle_db_errors(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except DatabaseError:
            raise
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}")
            raise DatabaseError(f"Database operation failed: {str(e)}")
    return wrapper

class Database:
    def __init__(self):
        self.connection_string = self._build_connection_string()
        self._connection_pool, self._max_pool_size, self._column_cache = [], 10, {}
        self._fault_cache = {}
        self._initialize_database()

    def _build_connection_string(self) -> str:
        base = {'DRIVER': DB_CONFIG['driver'], 'SERVER': DB_CONFIG['server'], 'DATABASE': DB_CONFIG['database'],
                'Connection Timeout': '30', 'Encrypt': 'no', 'TrustServerCertificate': 'yes'}
        if DB_CONFIG.get('trusted_connection', False):
            base['Trusted_Connection'] = 'yes'
        else:
            base['UID'] = DB_CONFIG['username']
            base['PWD'] = DB_CONFIG['password']
        return ';'.join(f"{k}={v}" for k, v in base.items())

    @contextmanager
    def get_connection(self):
        conn = None
        try:
            if self._connection_pool:
                conn = self._connection_pool.pop()
                try: conn.cursor().execute("SELECT 1")
                except: conn = None
            if not conn:
                conn = pyodbc.connect(self.connection_string, autocommit=False)
            yield conn
            conn.commit()
        except pyodbc.Error as e:
            if conn: conn.rollback()
            if "Cannot open database" in str(e):
                self._create_database()
                conn = pyodbc.connect(self.connection_string, autocommit=False)
                yield conn
                conn.commit()
            else:
                raise DatabaseError(f"Database operation failed: {str(e)}")
        except Exception as e:
            if conn: conn.rollback()
            raise DatabaseError(f"Unexpected error: {str(e)}")
        finally:
            if conn and len(self._connection_pool) < self._max_pool_size:
                self._connection_pool.append(conn)
            elif conn: conn.close()

    @handle_db_errors
    def execute_query(self, query: str, params: tuple = None, fetch_one=False, fetch_all=False):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            if fetch_one:
                row = cursor.fetchone()
                if row:
                    cols = [c[0] for c in cursor.description]
                    return dict(zip(cols, row))
                return None
            if fetch_all:
                rows = cursor.fetchall()
                if rows:
                    cols = [c[0] for c in cursor.description]
                    return [dict(zip(cols, r)) for r in rows]
                return []
            return cursor.rowcount

    def _create_database(self):
        trusted = DB_CONFIG.get('trusted_connection', False)
        master_conn = f"DRIVER={DB_CONFIG['driver']};SERVER={DB_CONFIG['server']};DATABASE=master;"
        master_conn += "Trusted_Connection=yes;" if trusted else f"UID={DB_CONFIG['username']};PWD={DB_CONFIG['password']};"
        conn = pyodbc.connect(master_conn, autocommit=True)
        conn.cursor().execute(f"IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = '{DB_CONFIG['database']}') CREATE DATABASE {DB_CONFIG['database']}")
        conn.close()

    @staticmethod
    def _hash_password(pwd: str) -> str:
        salt = secrets.token_hex(32)
        iterations = 100000
        h = hashlib.pbkdf2_hmac('sha256', pwd.encode(), salt.encode(), iterations)
        return f"{iterations}:{salt}:{h.hex()}"

    @staticmethod
    def _verify_password(pwd: str, hashed: str) -> bool:
        try:
            it, salt, hsh = hashed.split(':')
            new = hashlib.pbkdf2_hmac('sha256', pwd.encode(), salt.encode(), int(it))
            return new.hex() == hsh
        except: return False

    def _column_exists(self, cursor, table, col):
        if table in self._column_cache:
            return col.lower() in self._column_cache[table]
        cursor.execute("SELECT COUNT(*) FROM syscolumns WHERE name=? AND id=OBJECT_ID(?)", (col, table))
        exists = cursor.fetchone()[0] > 0
        if exists:
            self._column_cache.setdefault(table, set()).add(col.lower())
        return exists

    def _add_column_safe(self, cursor, table, col, col_def):
        if not self._column_exists(cursor, table, col):
            try:
                cursor.execute(f"ALTER TABLE {table} ADD {col} {col_def}")
                self._column_cache.setdefault(table, set()).add(col.lower())
                logger.info(f"Added column '{col}' to {table}")
            except Exception as e:
                if "Column names in each table must be unique" in str(e):
                    self._column_cache.setdefault(table, set()).add(col.lower())
                else:
                    logger.warning(f"Could not add column '{col}': {e}")

    def _initialize_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # --- USERS TABLE ---
            cursor.execute("""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
                CREATE TABLE users (id INT IDENTITY PRIMARY KEY, username NVARCHAR(50) UNIQUE NOT NULL,
                password_hash NVARCHAR(255) NOT NULL, full_name NVARCHAR(100) NOT NULL, email NVARCHAR(100),
                role NVARCHAR(50) DEFAULT 'viewer', is_active BIT DEFAULT 1, created_at DATETIME DEFAULT GETDATE(),
                last_login DATETIME, created_by INT)""")
            for col,defn in [('phone','NVARCHAR(20)'),('department','NVARCHAR(100)'),('profile_image','NVARCHAR(500)'),('updated_at','DATETIME')]:
                self._add_column_safe(cursor, 'users', col, defn)
            cursor.execute("IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='CHK_Role' AND xtype='C') ALTER TABLE users ADD CONSTRAINT CHK_Role CHECK (role IN ('admin','inspector','viewer','manager'))")

            # --- PRODUCTS TABLE ---
            cursor.execute("""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='products' AND xtype='U')
                CREATE TABLE products (id INT IDENTITY PRIMARY KEY, product_code NVARCHAR(50) UNIQUE NOT NULL,
                product_name NVARCHAR(100) NOT NULL, category NVARCHAR(50), batch_number NVARCHAR(50) NOT NULL,
                production_date DATE NOT NULL, expiry_date DATE, specification NVARCHAR(MAX), quantity INT DEFAULT 0,
                min_quantity INT DEFAULT 0, supplier NVARCHAR(200), status NVARCHAR(20) DEFAULT 'Active',
                created_by INT, created_at DATETIME DEFAULT GETDATE(), updated_at DATETIME)""")
            for col,defn in [('sub_category','NVARCHAR(50)'),('weight','DECIMAL(10,2)'),('unit','NVARCHAR(20)'),
                             ('location','NVARCHAR(100)'),('is_deleted','BIT DEFAULT 0'),('updated_by','INT'),('notes','NVARCHAR(MAX)')]:
                self._add_column_safe(cursor, 'products', col, defn)

            # --- INSPECTIONS TABLE ---
            cursor.execute("""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='inspections' AND xtype='U')
                CREATE TABLE inspections (id INT IDENTITY PRIMARY KEY, inspection_code NVARCHAR(50) UNIQUE NOT NULL,
                product_id INT NOT NULL, inspector_id INT NOT NULL, inspection_date DATETIME DEFAULT GETDATE(),
                quantity_checked INT DEFAULT 0, accepted_quantity INT DEFAULT 0, rejected_quantity INT DEFAULT 0,
                quality_score DECIMAL(5,2), defects NVARCHAR(MAX), status NVARCHAR(20) DEFAULT 'Completed',
                remarks NVARCHAR(MAX), created_at DATETIME DEFAULT GETDATE())""")
            for col,defn in [('inspection_type',"NVARCHAR(50) DEFAULT 'Routine'"),('sample_size','INT'),
                             ('defect_types','NVARCHAR(500)'),('attachments','NVARCHAR(1000)'),('reviewed_by','INT'),
                             ('reviewed_at','DATETIME'),('updated_at','DATETIME'),('line','NVARCHAR(50)'),('floor','NVARCHAR(50)')]:
                self._add_column_safe(cursor, 'inspections', col, defn)
            
            # ========== FIX: Explicitly add ship and model columns to inspections ==========
            self._add_column_safe(cursor, 'inspections', 'ship', 'NVARCHAR(50)')
            self._add_column_safe(cursor, 'inspections', 'model', 'NVARCHAR(100)')
            self._add_column_safe(cursor, 'inspections', 'phone_type', 'NVARCHAR(20)')
            self._add_column_safe(cursor, 'fault_categories', 'phone_type', "NVARCHAR(20) DEFAULT 'Both'")
            

            cursor.execute("IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='FK_inspections_products' AND xtype='F') ALTER TABLE inspections ADD CONSTRAINT FK_inspections_products FOREIGN KEY (product_id) REFERENCES products(id)")
            cursor.execute("IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='FK_inspections_users' AND xtype='F') ALTER TABLE inspections ADD CONSTRAINT FK_inspections_users FOREIGN KEY (inspector_id) REFERENCES users(id)")

            # --- DEFECTS TABLE ---
            cursor.execute("""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='defects' AND xtype='U')
                CREATE TABLE defects (id INT IDENTITY PRIMARY KEY, inspection_id INT NOT NULL,
                defect_type NVARCHAR(100) NOT NULL, severity NVARCHAR(20) DEFAULT 'Minor', quantity INT DEFAULT 1,
                description NVARCHAR(MAX), location NVARCHAR(200), image_path NVARCHAR(500), created_at DATETIME DEFAULT GETDATE(),
                FOREIGN KEY (inspection_id) REFERENCES inspections(id) ON DELETE CASCADE)""")
            cursor.execute("IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='CHK_Severity' AND xtype='C') ALTER TABLE defects ADD CONSTRAINT CHK_Severity CHECK (severity IN ('Critical','Major','Minor'))")

            # --- AUDIT LOG ---
            cursor.execute("""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='audit_log' AND xtype='U')
                CREATE TABLE audit_log (id INT IDENTITY PRIMARY KEY, table_name NVARCHAR(100), record_id INT,
                action NVARCHAR(50), old_value NVARCHAR(MAX), new_value NVARCHAR(MAX), changed_by INT,
                changed_at DATETIME DEFAULT GETDATE(), ip_address NVARCHAR(50))""")

            # --- NOTIFICATIONS ---
            cursor.execute("""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='notifications' AND xtype='U')
                CREATE TABLE notifications (id INT IDENTITY PRIMARY KEY, user_id INT NOT NULL, title NVARCHAR(200),
                message NVARCHAR(MAX), type NVARCHAR(50), is_read BIT DEFAULT 0, created_at DATETIME DEFAULT GETDATE(),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)""")

            # --- FAULT CATEGORIES & FAULTS ---
            cursor.execute("""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='fault_categories' AND xtype='U')
                CREATE TABLE fault_categories (id INT IDENTITY PRIMARY KEY, category_name NVARCHAR(100) NOT NULL,
                station_type NVARCHAR(50) NOT NULL, display_order INT DEFAULT 0, is_active BIT DEFAULT 1,
                icon NVARCHAR(10), description NVARCHAR(500), created_at DATETIME DEFAULT GETDATE(),
                created_by INT, updated_at DATETIME, CONSTRAINT CHK_FaultStationType CHECK (station_type IN ('Semi Test','MMI Test','Appearance Test','Final Test')))""")
            cursor.execute("""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='faults' AND xtype='U')
                CREATE TABLE faults (id INT IDENTITY PRIMARY KEY, category_id INT NOT NULL,
                fault_name NVARCHAR(200) NOT NULL, fault_code NVARCHAR(50), severity NVARCHAR(20) DEFAULT 'Minor',
                display_order INT DEFAULT 0, is_active BIT DEFAULT 1, created_at DATETIME DEFAULT GETDATE(),
                created_by INT, updated_at DATETIME, FOREIGN KEY (category_id) REFERENCES fault_categories(id) ON DELETE CASCADE,
                CONSTRAINT CHK_FaultSeverity CHECK (severity IN ('Critical','Major','Minor')))""")
            
             # ========== یہ نیا کوڈ یہاں ڈالیں (REWORK TABLES سے پہلے) ==========
            cursor.execute("""
                IF EXISTS (SELECT * FROM sysobjects WHERE name='CHK_FaultStationType' AND xtype='C')
                    ALTER TABLE fault_categories DROP CONSTRAINT CHK_FaultStationType
            """)
            cursor.execute("""
                ALTER TABLE fault_categories 
                ADD CONSTRAINT CHK_FaultStationType 
                CHECK (station_type IN ('Semi Test','MMI Test','Appearance Test','Final Test','Rework'))
            """)

            # --- REWORK TABLES ---
            cursor.execute("""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='rework_tasks' AND xtype='U')
                CREATE TABLE rework_tasks (id INT IDENTITY PRIMARY KEY, inspection_id INT NULL,
                source_station NVARCHAR(50) NOT NULL, fault_name NVARCHAR(200) NOT NULL,
                pending_quantity INT NOT NULL, resolved_quantity INT DEFAULT 0, status NVARCHAR(20) DEFAULT 'Pending',
                line NVARCHAR(50), model NVARCHAR(100), created_at DATETIME DEFAULT GETDATE(), updated_at DATETIME)""")
            cursor.execute("""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='rework_root_cause' AND xtype='U')
                CREATE TABLE rework_root_cause (id INT IDENTITY PRIMARY KEY, ship_no NVARCHAR(50), record_date DATE,
                line NVARCHAR(50), model NVARCHAR(100), fault_category NVARCHAR(100), fault_subcategory NVARCHAR(200),
                pcba_qty INT DEFAULT 0, material_qty INT DEFAULT 0, fixing_qty INT DEFAULT 0, soldering_qty INT DEFAULT 0,
                total_qty INT DEFAULT 0, remarks NVARCHAR(MAX), imported_at DATETIME DEFAULT GETDATE())""")
            cursor.execute("""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='rework_history' AND xtype='U')
                CREATE TABLE rework_history (id INT IDENTITY PRIMARY KEY, task_id INT NOT NULL, inspector_id INT NOT NULL,
                resolved_quantity INT NOT NULL, root_cause_stage NVARCHAR(50), remarks NVARCHAR(MAX),
                created_at DATETIME DEFAULT GETDATE(), FOREIGN KEY (task_id) REFERENCES rework_tasks(id))""")
            cursor.execute("""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='rework_completed' AND xtype='U')
                CREATE TABLE rework_completed (id INT IDENTITY PRIMARY KEY, line NVARCHAR(50) NOT NULL,
                model NVARCHAR(100) NOT NULL, fault_name NVARCHAR(200) NOT NULL, source_station NVARCHAR(50) NOT NULL,
                resolved_qty INT NOT NULL, resolution_date DATE NOT NULL, remarks NVARCHAR(MAX), imported_at DATETIME DEFAULT GETDATE())""")
            cursor.execute("""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='rework_resolution_mapping' AND xtype='U')
                CREATE TABLE rework_resolution_mapping (id INT IDENTITY PRIMARY KEY, fault_category NVARCHAR(100) NOT NULL,
                fault_subcategory NVARCHAR(200), root_cause NVARCHAR(500), responsible_dept NVARCHAR(100),
                solution_plan NVARCHAR(500), model NVARCHAR(100), ship_no NVARCHAR(50), record_date DATE,
                is_weak_point BIT DEFAULT 0, created_at DATETIME DEFAULT GETDATE(),
                updated_at DATETIME)""")
            
            for col, col_def in [('fault_subcategory', 'NVARCHAR(200)'),
                                 ('root_cause', 'NVARCHAR(500)'),
                                 ('responsible_dept', 'NVARCHAR(100)'),
                                 ('solution_plan', 'NVARCHAR(500)'),
                                 ('model', 'NVARCHAR(100)'),
                                 ('ship_no', 'NVARCHAR(50)'),
                                 ('record_date', 'DATE'),
                                 ('is_weak_point', 'BIT DEFAULT 0')]:
                self._add_column_safe(cursor, 'rework_resolution_mapping', col, col_def)

            self._add_column_safe(cursor, 'rework_history', 'root_cause_stage', 'NVARCHAR(50)')
            cursor.execute("""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='rework_details' AND xtype='U')
                CREATE TABLE rework_details (id INT IDENTITY PRIMARY KEY, inspection_id INT NOT NULL,
                fault_name NVARCHAR(200) NOT NULL, pcb NVARCHAR(255), material NVARCHAR(255), fixing NVARCHAR(255),
                solding NVARCHAR(255), created_at DATETIME DEFAULT GETDATE(),
                FOREIGN KEY (inspection_id) REFERENCES inspections(id) ON DELETE CASCADE)""")

            # ========== PERMISSION SYSTEM TABLES ==========
            cursor.execute("""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='pages' AND xtype='U')
                CREATE TABLE pages (
                    id INT IDENTITY PRIMARY KEY,
                    name NVARCHAR(100) NOT NULL,
                    route NVARCHAR(100) NOT NULL,
                    icon NVARCHAR(10) DEFAULT '📄',
                    description NVARCHAR(500),
                    display_order INT DEFAULT 0,
                    is_active BIT DEFAULT 1,
                    created_at DATETIME DEFAULT GETDATE()
                )""")

            cursor.execute("""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='page_functions' AND xtype='U')
                CREATE TABLE page_functions (
                    id INT IDENTITY PRIMARY KEY,
                    page_id INT NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
                    name NVARCHAR(100) NOT NULL,
                    code NVARCHAR(100) NOT NULL,
                    description NVARCHAR(500),
                    display_order INT DEFAULT 0,
                    is_active BIT DEFAULT 1,
                    created_at DATETIME DEFAULT GETDATE()
                )""")

            cursor.execute("""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='user_permissions' AND xtype='U')
                CREATE TABLE user_permissions (
                    id INT IDENTITY PRIMARY KEY,
                    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    page_id INT NOT NULL REFERENCES pages(id),
                    function_id INT NOT NULL REFERENCES page_functions(id),
                    is_allowed BIT DEFAULT 0,
                    granted_by INT REFERENCES users(id),
                    granted_at DATETIME DEFAULT GETDATE(),
                    UNIQUE(user_id, page_id, function_id)
                )""")

            cursor.execute("""IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='role_permissions' AND xtype='U')
                CREATE TABLE role_permissions (
                    id INT IDENTITY PRIMARY KEY,
                    role NVARCHAR(50) NOT NULL,
                    page_id INT NOT NULL REFERENCES pages(id),
                    function_id INT NOT NULL REFERENCES page_functions(id),
                    is_allowed BIT DEFAULT 1,
                    UNIQUE(role, page_id, function_id)
                )""")

            # --- INDEXES ---
            idxs = ["idx_users_username ON users(username)", "idx_users_role ON users(role)",
                    "idx_users_is_active ON users(is_active)",
                    "idx_products_code ON products(product_code)", "idx_products_status ON products(status)",
                    "idx_inspections_date ON inspections(inspection_date)",
                    "idx_inspections_product ON inspections(product_id)",
                    "idx_inspections_inspector_date ON inspections(inspector_id, inspection_date)",
                    "idx_inspections_product_date ON inspections(product_id, inspection_date)",
                    "idx_inspections_status ON inspections(status)",
                    "idx_defects_inspection ON defects(inspection_id)",
                    "idx_faults_category ON faults(category_id)", "idx_faults_active ON faults(is_active)",
                    "idx_fault_categories_station ON fault_categories(station_type)",
                    "idx_rework_tasks_inspection ON rework_tasks(inspection_id)",
                    "idx_rework_tasks_status ON rework_tasks(status)",
                    "idx_rework_tasks_line_model ON rework_tasks(line, model)",
                    "idx_rework_pending ON rework_tasks(pending_quantity)",
                    "idx_rework_history_task ON rework_history(task_id)",
                    "idx_rework_details_inspection ON rework_details(inspection_id)",
                    "idx_rework_resolution_mapping_category ON rework_resolution_mapping(fault_category)",
                    "idx_user_permissions_user ON user_permissions(user_id)",
                    "idx_user_permissions_page ON user_permissions(page_id)",
                    "idx_page_functions_page ON page_functions(page_id)",
                    "idx_role_permissions_role ON role_permissions(role)"]
            for idx in idxs:
                try:
                    name = idx.split()[0]
                    cursor.execute(f"IF NOT EXISTS (SELECT * FROM sysindexes WHERE name='{name}') CREATE INDEX {idx}")
                except: pass
            for idx in ["idx_rework_completed_line_model ON rework_completed(line, model)", "idx_rework_completed_date ON rework_completed(resolution_date)",
                        "idx_rework_resolution_mapping_model ON rework_resolution_mapping(model)",
                        "idx_rework_resolution_mapping_ship ON rework_resolution_mapping(ship_no)",
                        "idx_rework_resolution_mapping_date ON rework_resolution_mapping(record_date)",
                        "idx_rework_resolution_mapping_composite ON rework_resolution_mapping(fault_category, model, ship_no, record_date)"]:
                try: cursor.execute(f"IF NOT EXISTS (SELECT * FROM sysindexes WHERE name='{idx.split()[0]}') CREATE INDEX {idx}")
                except: pass

            # --- DEFAULT USERS & FAULT MAPPING ---
            self._insert_default_users(cursor)
            cursor.execute("SELECT COUNT(*) FROM rework_resolution_mapping")
            if cursor.fetchone()[0] == 0:
                default_map = [('LCD','Poor handling / ESD damage','Production','Add antistatic mats, retrain operators',1),
                               ('Soldering','Old soldering iron tips / low temperature','Maintenance','Replace tips every 2 weeks, daily temp check',1),
                               ('MIC','Supplier quality issue','Procurement','Implement incoming inspection for MIC lots',0),
                               ('Camera','Dust on lens during assembly','Production','Clean workstations daily, use dust covers',0),
                               ('Keypad','Wrong material batch','QA','Supplier audit + lot sampling before use',1),
                               ('Receiver','Poor connector alignment','Production','Add alignment jig',0),
                               ('Ringer','Incorrect component value','Engineering','Update BOM and verify',0),
                               ('Torch','LED soldering cold joint','Production','Reflow profile adjustment',0),
                               ('Dead','Power IC failure','Engineering','Change IC supplier, add test',1)]
                for cat,cause,dept,sol,weak in default_map:
                    cursor.execute("INSERT INTO rework_resolution_mapping (fault_category, root_cause, responsible_dept, solution_plan, is_weak_point, created_at) VALUES (?,?,?,?,?,GETDATE())", (cat,cause,dept,sol,weak))

    def _insert_default_users(self, cursor):
        for un,pw,full,email,role,dept in [('admin','admin123','System Administrator','admin@quality.com','admin','IT'),
                                           ('inspector','inspector123','Quality Inspector','inspector@quality.com','inspector','QA'),
                                           ('manager','manager123','Quality Manager','manager@quality.com','manager','Management'),
                                           ('viewer','viewer123','Quality Viewer','viewer@quality.com','viewer','QC')]:
            ph = self._hash_password(pw)
            cursor.execute("SELECT id FROM users WHERE username=?", (un,))
            existing = cursor.fetchone()
            if existing:
                cursor.execute("UPDATE users SET password_hash=?, full_name=?, email=?, role=?, department=?, is_active=1 WHERE username=?", (ph,full,email,role,dept,un))
            else:
                cursor.execute("INSERT INTO users (username, password_hash, full_name, email, role, department, is_active) VALUES (?,?,?,?,?,?,1)", (un,ph,full,email,role,dept))

    # ========== USER MANAGEMENT ==========
    @handle_db_errors
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        return self.execute_query("SELECT id, username, full_name, email, phone, role, department, is_active FROM users WHERE username=?", (username,), fetch_one=True)

    @handle_db_errors
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        if not email: return None
        return self.execute_query("SELECT id, username, full_name, email, role, department, is_active FROM users WHERE email=?", (email,), fetch_one=True)

    @handle_db_errors
    def delete_user(self, user_id: int, soft_delete: bool = True) -> bool:
        if soft_delete:
            rows = self.execute_query("UPDATE users SET is_active=0, updated_at=GETDATE() WHERE id=?", (user_id,))
            return rows > 0
        else:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM user_permissions WHERE user_id = ?", (user_id,))
                c.execute("DELETE FROM notifications WHERE user_id = ?", (user_id,))
                c.execute("DELETE FROM defects WHERE inspection_id IN (SELECT id FROM inspections WHERE inspector_id = ?)", (user_id,))
                c.execute("DELETE FROM rework_tasks WHERE inspection_id IN (SELECT id FROM inspections WHERE inspector_id = ?)", (user_id,))
                c.execute("DELETE FROM inspections WHERE inspector_id = ?", (user_id,))
                c.execute("DELETE FROM users WHERE id = ?", (user_id,))
                conn.commit()
                return c.rowcount > 0

    @handle_db_errors
    def update_user(self, user_id: int, user_data: Dict) -> bool:
        updates, params = [], []
        allowed = ['full_name','email','phone','role','department','is_active']
        for f in allowed:
            if f in user_data:
                updates.append(f"{f}=?")
                params.append(user_data[f])
        if 'password' in user_data and user_data['password']:
            updates.append("password_hash=?")
            params.append(self._hash_password(user_data['password']))
        if not updates:
            return False
        updates.append("updated_at=GETDATE()")
        params.append(user_id)
        self.execute_query(f"UPDATE users SET {', '.join(updates)} WHERE id=?", tuple(params))
        return True

    @handle_db_errors
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        user = self.execute_query("SELECT id, username, password_hash, full_name, email, phone, role, department, is_active, last_login FROM users WHERE username=? AND is_active=1", (username,), fetch_one=True)
        if user and self._verify_password(password, user['password_hash']):
            user.pop('password_hash')
            return user
        return None

    @handle_db_errors
    def update_last_login(self, user_id: int) -> bool:
        self.execute_query("UPDATE users SET last_login=GETDATE() WHERE id=?", (user_id,))
        return True

    @handle_db_errors
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        return self.execute_query("SELECT id, username, full_name, email, phone, role, department, is_active, created_at, last_login FROM users WHERE id=?", (user_id,), fetch_one=True)

    @handle_db_errors
    def get_all_users(self, active_only: bool = False) -> List[Dict]:
        q = "SELECT id, username, full_name, email, phone, role, department, is_active, created_at, last_login FROM users"
        if active_only: q += " WHERE is_active=1"
        q += " ORDER BY full_name"
        return self.execute_query(q, fetch_all=True)

    @handle_db_errors
    def create_user(self, user_data: Dict) -> Optional[int]:
        username = user_data['username'].strip()
        email = user_data.get('email', '').strip() if user_data.get('email') else None
        created_by = user_data.get('created_by', 1)

        if self.get_user_by_username(username):
            raise DatabaseError(f"Username '{username}' already exists.")
        if email and self.get_user_by_email(email):
            raise DatabaseError(f"Email '{email}' already exists.")
        if not self.get_user_by_id(created_by):
            raise DatabaseError(f"Invalid created_by user ID: {created_by}")

        ph = self._hash_password(user_data['password'])
        insert_sql = """
            INSERT INTO users 
            (username, password_hash, full_name, email, phone, role, department, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            username, ph, user_data['full_name'], email,
            user_data.get('phone'), user_data.get('role', 'viewer'),
            user_data.get('department'), created_by
        )

        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(insert_sql, params)
            except pyodbc.IntegrityError as e:
                raise DatabaseError(f"Duplicate key violation: {e}")
            except pyodbc.Error as e:
                raise DatabaseError(f"SQL error: {e}")

            if cursor.rowcount != 1:
                raise DatabaseError("Insert affected 0 rows. Possible constraint violation.")

            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if not row:
                raise DatabaseError("User was inserted but cannot be found by username.")
            user_id = int(row[0])

        self.apply_role_permissions(user_id, user_data.get('role', 'viewer'))
        return user_id

    # ========== PERMISSION SYSTEM API ==========
    @handle_db_errors
    def initialize_default_pages(self):
        with self.get_connection() as conn:
            c = conn.cursor()
            
            c.execute("SELECT COUNT(*) FROM pages")
            if c.fetchone()[0] > 0:
                return
            
            pages = [
                (1, 'Dashboard', 'dashboard', '📊', 'Main dashboard with statistics', 1),
                (2, 'User Management', 'users', '👥', 'Manage system users', 2),
                (3, 'Products', 'products', '📦', 'Product catalog management', 3),
                (4, 'Inspections', 'inspections', '🔍', 'Quality inspections', 4),
                (5, 'Defects', 'defects', '⚠️', 'Defect tracking', 5),
                (6, 'Rework Tasks', 'rework', '🔧', 'Rework management', 6),
                (7, 'Fault Categories', 'faults', '🏷️', 'Fault configuration', 7),
                (8, 'Reports', 'reports', '📈', 'Analytics and reports', 8),
                (9, 'Audit Log', 'audit', '📋', 'System audit trail', 9),
                (10, 'Settings', 'settings', '⚙️', 'System settings', 10),
            ]
            for p in pages:
                c.execute("SET IDENTITY_INSERT pages ON")
                c.execute("INSERT INTO pages (id, name, route, icon, description, display_order) VALUES (?,?,?,?,?,?)", p)
                c.execute("SET IDENTITY_INSERT pages OFF")
            
            functions = [
                (1, 'View', 'dashboard_view', 'Access dashboard', 1),
                (2, 'View', 'users_view', 'View users list', 1),
                (2, 'Create', 'users_create', 'Add new users', 2),
                (2, 'Edit', 'users_edit', 'Edit user profiles', 3),
                (2, 'Delete', 'users_delete', 'Delete users', 4),
                (2, 'Manage Permissions', 'users_permissions', 'Assign custom permissions', 5),
                (3, 'View', 'products_view', 'View products', 1),
                (3, 'Create', 'products_create', 'Add products', 2),
                (3, 'Edit', 'products_edit', 'Edit products', 3),
                (3, 'Delete', 'products_delete', 'Delete products', 4),
                (4, 'View', 'inspections_view', 'View inspections', 1),
                (4, 'Create', 'inspections_create', 'Create inspections', 2),
                (4, 'Edit', 'inspections_edit', 'Edit inspections', 3),
                (4, 'Delete', 'inspections_delete', 'Delete inspections', 4),
                (4, 'Export', 'inspections_export', 'Export inspection data', 5),
                (5, 'View', 'defects_view', 'View defects', 1),
                (5, 'Create', 'defects_create', 'Add defects', 2),
                (6, 'View', 'rework_view', 'View rework tasks', 1),
                (6, 'Resolve', 'rework_resolve', 'Resolve rework tasks', 2),
                (6, 'Export', 'rework_export', 'Export rework data', 3),
                (7, 'View', 'faults_view', 'View fault categories', 1),
                (7, 'Create', 'faults_create', 'Add fault categories', 2),
                (7, 'Edit', 'faults_edit', 'Edit fault categories', 3),
                (7, 'Delete', 'faults_delete', 'Delete fault categories', 4),
                (8, 'View', 'reports_view', 'View reports', 1),
                (8, 'Export', 'reports_export', 'Export reports', 2),
                (9, 'View', 'audit_view', 'View audit log', 1),
                (10, 'View', 'settings_view', 'View settings', 1),
                (10, 'Edit', 'settings_edit', 'Modify settings', 2),
            ]
            for f in functions:
                c.execute("INSERT INTO page_functions (page_id, name, code, description, display_order) VALUES (?,?,?,?,?)", f)
            
            roles = ['admin', 'manager', 'inspector', 'viewer']
            c.execute("SELECT id, code FROM page_functions")
            all_funcs = c.fetchall()
            
            for role in roles:
                for func_id, code in all_funcs:
                    is_allowed = 1
                    if role == 'viewer' and not code.endswith('_view'):
                        is_allowed = 0
                    if role == 'inspector' and any(x in code for x in ['_delete', '_permissions', '_settings_edit']):
                        is_allowed = 0
                    if role == 'manager' and 'permissions' in code:
                        is_allowed = 0
                    
                    c.execute("SELECT page_id FROM page_functions WHERE id = ?", (func_id,))
                    page_id = c.fetchone()[0]
                    
                    c.execute("""
                        INSERT INTO role_permissions (role, page_id, function_id, is_allowed)
                        VALUES (?, ?, ?, ?)
                    """, (role, page_id, func_id, is_allowed))
            
            conn.commit()
            logger.info("Default pages, functions and role permissions initialized")

    @handle_db_errors
    def get_all_pages_with_functions(self) -> List[Dict]:
        query = """
            SELECT p.id as page_id, p.name as page_name, p.icon, p.route,
                   pf.id as function_id, pf.name as function_name, pf.code, pf.description
            FROM pages p
            LEFT JOIN page_functions pf ON p.id = pf.page_id AND pf.is_active = 1
            WHERE p.is_active = 1
            ORDER BY p.display_order, pf.display_order
        """
        rows = self.execute_query(query, fetch_all=True)
        
        result = []
        current_page = None
        for row in rows:
            if current_page is None or current_page['page_id'] != row['page_id']:
                current_page = {
                    'page_id': row['page_id'],
                    'page_name': row['page_name'],
                    'icon': row['icon'],
                    'route': row['route'],
                    'functions': []
                }
                result.append(current_page)
            
            if row['function_id']:
                current_page['functions'].append({
                    'function_id': row['function_id'],
                    'function_name': row['function_name'],
                    'code': row['code'],
                    'description': row['description']
                })
        
        return result

    @handle_db_errors
    def get_user_permissions(self, user_id: int) -> List[Dict]:
        query = """
            SELECT up.*, p.name as page_name, p.icon, pf.name as function_name, pf.code
            FROM user_permissions up
            JOIN pages p ON up.page_id = p.id
            JOIN page_functions pf ON up.function_id = pf.id
            WHERE up.user_id = ?
            ORDER BY p.display_order, pf.display_order
        """
        return self.execute_query(query, (user_id,), fetch_all=True)

    @handle_db_errors
    def get_user_permissions_dict(self, user_id: int) -> Dict[str, bool]:
        perms = self.get_user_permissions(user_id)
        return {p['code']: bool(p['is_allowed']) for p in perms}

    @handle_db_errors
    def check_user_permission(self, user_id: int, function_code: str) -> bool:
        user = self.get_user_by_id(user_id)
        if user and user.get('role') == 'admin':
            return True
        
        query = """
            SELECT 1 FROM user_permissions up
            JOIN page_functions pf ON up.function_id = pf.id
            WHERE up.user_id = ? AND pf.code = ? AND up.is_allowed = 1
        """
        result = self.execute_query(query, (user_id, function_code), fetch_one=True)
        return result is not None

    @handle_db_errors
    def get_user_allowed_pages(self, user_id: int) -> List[Dict]:
        query = """
            SELECT DISTINCT p.* 
            FROM pages p
            JOIN user_permissions up ON p.id = up.page_id
            WHERE up.user_id = ? AND up.is_allowed = 1 AND p.is_active = 1
            ORDER BY p.display_order
        """
        return self.execute_query(query, (user_id,), fetch_all=True)

    @handle_db_errors
    def save_user_permissions(self, user_id: int, permissions: List[Dict], granted_by: int = None) -> bool:
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM user_permissions WHERE user_id = ?", (user_id,))
            
            for perm in permissions:
                if perm.get('is_allowed'):
                    c.execute("""
                        INSERT INTO user_permissions (user_id, page_id, function_id, is_allowed, granted_by, granted_at)
                        VALUES (?, ?, ?, 1, ?, GETDATE())
                    """, (user_id, perm['page_id'], perm['function_id'], granted_by))
            
            conn.commit()
            logger.info(f"Permissions updated for user {user_id}")
            return True

    @handle_db_errors
    def apply_role_permissions(self, user_id: int, role: str) -> bool:
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM user_permissions WHERE user_id = ?", (user_id,))
            
            c.execute("""
                INSERT INTO user_permissions (user_id, page_id, function_id, is_allowed)
                SELECT ?, rp.page_id, rp.function_id, rp.is_allowed
                FROM role_permissions rp
                WHERE rp.role = ? AND rp.is_allowed = 1
            """, (user_id, role))
            
            conn.commit()
            return True

    # ========== PRODUCT API ==========
    @handle_db_errors
    def get_all_products(self, status: str = None, category: str = None) -> List[Dict]:
        q = "SELECT id, product_code, product_name, category, batch_number, production_date, expiry_date, quantity, min_quantity, location, supplier, status, created_at FROM products WHERE (is_deleted=0 OR is_deleted IS NULL)"
        p = []
        if status: q += " AND status=?"; p.append(status)
        if category: q += " AND category=?"; p.append(category)
        q += " ORDER BY created_at DESC"
        return self.execute_query(q, tuple(p), fetch_all=True)

    @handle_db_errors
    def get_product_by_id(self, pid: int) -> Optional[Dict]:
        return self.execute_query("SELECT * FROM products WHERE id=? AND (is_deleted=0 OR is_deleted IS NULL)", (pid,), fetch_one=True)

    @handle_db_errors
    def get_product_by_code(self, code: str) -> Optional[Dict]:
        return self.execute_query("SELECT * FROM products WHERE product_code=? AND (is_deleted=0 OR is_deleted IS NULL)", (code,), fetch_one=True)

    @handle_db_errors
    def add_product(self, data: Dict) -> Optional[int]:
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO products (product_code, product_name, category, batch_number, production_date, expiry_date,
                                    specification, quantity, min_quantity, location, supplier, unit, created_by)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (data['product_code'], data['product_name'], data.get('category'), data['batch_number'],
                data['production_date'], data.get('expiry_date'), data.get('specification'),
                data.get('quantity',0), data.get('min_quantity',0), data.get('location'), data.get('supplier'),
                data.get('unit','pcs'), data.get('created_by',1)))
            c.execute("SELECT SCOPE_IDENTITY()")
            return c.fetchone()[0]

    @handle_db_errors
    def update_product(self, pid: int, data: Dict) -> bool:
        allowed = ['product_name','category','sub_category','specification','quantity','min_quantity','location','supplier','unit','status']
        updates, params = [], []
        for f in allowed:
            if f in data:
                updates.append(f"{f}=?")
                params.append(data[f])
        if not updates: return False
        params.append(pid)
        self.execute_query(f"UPDATE products SET {', '.join(updates)}, updated_at=GETDATE() WHERE id=?", tuple(params))
        return True

    @handle_db_errors
    def delete_product(self, pid: int, soft_delete: bool = True) -> bool:
        if soft_delete:
            self.execute_query("UPDATE products SET is_deleted=1, status='Inactive' WHERE id=?", (pid,))
        else:
            self.execute_query("DELETE FROM products WHERE id=?", (pid,))
        return True

    # ========== INSPECTION API ==========
    @handle_db_errors
    def add_inspection(self, data: Dict) -> Optional[int]:
        qty = data.get('quantity_checked',0)
        acc = data.get('accepted_quantity',0)
        rej = qty - acc
        qual = (acc / qty * 100) if qty > 0 else 0
        code = f"QC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8].upper()}"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""INSERT INTO inspections (inspection_code, product_id, inspector_id, inspection_type,
                quantity_checked, accepted_quantity, rejected_quantity, quality_score, defects, remarks, status, line, floor)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) SELECT SCOPE_IDENTITY()""",
                (code, data.get('product_id'), data['inspector_id'], data.get('inspection_type','Routine'), qty, acc, rej, qual,
                 data.get('defects'), data.get('remarks'), 'Completed', data.get('line'), data.get('floor')))
            insp_id = cursor.fetchone()[0]
            for d in data.get('defect_list', []):
                cursor.execute("INSERT INTO defects (inspection_id, defect_type, severity, quantity, description, location) VALUES (?,?,?,?,?,?) SELECT SCOPE_IDENTITY()",
                               (insp_id, d['defect_type'], d.get('severity','Minor'), d.get('quantity',1), d.get('description'), d.get('location')))
            return insp_id

    @handle_db_errors
    def get_all_inspections(self, filters: Dict = None) -> List[Dict]:
        q = """SELECT i.id, i.inspection_code, i.inspection_type, p.product_name, p.product_code, p.batch_number, u.full_name as inspector_name,
               i.inspection_date, i.quantity_checked, i.accepted_quantity, i.rejected_quantity, i.quality_score, i.status, i.defects, i.remarks, i.line, i.floor, i.created_at
               FROM inspections i LEFT JOIN products p ON i.product_id = p.id LEFT JOIN users u ON i.inspector_id = u.id WHERE 1=1"""
        p = []
        if filters:
            if filters.get('status'): q += " AND i.status=?"; p.append(filters['status'])
            if filters.get('product_id'): q += " AND i.product_id=?"; p.append(filters['product_id'])
            if filters.get('inspector_id'): q += " AND i.inspector_id=?"; p.append(filters['inspector_id'])
            if filters.get('date_from'): q += " AND CAST(i.inspection_date AS DATE) >= ?"; p.append(filters['date_from'])
            if filters.get('date_to'): q += " AND CAST(i.inspection_date AS DATE) <= ?"; p.append(filters['date_to'])
        q += " ORDER BY i.inspection_date DESC"
        return self.execute_query(q, tuple(p), fetch_all=True)

    @handle_db_errors
    def get_inspections_paginated(self, filters: Dict = None, page: int = 1, page_size: int = 50) -> Dict:
        offset = (page - 1) * page_size
        where_clause = ""
        params = []
        if filters:
            if filters.get('status'): where_clause += " AND i.status=?"; params.append(filters['status'])
            if filters.get('product_id'): where_clause += " AND i.product_id=?"; params.append(filters['product_id'])
            if filters.get('inspector_id'): where_clause += " AND i.inspector_id=?"; params.append(filters['inspector_id'])
            if filters.get('date_from'): where_clause += " AND CAST(i.inspection_date AS DATE) >= ?"; params.append(filters['date_from'])
            if filters.get('date_to'): where_clause += " AND CAST(i.inspection_date AS DATE) <= ?"; params.append(filters['date_to'])
        count_q = f"SELECT COUNT(*) FROM inspections i WHERE 1=1 {where_clause}"
        total = self.execute_query(count_q, tuple(params), fetch_one=True)['']
        data_q = f"""
            SELECT i.id, i.inspection_code, i.inspection_type, p.product_name, p.product_code, p.batch_number,
                   u.full_name as inspector_name, i.inspection_date, i.quantity_checked, i.accepted_quantity,
                   i.rejected_quantity, i.quality_score, i.status, i.defects, i.remarks, i.line, i.floor, i.created_at
            FROM inspections i
            LEFT JOIN products p ON i.product_id = p.id
            LEFT JOIN users u ON i.inspector_id = u.id
            WHERE 1=1 {where_clause}
            ORDER BY i.inspection_date DESC
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        params.extend([offset, page_size])
        data = self.execute_query(data_q, tuple(params), fetch_all=True)
        return {'data': data, 'total': total, 'page': page, 'page_size': page_size}

    @handle_db_errors
    def get_inspection_by_id(self, iid: int) -> Optional[Dict]:
        insp = self.execute_query("SELECT * FROM inspections WHERE id=?", (iid,), fetch_one=True)
        if insp:
            insp['defects_list'] = self.execute_query("SELECT * FROM defects WHERE inspection_id=? ORDER BY severity DESC", (iid,), fetch_all=True)
        return insp

    @handle_db_errors
    def get_inspection_statistics(self) -> Dict:
        stats = {}
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM products WHERE (is_deleted=0 OR is_deleted IS NULL)"); stats['total_products'] = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM products WHERE status='Active' AND (is_deleted=0 OR is_deleted IS NULL)"); stats['active_products'] = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM inspections"); stats['total_inspections'] = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM inspections WHERE CAST(inspection_date AS DATE)=CAST(GETDATE() AS DATE)"); stats['today_inspections'] = c.fetchone()[0]
            c.execute("SELECT AVG(CAST(quality_score AS FLOAT)) FROM inspections WHERE quality_score IS NOT NULL"); r = c.fetchone()[0]; stats['avg_quality_score'] = float(r) if r else 0
            c.execute("SELECT CASE WHEN COUNT(*)>0 THEN CAST(SUM(CASE WHEN quality_score>=80 THEN 1 ELSE 0 END) AS FLOAT)*100/COUNT(*) ELSE 0 END FROM inspections WHERE quality_score IS NOT NULL"); r = c.fetchone()[0]; stats['pass_rate'] = float(r) if r else 0
            c.execute("SELECT CASE WHEN SUM(quantity_checked)>0 THEN CAST(SUM(rejected_quantity) AS FLOAT)*100/SUM(quantity_checked) ELSE 0 END FROM inspections"); r = c.fetchone()[0]; stats['rejection_rate'] = float(r) if r else 0
            c.execute("SELECT TOP 5 i.inspection_code, ISNULL(p.product_name,'Unknown'), i.quality_score, i.status, i.inspection_date FROM inspections i LEFT JOIN products p ON i.product_id = p.id ORDER BY i.inspection_date DESC")
            stats['recent_inspections'] = [{'code':r[0],'product':r[1],'score':float(r[2]) if r[2] else 0,'status':r[3],'date':r[4]} for r in c.fetchall()]
        return stats

    @handle_db_errors
    def get_recent_inspections(self, limit: int = 10) -> List[Dict]:
        q = """SELECT TOP (?) i.id, i.inspection_code, i.inspection_type, i.inspection_date, i.status, i.quality_score,
               ISNULL(p.product_name,'N/A') as product_name, ISNULL(u.full_name,'Unknown') as inspector_name
               FROM inspections i LEFT JOIN products p ON i.product_id = p.id LEFT JOIN users u ON i.inspector_id = u.id
               ORDER BY i.inspection_date DESC"""
        return self.execute_query(q, (limit,), fetch_all=True)

    # ========== FAULT MANAGEMENT API ==========
    @handle_db_errors
    def get_fault_categories(self, station: str, phone_type: str = None) -> List[Dict]:
        cache_key = f"{station}_{phone_type}" if phone_type else station
        if cache_key in self._fault_cache:
            return self._fault_cache[cache_key]
        query = "SELECT id, category_name, display_order, icon, description, is_active FROM fault_categories WHERE station_type=? AND is_active=1"
        params = [station]
        if phone_type:
            query += " AND phone_type = ?"
            params.append(phone_type)
        query += " ORDER BY display_order"
        data = self.execute_query(query, tuple(params), fetch_all=True)
        self._fault_cache[cache_key] = data
        return data

    @handle_db_errors
    def invalidate_fault_cache(self):
        self._fault_cache.clear()

    @handle_db_errors
    def get_faults_by_category(self, cat_id: int) -> List[Dict]:
        return self.execute_query("SELECT id, fault_name, fault_code, severity, display_order, is_active FROM faults WHERE category_id=? AND is_active=1 ORDER BY display_order", (cat_id,), fetch_all=True)

    @handle_db_errors
    def get_all_faults_by_station(self, station: str) -> Dict:
        query = """
            SELECT c.category_name, c.id as category_id, 
                   f.id as fault_id, f.fault_name, f.fault_code, f.severity
            FROM fault_categories c
            LEFT JOIN faults f ON c.id = f.category_id AND f.is_active = 1
            WHERE c.station_type = ? AND c.is_active = 1
            ORDER BY c.display_order, f.display_order
        """
        rows = self.execute_query(query, (station,), fetch_all=True)
        result = {}
        for row in rows:
            cat_name = row['category_name']
            if cat_name not in result:
                result[cat_name] = {'category_id': row['category_id'], 'faults': []}
            if row['fault_id']:
                result[cat_name]['faults'].append({
                    'id': row['fault_id'],
                    'fault_name': row['fault_name'],
                    'fault_code': row['fault_code'],
                    'severity': row['severity']
                })
        return result
    
    @handle_db_errors
    def save_rework_entries(self, rework_data):
        if isinstance(rework_data, dict):
            rework_data = [rework_data]
        if not rework_data:
            return True

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for entry in rework_data:
                sql = """
                    INSERT INTO rework_root_cause 
                    (ship_no, record_date, line, model, fault_category, fault_subcategory,
                     pcba_qty, material_qty, fixing_qty, soldering_qty, total_qty, remarks, imported_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
                """
                cursor.execute(sql, (
                    entry.get('ship_no'),
                    entry.get('record_date'),
                    entry.get('line'),
                    entry.get('model'),
                    entry.get('fault_category'),
                    entry.get('fault_subcategory'),
                    entry.get('pcba_qty', 0),
                    entry.get('material_qty', 0),
                    entry.get('fixing_qty', 0),
                    entry.get('soldering_qty', 0),
                    entry.get('total_qty', 0),
                    entry.get('remarks')
                ))
            conn.commit()
        return True

    # ======================================================================
    # FIXED METHOD: save_rework_root_cause_from_inspection
    # Now fetches ship/model directly from inspection and splits fault name
    # ======================================================================
    @handle_db_errors
    def save_rework_root_cause_from_inspection(self, inspection_id: int, rework_entries: List[tuple]) -> bool:
        """
        rework_entries: list of tuples (fault_name, pcb_qty, material_qty, fixing_qty, solding_qty)
        Upsert into rework_root_cause table based on (record_date, line, model, fault_category, fault_subcategory)
        Now matches the import logic exactly.
        """
        if not rework_entries:
            return True

        # 1. Get inspection details (now includes ship and model columns)
        insp = self.get_inspection_by_id(inspection_id)
        if not insp:
            raise DatabaseError(f"Inspection with id {inspection_id} not found.")

        record_date = insp.get('inspection_date')
        if isinstance(record_date, datetime):
            record_date = record_date.date()
        line = insp.get('line', '')
        model = insp.get('model', '')   # Directly from inspections table
        ship = insp.get('ship', '')     # Directly from inspections table

        # 2. Loop through entries and upsert
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for fault_name, pcb_qty, material_qty, fixing_qty, solding_qty in rework_entries:
                # Convert to integers
                pcb = int(pcb_qty) if pcb_qty else 0
                mat = int(material_qty) if material_qty else 0
                fix = int(fixing_qty) if fixing_qty else 0
                sold = int(solding_qty) if solding_qty else 0
                total = pcb + mat + fix + sold
                if total == 0:
                    continue

                # Split fault_name into category and subcategory (like import)
                if ' - ' in fault_name:
                    cat, sub = fault_name.split(' - ', 1)
                else:
                    cat = fault_name
                    sub = ''

                # Check existence on unique key (same as import)
                cursor.execute("""
                    SELECT id FROM rework_root_cause
                    WHERE record_date = ? AND line = ? AND model = ? 
                      AND fault_category = ? AND fault_subcategory = ?
                """, (record_date, line, model, cat.strip(), sub.strip()))
                existing = cursor.fetchone()
                if existing:
                    # Update existing
                    cursor.execute("""
                        UPDATE rework_root_cause
                        SET ship_no = ?, pcba_qty = ?, material_qty = ?, fixing_qty = ?, soldering_qty = ?,
                            total_qty = ?, remarks = ?, imported_at = GETDATE()
                        WHERE id = ?
                    """, (ship, pcb, mat, fix, sold, total,
                          f"Updated from manual entry on {datetime.now()}", existing[0]))
                else:
                    # Insert new
                    cursor.execute("""
                        INSERT INTO rework_root_cause 
                        (ship_no, record_date, line, model, fault_category, fault_subcategory,
                         pcba_qty, material_qty, fixing_qty, soldering_qty, total_qty, remarks, imported_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
                    """, (ship, record_date, line, model, cat.strip(), sub.strip(),
                          pcb, mat, fix, sold, total,
                          f"Imported from manual entry on {datetime.now()}"))
            conn.commit()
        return True

    @handle_db_errors
    def add_fault_category(self, name: str, station: str, created_by: int = None, icon: str = None, phone_type: str = 'Both') -> Optional[int]:
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COALESCE(MAX(display_order),0)+1 FROM fault_categories WHERE station_type=?", (station,))
            order = c.fetchone()[0]
            c.execute("""
                INSERT INTO fault_categories (category_name, station_type, display_order, created_by, icon, created_at, phone_type)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?, ?, ?, GETDATE(), ?)
            """, (name, station, order, created_by, icon, phone_type))
            row = c.fetchone()
            cat_id = row[0] if row else None
            if cat_id:
                self.log_audit('fault_categories', cat_id, 'CREATE', None, name, created_by)
                self.invalidate_fault_cache()
            return cat_id
        
    @handle_db_errors
    def add_fault(self, cat_id: int, name: str, code: str = None, severity: str = 'Minor', created_by: int = None) -> Optional[int]:
        if severity not in ['Critical','Major','Minor']:
            severity = 'Minor'
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COALESCE(MAX(display_order),0)+1 FROM faults WHERE category_id=?", (cat_id,))
            order = c.fetchone()[0]
            c.execute("""
                INSERT INTO faults (category_id, fault_name, fault_code, severity, display_order, created_by, created_at)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?, ?, ?, ?, GETDATE())
            """, (cat_id, name, code, severity, order, created_by))
            row = c.fetchone()
            fid = row[0] if row else None
            if fid:
                self.log_audit('faults', fid, 'CREATE', None, name, created_by)
                self.invalidate_fault_cache()
            return fid
    
    @handle_db_errors
    def update_fault(self, fid: int, name: str = None, code: str = None, severity: str = None, active: bool = None, updated_by: int = None) -> bool:
        updates, p = [], []
        if name is not None: updates.append("fault_name=?"); p.append(name)
        if code is not None: updates.append("fault_code=?"); p.append(code)
        if severity is not None and severity in ['Critical','Major','Minor']: updates.append("severity=?"); p.append(severity)
        if active is not None: updates.append("is_active=?"); p.append(1 if active else 0)
        if not updates: return False
        updates.append("updated_at=GETDATE()")
        p.append(fid)
        self.execute_query(f"UPDATE faults SET {', '.join(updates)} WHERE id=?", tuple(p))
        self.invalidate_fault_cache()
        return True

    @handle_db_errors
    def update_fault_category(self, cid: int, name: str = None, active: bool = None, updated_by: int = None) -> bool:
        updates, p = [], []
        if name is not None: updates.append("category_name=?"); p.append(name)
        if active is not None: updates.append("is_active=?"); p.append(1 if active else 0)
        if not updates: return False
        updates.append("updated_at=GETDATE()")
        p.append(cid)
        self.execute_query(f"UPDATE fault_categories SET {', '.join(updates)} WHERE id=?", tuple(p))
        self.invalidate_fault_cache()
        return True

    @handle_db_errors
    def delete_fault(self, fid: int, soft_delete: bool = True, deleted_by: int = None) -> bool:
        if soft_delete:
            self.execute_query("UPDATE faults SET is_active=0, updated_at=GETDATE() WHERE id=?", (fid,))
        else:
            f = self.execute_query("SELECT fault_name FROM faults WHERE id=?", (fid,), fetch_one=True)
            self.execute_query("DELETE FROM faults WHERE id=?", (fid,))
            if f: self.log_audit('faults', fid, 'DELETE', f['fault_name'], None, deleted_by)
        self.invalidate_fault_cache()
        return True

    @handle_db_errors
    def delete_fault_category(self, cid: int, soft_delete: bool = True) -> bool:
        if soft_delete:
            self.execute_query("UPDATE faults SET is_active=0 WHERE category_id=?", (cid,))
            self.execute_query("UPDATE fault_categories SET is_active=0 WHERE id=?", (cid,))
        else:
            self.execute_query("DELETE FROM fault_categories WHERE id=?", (cid,))
        self.invalidate_fault_cache()
        return True

    @handle_db_errors
    def get_fault_statistics(self) -> Dict:
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM fault_categories WHERE is_active=1"); cats = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM faults WHERE is_active=1"); faults = c.fetchone()[0]
            c.execute("SELECT severity, COUNT(*) FROM faults WHERE is_active=1 GROUP BY severity"); sev = {r[0]:r[1] for r in c.fetchall()}
            c.execute("SELECT fc.station_type, COUNT(f.id) FROM fault_categories fc LEFT JOIN faults f ON fc.id=f.category_id AND f.is_active=1 WHERE fc.is_active=1 GROUP BY fc.station_type"); st = {r[0]:r[1] for r in c.fetchall()}
            return {'total_categories':cats, 'total_faults':faults, 'faults_by_severity':sev, 'faults_by_station':st}

    # ========== REWORK API ==========
    @staticmethod
    def parse_faults_from_defects(text: str) -> Dict[str, int]:
        faults = {}
        if not text or text == "No defects": return faults
        for line in text.split('\n'):
            line = line.strip()
            if not line: continue
            m = re.match(r'^(.+?):\s*(\d+)\s*(?:pcs)?$', line, re.IGNORECASE)
            if m: faults[m.group(1).strip()] = int(m.group(2))
            else:
                m2 = re.match(r'^[•\-]\s*(.+?):\s*(\d+)\s*(?:pcs)?$', line, re.IGNORECASE)
                if m2: faults[m2.group(1).strip()] = int(m2.group(2))
        return faults

    @handle_db_errors
    def create_rework_tasks_from_inspection(self, insp_id: int) -> bool:
        insp = self.get_inspection_by_id(insp_id)
        if not insp: return False
        station = insp.get('inspection_type', '')
        if station in ['Rework','Final Test']: return True
        faults = self.parse_faults_from_defects(insp.get('defects',''))
        if not faults: return True
        data = [(insp_id, station, fault_name, qty) for fault_name, qty in faults.items()]
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(
                "INSERT INTO rework_tasks (inspection_id, source_station, fault_name, pending_quantity, created_at) VALUES (?,?,?,?,GETDATE())",
                data
            )
        return True

    @handle_db_errors
    def get_all_pending_rework_tasks(self) -> List[Dict]:
        return self.execute_query("""SELECT t.id, t.inspection_id, t.source_station, t.fault_name, t.pending_quantity,
               t.resolved_quantity, t.line, t.model, i.inspection_code FROM rework_tasks t LEFT JOIN inspections i ON t.inspection_id=i.id
               WHERE t.pending_quantity>0 ORDER BY t.created_at ASC""", fetch_all=True)

    @handle_db_errors
    def resolve_rework_quantity(self, task_id: int, qty: int, inspector_id: int, remarks: str = None) -> bool:
        with self.get_connection() as conn:
            c = conn.cursor()
            c.execute("""UPDATE rework_tasks SET pending_quantity = pending_quantity - ?, resolved_quantity = resolved_quantity + ?,
                updated_at = GETDATE(), status = CASE WHEN pending_quantity - ? <= 0 THEN 'Completed' ELSE 'InProgress' END
                WHERE id = ? AND pending_quantity >= ?""", (qty, qty, qty, task_id, qty))
            if c.rowcount == 0: return False
            c.execute("INSERT INTO rework_history (task_id, inspector_id, resolved_quantity, remarks, created_at) VALUES (?,?,?,?,GETDATE())", (task_id, inspector_id, qty, remarks))
        return True

    @handle_db_errors
    def get_rework_summary(self) -> Dict:
        rows = self.execute_query("SELECT source_station, line, COUNT(*) as task_count, SUM(pending_quantity) as total_pending FROM rework_tasks WHERE pending_quantity>0 GROUP BY source_station, line ORDER BY source_station, line", fetch_all=True)
        total = self.execute_query("SELECT SUM(pending_quantity) as grand_total FROM rework_tasks WHERE pending_quantity>0", fetch_one=True)
        return {'details': rows, 'grand_total': total['grand_total'] if total else 0}

    @handle_db_errors
    def get_rework_resolution_mapping(self) -> Dict[str, Dict]:
        rows = self.execute_query("SELECT fault_category, fault_subcategory, root_cause, responsible_dept, solution_plan, is_weak_point FROM rework_resolution_mapping", fetch_all=True)
        return {r['fault_category']:{'fault_subcategory': r['fault_subcategory'] or '',
                                      'root_cause':r['root_cause']or'',
                                      'responsible_dept':r['responsible_dept']or'',
                                      'solution_plan':r['solution_plan']or'',
                                      'is_weak_point':bool(r['is_weak_point'])} for r in rows}

    @handle_db_errors
    def save_root_cause_mapping(self, fault_category: str, fault_subcategory: str, data: dict) -> bool:
        model = data.get('model', '')
        ship_no = data.get('ship_no', '')
        record_date = data.get('record_date', '')
        with self.get_connection() as conn:
            cursor = conn.cursor()
            where_sql = "fault_category = ? AND fault_subcategory = ?"
            params_where = [fault_category, fault_subcategory]
            if model:
                where_sql += " AND (model = ? OR model IS NULL OR model = '')"
                params_where.append(model)
            if ship_no:
                where_sql += " AND (ship_no = ? OR ship_no IS NULL OR ship_no = '')"
                params_where.append(ship_no)
            if record_date:
                where_sql += " AND (record_date = ? OR record_date IS NULL)"
                params_where.append(record_date)
            cursor.execute(f"SELECT id FROM rework_resolution_mapping WHERE {where_sql}", tuple(params_where))
            exists = cursor.fetchone()
            if exists:
                update_sql = """
                    UPDATE rework_resolution_mapping
                    SET root_cause = ?, responsible_dept = ?, solution_plan = ?, model = ?, ship_no = ?, record_date = ?, updated_at = GETDATE()
                    WHERE fault_category = ? AND fault_subcategory = ?
                """
                update_params = [data['root_cause'], data['responsible_dept'], data['solution'], model, ship_no, record_date, fault_category, fault_subcategory]
                if model:
                    update_sql += " AND (model = ? OR model IS NULL OR model = '')"
                    update_params.append(model)
                if ship_no:
                    update_sql += " AND (ship_no = ? OR ship_no IS NULL OR ship_no = '')"
                    update_params.append(ship_no)
                if record_date:
                    update_sql += " AND (record_date = ? OR record_date IS NULL)"
                    update_params.append(record_date)
                cursor.execute(update_sql, tuple(update_params))
            else:
                cursor.execute("""
                    INSERT INTO rework_resolution_mapping (fault_category, fault_subcategory, root_cause, responsible_dept, solution_plan, model, ship_no, record_date, is_weak_point, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, GETDATE())
                """, (fault_category, fault_subcategory, data['root_cause'], data['responsible_dept'], data['solution'], model, ship_no, record_date))
            conn.commit()
            return True

    # ========== AUDIT, NOTIFICATIONS, UTILITIES ==========
    @handle_db_errors
    def log_audit(self, table: str, rid: int, action: str, old_val: str = None, new_val: str = None, changed_by: int = None, ip: str = None) -> bool:
        self.execute_query("INSERT INTO audit_log (table_name, record_id, action, old_value, new_value, changed_by, ip_address) VALUES (?,?,?,?,?,?,?)", (table, rid, action, old_val, new_val, changed_by, ip))
        return True

    @handle_db_errors
    def add_notification(self, user_id: int, title: str, msg: str, typ: str = 'info') -> bool:
        self.execute_query("INSERT INTO notifications (user_id, title, message, type) VALUES (?,?,?,?)", (user_id, title, msg, typ))
        return True

    @handle_db_errors
    def get_notifications(self, user_id: int, unread_only: bool = False) -> List[Dict]:
        q = "SELECT * FROM notifications WHERE user_id=?"
        p = [user_id]
        if unread_only: q += " AND is_read=0"
        q += " ORDER BY created_at DESC"
        return self.execute_query(q, tuple(p), fetch_all=True)

    @handle_db_errors
    def mark_notification_read(self, nid: int) -> bool:
        self.execute_query("UPDATE notifications SET is_read=1 WHERE id=?", (nid,))
        return True

    @handle_db_errors
    def check_connection(self) -> bool:
        try:
            with self.get_connection() as conn:
                conn.cursor().execute("SELECT 1")
            return True
        except: return False

    def close_all_connections(self):
        for conn in self._connection_pool:
            try: conn.close()
            except: pass
        self._connection_pool.clear()

    def close(self): self.close_all_connections()

if __name__ == "__main__":
    db = Database()
    print("Database initialized successfully with permission system.")
    db.close()