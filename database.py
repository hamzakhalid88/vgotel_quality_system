"""
Database Module for Quality Control System
Professional implementation with auto-migration and backward compatibility
"""

import pyodbc
import re
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import hashlib
import secrets
import uuid
import logging
from contextlib import contextmanager
from functools import wraps
from config import DB_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    pass


class ValidationError(Exception):
    pass


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
        self._connection_pool = []
        self._max_pool_size = 5
        self._column_cache = {}
        self._initialize_database()
        
    def _initialize_database(self) -> None:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                self._create_or_update_users_table(cursor)
                self._create_or_update_products_table(cursor)
                self._create_or_update_inspections_table(cursor)
                self._create_defects_table(cursor)
                self._create_audit_log_table(cursor)
                self._create_notifications_table(cursor)
                self._create_fault_tables(cursor)
                self._create_rework_tables(cursor)
                self._migrate_rework_tables(cursor)
                self._create_indexes(cursor)
                self._insert_default_users(cursor)
                # Optional: uncomment if you need default faults
                # self._insert_default_faults(cursor)
        except Exception as e:
            raise DatabaseError(f"Failed to initialize database: {str(e)}")

    def _build_connection_string(self) -> str:
        try:
            base_config = {
                'DRIVER': DB_CONFIG['driver'],
                'SERVER': DB_CONFIG['server'],
                'DATABASE': DB_CONFIG['database'],
                'Connection Timeout': '30',
                'Encrypt': 'no',
                'TrustServerCertificate': 'yes'
            }
            if DB_CONFIG.get('trusted_connection', False):
                base_config['Trusted_Connection'] = 'yes'
            else:
                base_config['UID'] = DB_CONFIG['username']
                base_config['PWD'] = DB_CONFIG['password']
            conn_str = ';'.join([f"{k}={v}" for k, v in base_config.items()])
            return conn_str
        except Exception as e:
            raise DatabaseError(f"Configuration error: {e}")

    @contextmanager
    def get_connection(self):
        conn = None
        try:
            if self._connection_pool:
                conn = self._connection_pool.pop()
                try:
                    conn.cursor().execute("SELECT 1")
                except Exception:
                    conn = None
            if not conn:
                conn = pyodbc.connect(self.connection_string, autocommit=False)
            yield conn
            conn.commit()
        except pyodbc.Error as e:
            if conn:
                conn.rollback()
            if "Cannot open database" in str(e):
                self._create_database()
                conn = pyodbc.connect(self.connection_string, autocommit=False)
                yield conn
                conn.commit()
            else:
                raise DatabaseError(f"Database operation failed: {str(e)}")
        except Exception as e:
            if conn:
                conn.rollback()
            raise DatabaseError(f"Unexpected error: {str(e)}")
        finally:
            if conn and len(self._connection_pool) < self._max_pool_size:
                self._connection_pool.append(conn)
            elif conn:
                conn.close()

    @handle_db_errors
    def execute_query(self, query: str, params: tuple = None,
                      fetch_one: bool = False, fetch_all: bool = False) -> Any:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            if fetch_one:
                result = cursor.fetchone()
                if result:
                    columns = [column[0] for column in cursor.description]
                    return dict(zip(columns, result))
                return None
            elif fetch_all:
                rows = cursor.fetchall()
                if rows:
                    columns = [column[0] for column in cursor.description]
                    return [dict(zip(columns, row)) for row in rows]
                return []
            else:
                return cursor.rowcount

    def _create_database(self) -> None:
        try:
            if DB_CONFIG.get('trusted_connection', False):
                master_conn_str = f"DRIVER={DB_CONFIG['driver']};SERVER={DB_CONFIG['server']};DATABASE=master;Trusted_Connection=yes;"
            else:
                master_conn_str = f"DRIVER={DB_CONFIG['driver']};SERVER={DB_CONFIG['server']};DATABASE=master;UID={DB_CONFIG['username']};PWD={DB_CONFIG['password']};"
            conn = pyodbc.connect(master_conn_str, autocommit=True)
            cursor = conn.cursor()
            cursor.execute(f"""
                IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = '{DB_CONFIG['database']}')
                BEGIN
                    CREATE DATABASE {DB_CONFIG['database']}
                END
            """)
            conn.close()
        except Exception as e:
            raise DatabaseError(f"Could not create database: {str(e)}")


    @staticmethod
    def _hash_password(password: str) -> str:
        salt = secrets.token_hex(32)
        iterations = 100000
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), iterations)
        return f"{iterations}:{salt}:{hash_obj.hex()}"

    @staticmethod
    def _verify_password(password: str, hashed: str) -> bool:
        try:
            iterations, salt, stored_hash = hashed.split(':')
            iterations = int(iterations)
            hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), iterations)
            return hash_obj.hex() == stored_hash
        except Exception:
            return False

    def _insert_default_faults(self, cursor) -> None:
        cursor.execute("SELECT COUNT(*) FROM fault_categories")
        if cursor.fetchone()[0] == 0:
            categories = [
                ('LCD', 'Semi Test', 1, '🖥️'),
                ('Receiver', 'Semi Test', 2, '📞'),
                ('Ringer', 'Semi Test', 3, '🔊'),
                ('MIC', 'Semi Test', 4, '🎤'),
                ('Camera', 'Semi Test', 5, '📷'),
                ('Torch', 'Semi Test', 6, '🔦'),
                ('Keypad', 'Semi Test', 7, '🔢'),
                ('Dead', 'Semi Test', 8, '⚰️'),
            ]
            for cat_name, station, order, icon in categories:
                # Insert category
                cursor.execute("""
                    INSERT INTO fault_categories (category_name, station_type, display_order, icon, created_at)
                    VALUES (?, ?, ?, ?, GETDATE())
                """, (cat_name, station, order, icon))
                # Get the new category ID
                cursor.execute("SELECT CAST(SCOPE_IDENTITY() AS INT)")
                row = cursor.fetchone()
                if row and row[0]:
                    cat_id = row[0]
                else:
                    # Fallback: query the category by name
                    cursor.execute("SELECT id FROM fault_categories WHERE category_name = ? AND station_type = ?", (cat_name, station))
                    cat_id = cursor.fetchone()[0]

                # Define faults for this category
                if cat_name == 'LCD':
                    faults = ['LCD BLACK', 'LCD WHITE', 'LCD SHADE', 'LCD SPOT', 'LCD LINE']
                elif cat_name == 'Receiver':
                    faults = ['RECEIVER NOT WORK', 'RECEIVER DISTORTION', 'RECEIVER SLOW']
                elif cat_name == 'Ringer':
                    faults = ['RINGER NOT WORK', 'RINGER DISTORTION', 'RINGER SLOW']
                elif cat_name == 'MIC':
                    faults = ['MIC NOT WORK']
                elif cat_name == 'Camera':
                    faults = ['CAMERA BLACK/WHITE', 'CAMERA ERROR', 'CAMERA SHADE/SPOT/LINE']
                elif cat_name == 'Torch':
                    faults = ['TORCH NOT WORK', 'ONE TORCH NOT WORK', 'TORCH AUTO WORK']
                elif cat_name == 'Keypad':
                    faults = ['KEYPAD NOT WORK', 'KEYPAD WORK SOMETIME', 'KEYPAD HARD']
                else:  # Dead
                    faults = ['DEAD']

                for i, fault_name in enumerate(faults):
                    cursor.execute("""
                        INSERT INTO faults (category_id, fault_name, display_order, created_at)
                        VALUES (?, ?, ?, GETDATE())
                    """, (cat_id, fault_name, i))
                    
    def _column_exists(self, cursor, table_name: str, column_name: str) -> bool:
        if table_name in self._column_cache:
            return column_name.lower() in self._column_cache[table_name]
        cursor.execute("SELECT COUNT(*) FROM syscolumns WHERE name = ? AND id = OBJECT_ID(?)", (column_name, table_name))
        exists = cursor.fetchone()[0] > 0
        if table_name not in self._column_cache:
            self._column_cache[table_name] = set()
        if exists:
            self._column_cache[table_name].add(column_name.lower())
        return exists

    def _add_column_safe(self, cursor, table_name: str, column_name: str, column_def: str) -> None:
        if not self._column_exists(cursor, table_name, column_name):
            try:
                cursor.execute(f"ALTER TABLE {table_name} ADD {column_name} {column_def}")
                logger.info(f"Added column '{column_name}' to {table_name}")
                if table_name not in self._column_cache:
                    self._column_cache[table_name] = set()
                self._column_cache[table_name].add(column_name.lower())
            except Exception as e:
                if "Column names in each table must be unique" in str(e):
                    if table_name not in self._column_cache:
                        self._column_cache[table_name] = set()
                    self._column_cache[table_name].add(column_name.lower())
                    logger.debug(f"Column '{column_name}' already exists in {table_name}")
                else:
                    logger.warning(f"Could not add column '{column_name}': {e}")

    def _migrate_rework_tables(self, cursor) -> None:
        self._add_column_safe(cursor, 'rework_tasks', 'line', 'NVARCHAR(50)')
        self._add_column_safe(cursor, 'rework_tasks', 'model', 'NVARCHAR(100)')
        try:
            cursor.execute("""
                SELECT * FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'rework_tasks' AND COLUMN_NAME = 'inspection_id'
            """)
            col_info = cursor.fetchone()
            if col_info and col_info[6] == 'NO':
                cursor.execute("ALTER TABLE rework_tasks ALTER COLUMN inspection_id INT NULL")
                logger.info("Made inspection_id nullable in rework_tasks")
        except Exception as e:
            logger.warning(f"Could not alter inspection_id: {e}")

    def _create_or_update_users_table(self, cursor) -> None:
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
            CREATE TABLE users (
                id INT IDENTITY(1,1) PRIMARY KEY,
                username NVARCHAR(50) UNIQUE NOT NULL,
                password_hash NVARCHAR(255) NOT NULL,
                full_name NVARCHAR(100) NOT NULL,
                email NVARCHAR(100),
                role NVARCHAR(50) DEFAULT 'viewer',
                is_active BIT DEFAULT 1,
                created_at DATETIME DEFAULT GETDATE(),
                last_login DATETIME,
                created_by INT
            )
        """)
        self._add_column_safe(cursor, 'users', 'phone', 'NVARCHAR(20)')
        self._add_column_safe(cursor, 'users', 'department', 'NVARCHAR(100)')
        self._add_column_safe(cursor, 'users', 'profile_image', 'NVARCHAR(500)')
        self._add_column_safe(cursor, 'users', 'updated_at', 'DATETIME')
        try:
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='CHK_Role' AND xtype='C')
                ALTER TABLE users ADD CONSTRAINT CHK_Role CHECK (role IN ('admin', 'inspector', 'viewer', 'manager'))
            """)
        except Exception:
            pass

    def _create_or_update_products_table(self, cursor) -> None:
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='products' AND xtype='U')
            CREATE TABLE products (
                id INT IDENTITY(1,1) PRIMARY KEY,
                product_code NVARCHAR(50) UNIQUE NOT NULL,
                product_name NVARCHAR(100) NOT NULL,
                category NVARCHAR(50),
                batch_number NVARCHAR(50) NOT NULL,
                production_date DATE NOT NULL,
                expiry_date DATE,
                specification NVARCHAR(MAX),
                quantity INT DEFAULT 0,
                min_quantity INT DEFAULT 0,
                supplier NVARCHAR(200),
                status NVARCHAR(20) DEFAULT 'Active',
                created_by INT,
                created_at DATETIME DEFAULT GETDATE(),
                updated_at DATETIME
            )
        """)
        self._add_column_safe(cursor, 'products', 'sub_category', 'NVARCHAR(50)')
        self._add_column_safe(cursor, 'products', 'weight', 'DECIMAL(10,2)')
        self._add_column_safe(cursor, 'products', 'unit', 'NVARCHAR(20)')
        self._add_column_safe(cursor, 'products', 'location', 'NVARCHAR(100)')
        self._add_column_safe(cursor, 'products', 'is_deleted', 'BIT DEFAULT 0')
        self._add_column_safe(cursor, 'products', 'updated_by', 'INT')
        self._add_column_safe(cursor, 'products', 'notes', 'NVARCHAR(MAX)')
        try:
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='CHK_ProductStatus' AND xtype='C')
                ALTER TABLE products ADD CONSTRAINT CHK_ProductStatus CHECK (status IN ('Active', 'Inactive', 'Discontinued'))
            """)
        except Exception:
            pass

    def _create_or_update_inspections_table(self, cursor) -> None:
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='inspections' AND xtype='U')
            CREATE TABLE inspections (
                id INT IDENTITY(1,1) PRIMARY KEY,
                inspection_code NVARCHAR(50) UNIQUE NOT NULL,
                product_id INT NOT NULL,
                inspector_id INT NOT NULL,
                inspection_date DATETIME DEFAULT GETDATE(),
                quantity_checked INT DEFAULT 0,
                accepted_quantity INT DEFAULT 0,
                rejected_quantity INT DEFAULT 0,
                quality_score DECIMAL(5,2),
                defects NVARCHAR(MAX),
                status NVARCHAR(20) DEFAULT 'Completed',
                remarks NVARCHAR(MAX),
                created_at DATETIME DEFAULT GETDATE()
            )
        """)
        self._add_column_safe(cursor, 'inspections', 'inspection_type', "NVARCHAR(50) DEFAULT 'Routine'")
        self._add_column_safe(cursor, 'inspections', 'sample_size', 'INT')
        self._add_column_safe(cursor, 'inspections', 'defect_types', 'NVARCHAR(500)')
        self._add_column_safe(cursor, 'inspections', 'attachments', 'NVARCHAR(1000)')
        self._add_column_safe(cursor, 'inspections', 'reviewed_by', 'INT')
        self._add_column_safe(cursor, 'inspections', 'reviewed_at', 'DATETIME')
        self._add_column_safe(cursor, 'inspections', 'updated_at', 'DATETIME')
        self._add_column_safe(cursor, 'inspections', 'line', 'NVARCHAR(50)')
        self._add_column_safe(cursor, 'inspections', 'floor', 'NVARCHAR(50)')
        try:
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='FK_inspections_products' AND xtype='F')
                ALTER TABLE inspections ADD CONSTRAINT FK_inspections_products FOREIGN KEY (product_id) REFERENCES products(id)
            """)
        except Exception:
            pass
        try:
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='FK_inspections_users' AND xtype='F')
                ALTER TABLE inspections ADD CONSTRAINT FK_inspections_users FOREIGN KEY (inspector_id) REFERENCES users(id)
            """)
        except Exception:
            pass

    def _create_defects_table(self, cursor) -> None:
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='defects' AND xtype='U')
            CREATE TABLE defects (
                id INT IDENTITY(1,1) PRIMARY KEY,
                inspection_id INT NOT NULL,
                defect_type NVARCHAR(100) NOT NULL,
                severity NVARCHAR(20) DEFAULT 'Minor',
                quantity INT DEFAULT 1,
                description NVARCHAR(MAX),
                location NVARCHAR(200),
                image_path NVARCHAR(500),
                created_at DATETIME DEFAULT GETDATE(),
                FOREIGN KEY (inspection_id) REFERENCES inspections(id) ON DELETE CASCADE
            )
        """)
        try:
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='CHK_Severity' AND xtype='C')
                ALTER TABLE defects ADD CONSTRAINT CHK_Severity CHECK (severity IN ('Critical', 'Major', 'Minor'))
            """)
        except Exception:
            pass

    def _create_audit_log_table(self, cursor) -> None:
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='audit_log' AND xtype='U')
            CREATE TABLE audit_log (
                id INT IDENTITY(1,1) PRIMARY KEY,
                table_name NVARCHAR(100),
                record_id INT,
                action NVARCHAR(50),
                old_value NVARCHAR(MAX),
                new_value NVARCHAR(MAX),
                changed_by INT,
                changed_at DATETIME DEFAULT GETDATE(),
                ip_address NVARCHAR(50)
            )
        """)

    def _create_notifications_table(self, cursor) -> None:
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='notifications' AND xtype='U')
            CREATE TABLE notifications (
                id INT IDENTITY(1,1) PRIMARY KEY,
                user_id INT NOT NULL,
                title NVARCHAR(200),
                message NVARCHAR(MAX),
                type NVARCHAR(50),
                is_read BIT DEFAULT 0,
                created_at DATETIME DEFAULT GETDATE(),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

    def _create_fault_tables(self, cursor) -> None:
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='fault_categories' AND xtype='U')
            CREATE TABLE fault_categories (
                id INT IDENTITY(1,1) PRIMARY KEY,
                category_name NVARCHAR(100) NOT NULL,
                station_type NVARCHAR(50) NOT NULL,
                display_order INT DEFAULT 0,
                is_active BIT DEFAULT 1,
                icon NVARCHAR(10),
                description NVARCHAR(500),
                created_at DATETIME DEFAULT GETDATE(),
                created_by INT,
                updated_at DATETIME,
                CONSTRAINT CHK_FaultStationType CHECK (station_type IN ('Semi Test', 'MMI Test', 'Appearance Test', 'Final Test'))
            )
        """)
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='faults' AND xtype='U')
            CREATE TABLE faults (
                id INT IDENTITY(1,1) PRIMARY KEY,
                category_id INT NOT NULL,
                fault_name NVARCHAR(200) NOT NULL,
                fault_code NVARCHAR(50),
                severity NVARCHAR(20) DEFAULT 'Minor',
                display_order INT DEFAULT 0,
                is_active BIT DEFAULT 1,
                created_at DATETIME DEFAULT GETDATE(),
                created_by INT,
                updated_at DATETIME,
                FOREIGN KEY (category_id) REFERENCES fault_categories(id) ON DELETE CASCADE,
                CONSTRAINT CHK_FaultSeverity CHECK (severity IN ('Critical', 'Major', 'Minor'))
            )
        """)

    def _create_rework_tables(self, cursor) -> None:
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='rework_tasks' AND xtype='U')
            CREATE TABLE rework_tasks (
                id INT IDENTITY(1,1) PRIMARY KEY,
                inspection_id INT NULL,
                source_station NVARCHAR(50) NOT NULL,
                fault_name NVARCHAR(200) NOT NULL,
                pending_quantity INT NOT NULL,
                resolved_quantity INT DEFAULT 0,
                status NVARCHAR(20) DEFAULT 'Pending',
                line NVARCHAR(50) NULL,
                model NVARCHAR(100) NULL,
                created_at DATETIME DEFAULT GETDATE(),
                updated_at DATETIME
            )
        """)
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='rework_root_cause' AND xtype='U')
            CREATE TABLE rework_root_cause (
                id INT IDENTITY(1,1) PRIMARY KEY,
                ship_no NVARCHAR(50),
                record_date DATE,
                line NVARCHAR(50),
                model NVARCHAR(100),
                fault_category NVARCHAR(100),
                fault_subcategory NVARCHAR(200),
                pcba_qty INT DEFAULT 0,
                material_qty INT DEFAULT 0,
                fixing_qty INT DEFAULT 0,
                soldering_qty INT DEFAULT 0,
                total_qty INT DEFAULT 0,
                remarks NVARCHAR(MAX),
                imported_at DATETIME DEFAULT GETDATE()
            )
        """)
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='rework_history' AND xtype='U')
            CREATE TABLE rework_history (
                id INT IDENTITY(1,1) PRIMARY KEY,
                task_id INT NOT NULL,
                inspector_id INT NOT NULL,
                resolved_quantity INT NOT NULL,
                root_cause_stage NVARCHAR(50) NULL,
                remarks NVARCHAR(MAX),
                created_at DATETIME DEFAULT GETDATE(),
                FOREIGN KEY (task_id) REFERENCES rework_tasks(id)
            )
        """)
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='rework_completed' AND xtype='U')
            CREATE TABLE rework_completed (
                id INT IDENTITY(1,1) PRIMARY KEY,
                line NVARCHAR(50) NOT NULL,
                model NVARCHAR(100) NOT NULL,
                fault_name NVARCHAR(200) NOT NULL,
                source_station NVARCHAR(50) NOT NULL,
                resolved_qty INT NOT NULL,
                resolution_date DATE NOT NULL,
                remarks NVARCHAR(MAX),
                imported_at DATETIME DEFAULT GETDATE()
            )
        """)
        # ========== NEW TABLE: rework_resolution_mapping ==========
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='rework_resolution_mapping' AND xtype='U')
            CREATE TABLE rework_resolution_mapping (
                id INT IDENTITY(1,1) PRIMARY KEY,
                fault_category NVARCHAR(100) NOT NULL,
                root_cause NVARCHAR(500),
                responsible_dept NVARCHAR(100),
                solution_plan NVARCHAR(500),
                is_weak_point BIT DEFAULT 0,
                created_at DATETIME DEFAULT GETDATE(),
                updated_at DATETIME
            )
        """)
        # Insert some default mapping data if table is empty
        cursor.execute("SELECT COUNT(*) FROM rework_resolution_mapping")
        if cursor.fetchone()[0] == 0:
            default_mappings = [
                ('LCD', 'Poor handling / ESD damage', 'Production', 'Add antistatic mats, retrain operators', 1),
                ('Soldering', 'Old soldering iron tips / low temperature', 'Maintenance', 'Replace tips every 2 weeks, daily temp check', 1),
                ('MIC', 'Supplier quality issue', 'Procurement', 'Implement incoming inspection for MIC lots', 0),
                ('Camera', 'Dust on lens during assembly', 'Production', 'Clean workstations daily, use dust covers', 0),
                ('Keypad', 'Wrong material batch', 'QA', 'Supplier audit + lot sampling before use', 1),
                ('Receiver', 'Poor connector alignment', 'Production', 'Add alignment jig', 0),
                ('Ringer', 'Incorrect component value', 'Engineering', 'Update BOM and verify', 0),
                ('Torch', 'LED soldering cold joint', 'Production', 'Reflow profile adjustment', 0),
                ('Dead', 'Power IC failure', 'Engineering', 'Change IC supplier, add test', 1),
            ]
            for cat, cause, dept, sol, weak in default_mappings:
                cursor.execute("""
                    INSERT INTO rework_resolution_mapping 
                    (fault_category, root_cause, responsible_dept, solution_plan, is_weak_point, created_at)
                    VALUES (?, ?, ?, ?, ?, GETDATE())
                """, (cat, cause, dept, sol, weak))
        # ============================================================
        
        self._add_column_safe(cursor, 'rework_history', 'root_cause_stage', 'NVARCHAR(50)')
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='rework_details' AND xtype='U')
            CREATE TABLE rework_details (
                id INT IDENTITY(1,1) PRIMARY KEY,
                inspection_id INT NOT NULL,
                fault_name NVARCHAR(200) NOT NULL,
                pcb NVARCHAR(255),
                material NVARCHAR(255),
                fixing NVARCHAR(255),
                solding NVARCHAR(255),
                created_at DATETIME DEFAULT GETDATE(),
                FOREIGN KEY (inspection_id) REFERENCES inspections(id) ON DELETE CASCADE
            )
        """)

    def _create_indexes(self, cursor) -> None:
        index_queries = [
            "CREATE INDEX idx_users_username ON users(username)",
            "CREATE INDEX idx_users_role ON users(role)",
            "CREATE INDEX idx_products_code ON products(product_code)",
            "CREATE INDEX idx_products_status ON products(status)",
            "CREATE INDEX idx_inspections_date ON inspections(inspection_date)",
            "CREATE INDEX idx_inspections_product ON inspections(product_id)",
            "CREATE INDEX idx_inspections_status ON inspections(status)",
            "CREATE INDEX idx_defects_inspection ON defects(inspection_id)",
            "CREATE INDEX idx_faults_category ON faults(category_id)",
            "CREATE INDEX idx_faults_active ON faults(is_active)",
            "CREATE INDEX idx_fault_categories_station ON fault_categories(station_type)",
            "CREATE INDEX idx_rework_tasks_inspection ON rework_tasks(inspection_id)",
            "CREATE INDEX idx_rework_tasks_status ON rework_tasks(status)",
            "CREATE INDEX idx_rework_tasks_line_model ON rework_tasks(line, model)",
            "CREATE INDEX idx_rework_history_task ON rework_history(task_id)",
            "CREATE INDEX idx_rework_details_inspection ON rework_details(inspection_id)",
            "CREATE INDEX idx_rework_resolution_mapping_category ON rework_resolution_mapping(fault_category)"
        ]
        for idx_sql in index_queries:
            try:
                idx_name = idx_sql.split('ON')[0].split('INDEX')[1].strip()
                cursor.execute(f"""
                    IF NOT EXISTS (SELECT * FROM sysindexes WHERE name = '{idx_name}')
                    BEGIN {idx_sql} END
                """)
            except Exception:
                try:
                    cursor.execute(idx_sql)
                except Exception:
                    pass

        # Create indexes for rework_completed table (separately)
        try:
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysindexes WHERE name = 'idx_rework_completed_line_model')
                CREATE INDEX idx_rework_completed_line_model ON rework_completed(line, model)
            """)
        except Exception:
            pass
        try:
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysindexes WHERE name = 'idx_rework_completed_date')
                CREATE INDEX idx_rework_completed_date ON rework_completed(resolution_date)
            """)
        except Exception:
            pass

    def _insert_default_users(self, cursor) -> None:
        users = [
            ('admin', 'admin123', 'System Administrator', 'admin@quality.com', 'admin', 'IT Department'),
            ('inspector', 'inspector123', 'Quality Inspector', 'inspector@quality.com', 'inspector', 'Quality Assurance'),
            ('manager', 'manager123', 'Quality Manager', 'manager@quality.com', 'manager', 'Quality Management'),
            ('viewer', 'viewer123', 'Quality Viewer', 'viewer@quality.com', 'viewer', 'Quality Control')
        ]
        for username, password, full_name, email, role, department in users:
            cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
            existing = cursor.fetchone()
            pwd_hash = self._hash_password(password)
            if existing:
                cursor.execute("""
                    UPDATE users SET password_hash=?, full_name=?, email=?, role=?, department=?, is_active=1
                    WHERE username=?
                """, (pwd_hash, full_name, email, role, department, username))
            else:
                cursor.execute("""
                    INSERT INTO users (username, password_hash, full_name, email, role, department, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                """, (username, pwd_hash, full_name, email, role, department))

    def _insert_default_faults(self, cursor) -> None:
        cursor.execute("SELECT COUNT(*) FROM fault_categories")
        if cursor.fetchone()[0] == 0:
            categories = [
                ('LCD', 'Semi Test', 1, '🖥️'),
                ('Receiver', 'Semi Test', 2, '📞'),
                ('Ringer', 'Semi Test', 3, '🔊'),
                ('MIC', 'Semi Test', 4, '🎤'),
                ('Camera', 'Semi Test', 5, '📷'),
                ('Torch', 'Semi Test', 6, '🔦'),
                ('Keypad', 'Semi Test', 7, '🔢'),
                ('Dead', 'Semi Test', 8, '⚰️'),
            ]
            for cat_name, station, order, icon in categories:
                # Insert the category
                cursor.execute("""
                    INSERT INTO fault_categories (category_name, station_type, display_order, icon, created_at)
                    VALUES (?, ?, ?, ?, GETDATE())
                """, (cat_name, station, order, icon))
                # Get the generated identity
                cursor.execute("SELECT SCOPE_IDENTITY()")
                cat_id = cursor.fetchone()[0]

                # Insert faults for this category
                if cat_name == 'LCD':
                    faults = ['LCD BLACK', 'LCD WHITE', 'LCD SHADE', 'LCD SPOT', 'LCD LINE']
                elif cat_name == 'Receiver':
                    faults = ['RECEIVER NOT WORK', 'RECEIVER DISTORTION', 'RECEIVER SLOW']
                elif cat_name == 'Ringer':
                    faults = ['RINGER NOT WORK', 'RINGER DISTORTION', 'RINGER SLOW']
                elif cat_name == 'MIC':
                    faults = ['MIC NOT WORK']
                elif cat_name == 'Camera':
                    faults = ['CAMERA BLACK/WHITE', 'CAMERA ERROR', 'CAMERA SHADE/SPOT/LINE']
                elif cat_name == 'Torch':
                    faults = ['TORCH NOT WORK', 'ONE TORCH NOT WORK', 'TORCH AUTO WORK']
                elif cat_name == 'Keypad':
                    faults = ['KEYPAD NOT WORK', 'KEYPAD WORK SOMETIME', 'KEYPAD HARD']
                else:
                    faults = ['DEAD']

                for i, ft in enumerate(faults):
                    cursor.execute("""
                        INSERT INTO faults (category_id, fault_name, display_order, created_at)
                        VALUES (?, ?, ?, GETDATE())
                    """, (cat_id, ft, i))

    # ========== NEW METHOD: get_rework_resolution_mapping ==========
    @handle_db_errors
    def get_rework_resolution_mapping(self) -> Dict[str, Dict]:
        """
        Fetch all resolution mappings from rework_resolution_mapping table.
        Returns a dictionary: fault_category -> {root_cause, responsible_dept, solution_plan, is_weak_point}
        """
        rows = self.execute_query(
            "SELECT fault_category, root_cause, responsible_dept, solution_plan, is_weak_point FROM rework_resolution_mapping",
            fetch_all=True
        )
        mapping = {}
        for row in rows:
            mapping[row['fault_category']] = {
                'root_cause': row['root_cause'] or '',
                'responsible_dept': row['responsible_dept'] or '',
                'solution_plan': row['solution_plan'] or '',
                'is_weak_point': bool(row['is_weak_point'])
            }
        return mapping
    # ================================================================

    # ========== FAULT MANAGEMENT API ==========
    @handle_db_errors
    def get_fault_categories(self, station_type: str) -> List[Dict]:
        query = "SELECT id, category_name, display_order, icon, description, is_active FROM fault_categories WHERE station_type = ? AND is_active = 1 ORDER BY display_order"
        return self.execute_query(query, (station_type,), fetch_all=True)

    @handle_db_errors
    def get_faults_by_category(self, category_id: int) -> List[Dict]:
        query = "SELECT id, fault_name, fault_code, severity, display_order, is_active FROM faults WHERE category_id = ? AND is_active = 1 ORDER BY display_order"
        return self.execute_query(query, (category_id,), fetch_all=True)

    @handle_db_errors
    def get_all_faults_by_station(self, station_type: str) -> Dict:
        categories = self.get_fault_categories(station_type)
        result = {}
        for cat in categories:
            faults = self.get_faults_by_category(cat['id'])
            result[cat['category_name']] = {'category_id': cat['id'], 'faults': faults}
        return result

    @handle_db_errors
    def add_fault_category(self, category_name: str, station_type: str, created_by: int = None, icon: str = None) -> Optional[int]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COALESCE(MAX(display_order),0)+1 FROM fault_categories WHERE station_type = ?", (station_type,))
            max_order = cursor.fetchone()[0]
            cursor.execute("INSERT INTO fault_categories (category_name, station_type, display_order, created_by, icon, created_at) VALUES (?,?,?,?,?,GETDATE()) SELECT SCOPE_IDENTITY()", (category_name, station_type, max_order, created_by, icon))
            cat_id = cursor.fetchone()[0]
            self.log_audit('fault_categories', cat_id, 'CREATE', None, category_name, created_by)
            return cat_id

    @handle_db_errors
    def add_fault(self, category_id: int, fault_name: str, fault_code: str = None, severity: str = 'Minor', created_by: int = None) -> Optional[int]:
        if severity not in ['Critical','Major','Minor']:
            severity = 'Minor'
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COALESCE(MAX(display_order),0)+1 FROM faults WHERE category_id = ?", (category_id,))
            max_order = cursor.fetchone()[0]
            cursor.execute("INSERT INTO faults (category_id, fault_name, fault_code, severity, display_order, created_by, created_at) VALUES (?,?,?,?,?,?,GETDATE()) SELECT SCOPE_IDENTITY()", (category_id, fault_name, fault_code, severity, max_order, created_by))
            fault_id = cursor.fetchone()[0]
            self.log_audit('faults', fault_id, 'CREATE', None, fault_name, created_by)
            return fault_id

    @handle_db_errors
    def update_fault(self, fault_id: int, fault_name: str = None, fault_code: str = None, severity: str = None, is_active: bool = None, updated_by: int = None) -> bool:
        updates, params = [], []
        if fault_name is not None:
            updates.append("fault_name = ?"); params.append(fault_name)
        if fault_code is not None:
            updates.append("fault_code = ?"); params.append(fault_code)
        if severity is not None and severity in ['Critical','Major','Minor']:
            updates.append("severity = ?"); params.append(severity)
        if is_active is not None:
            updates.append("is_active = ?"); params.append(1 if is_active else 0)
        if not updates:
            return False
        updates.append("updated_at = GETDATE()")
        params.append(fault_id)
        self.execute_query(f"UPDATE faults SET {', '.join(updates)} WHERE id = ?", tuple(params))
        return True

    @handle_db_errors
    def update_fault_category(self, category_id: int, category_name: str = None, is_active: bool = None, updated_by: int = None) -> bool:
        updates, params = [], []
        if category_name is not None:
            updates.append("category_name = ?"); params.append(category_name)
        if is_active is not None:
            updates.append("is_active = ?"); params.append(1 if is_active else 0)
        if not updates:
            return False
        updates.append("updated_at = GETDATE()")
        params.append(category_id)
        self.execute_query(f"UPDATE fault_categories SET {', '.join(updates)} WHERE id = ?", tuple(params))
        return True

    @handle_db_errors
    def delete_fault(self, fault_id: int, soft_delete: bool = True, deleted_by: int = None) -> bool:
        if soft_delete:
            self.execute_query("UPDATE faults SET is_active = 0, updated_at = GETDATE() WHERE id = ?", (fault_id,))
        else:
            fault = self.execute_query("SELECT fault_name FROM faults WHERE id = ?", (fault_id,), fetch_one=True)
            self.execute_query("DELETE FROM faults WHERE id = ?", (fault_id,))
            if fault:
                self.log_audit('faults', fault_id, 'DELETE', fault['fault_name'], None, deleted_by)
        return True

    @handle_db_errors
    def delete_fault_category(self, category_id: int, soft_delete: bool = True) -> bool:
        if soft_delete:
            self.execute_query("UPDATE faults SET is_active = 0 WHERE category_id = ?", (category_id,))
            self.execute_query("UPDATE fault_categories SET is_active = 0 WHERE id = ?", (category_id,))
        else:
            self.execute_query("DELETE FROM fault_categories WHERE id = ?", (category_id,))
        return True

    @handle_db_errors
    def search_faults(self, search_term: str, station_type: str = None) -> List[Dict]:
        query = """
            SELECT 
                f.id,
                f.fault_name,
                f.fault_code,
                f.severity,
                f.display_order,
                f.is_active,
                c.category_name,
                c.station_type
            FROM faults f
            INNER JOIN fault_categories c
                ON f.category_id = c.id
            WHERE f.is_active = 1
            AND (
                    f.fault_name LIKE ?
                    OR c.category_name LIKE ?
                    OR ISNULL(f.fault_code, '') LIKE ?
                )
        """
        params = [
            f"%{search_term}%",
            f"%{search_term}%",
            f"%{search_term}%"
        ]
        if station_type:
            query += " AND c.station_type = ? "
            params.append(station_type)
        query += """
            ORDER BY 
                c.display_order,
                f.display_order,
                f.fault_name
        """
        return self.execute_query(query, tuple(params), fetch_all=True)

    @handle_db_errors
    def get_fault_statistics(self) -> Dict:
        stats = {}
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM fault_categories WHERE is_active=1")
            stats['total_categories'] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM faults WHERE is_active=1")
            stats['total_faults'] = cursor.fetchone()[0]
            cursor.execute("SELECT severity, COUNT(*) FROM faults WHERE is_active=1 GROUP BY severity")
            stats['faults_by_severity'] = {r[0]: r[1] for r in cursor.fetchall()}
            cursor.execute("SELECT fc.station_type, COUNT(f.id) FROM fault_categories fc LEFT JOIN faults f ON fc.id=f.category_id AND f.is_active=1 WHERE fc.is_active=1 GROUP BY fc.station_type")
            stats['faults_by_station'] = {r[0]: r[1] for r in cursor.fetchall()}
        return stats

    # ========== REWORK MANAGEMENT API ==========
    @staticmethod
    def parse_faults_from_defects(defects_text: str) -> Dict[str, int]:
        faults = {}
        if not defects_text or defects_text == "No defects":
            return faults
        for line in defects_text.split('\n'):
            line = line.strip()
            if not line:
                continue
            m = re.match(r'^(.+?):\s*(\d+)\s*(?:pcs)?$', line, re.IGNORECASE)
            if m:
                faults[m.group(1).strip()] = int(m.group(2))
            else:
                m2 = re.match(r'^[•\-]\s*(.+?):\s*(\d+)\s*(?:pcs)?$', line, re.IGNORECASE)
                if m2:
                    faults[m2.group(1).strip()] = int(m2.group(2))
        return faults

    @handle_db_errors
    def create_rework_tasks_from_inspection(self, inspection_id: int) -> bool:
        insp = self.get_inspection_by_id(inspection_id)
        if not insp:
            return False
        station = insp.get('inspection_type', '')
        if station in ['Rework', 'Final Test']:
            return True
        faults = self.parse_faults_from_defects(insp.get('defects', ''))
        if not faults:
            return True
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for fault_name, qty in faults.items():
                cursor.execute("INSERT INTO rework_tasks (inspection_id, source_station, fault_name, pending_quantity, created_at) VALUES (?,?,?,?,GETDATE())", (inspection_id, station, fault_name, qty))
            conn.commit()
        return True

    @handle_db_errors
    def get_pending_rework_task(self, line: str, model: str, fault_name: str, source_station: str) -> Optional[Dict]:
        query = """
            SELECT id, pending_quantity 
            FROM rework_tasks 
            WHERE line = ? AND model = ? AND fault_name = ? AND source_station = ? AND status != 'Completed'
        """
        return self.execute_query(query, (line, model, fault_name, source_station), fetch_one=True)

    @handle_db_errors
    def get_rework_tasks_for_inspection(self, inspection_id: int) -> List[Dict]:
        return self.execute_query("SELECT id, fault_name, pending_quantity, resolved_quantity FROM rework_tasks WHERE inspection_id = ? AND pending_quantity > 0 ORDER BY fault_name", (inspection_id,), fetch_all=True)

    @handle_db_errors
    def get_all_pending_rework_tasks(self) -> List[Dict]:
        return self.execute_query("""
            SELECT t.id, t.inspection_id, t.source_station, t.fault_name, t.pending_quantity, t.resolved_quantity, t.line, t.model, i.inspection_code
            FROM rework_tasks t LEFT JOIN inspections i ON t.inspection_id = i.id
            WHERE t.pending_quantity > 0 ORDER BY t.created_at ASC
        """, fetch_all=True)

    @handle_db_errors
    def update_pending_quantity(self, task_id: int, new_pending_qty: int) -> bool:
        self.execute_query("UPDATE rework_tasks SET pending_quantity = ?, updated_at = GETDATE() WHERE id = ?", (new_pending_qty, task_id))
        return True

    @handle_db_errors
    def add_pending_rework_task(self, line: str, model: str, fault_name: str, source_station: str, quantity: int) -> int:
        insert_sql = """
            INSERT INTO rework_tasks (line, model, fault_name, source_station, pending_quantity, created_at)
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, GETDATE())
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(insert_sql, (line, model, fault_name, source_station, quantity))
            row = cursor.fetchone()
            if row and row[0] is not None:
                return row[0]
            cursor.execute("SELECT SCOPE_IDENTITY()")
            row2 = cursor.fetchone()
            if row2 and row2[0] is not None:
                return int(row2[0])
            raise DatabaseError("Failed to retrieve new task ID")

    @handle_db_errors
    def resolve_rework_with_diagnostic(self, task_id: int, resolved_qty: int, inspector_id: int, root_cause_stage: str, remarks: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE rework_tasks
                SET pending_quantity = pending_quantity - ?,
                    resolved_quantity = resolved_quantity + ?,
                    updated_at = GETDATE(),
                    status = CASE WHEN pending_quantity - ? <= 0 THEN 'Completed' ELSE 'InProgress' END
                WHERE id = ? AND pending_quantity >= ?
            """, (resolved_qty, resolved_qty, resolved_qty, task_id, resolved_qty))
            if cursor.rowcount == 0:
                return False
            cursor.execute("INSERT INTO rework_history (task_id, inspector_id, resolved_quantity, root_cause_stage, remarks, created_at) VALUES (?,?,?,?,?,GETDATE())", (task_id, inspector_id, resolved_qty, root_cause_stage, remarks))
            conn.commit()
        return True

    @handle_db_errors
    def resolve_rework_quantity(self, task_id: int, resolved_qty: int, inspector_id: int, remarks: str = None) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE rework_tasks
                SET pending_quantity = pending_quantity - ?,
                    resolved_quantity = resolved_quantity + ?,
                    updated_at = GETDATE(),
                    status = CASE WHEN pending_quantity - ? <= 0 THEN 'Completed' ELSE 'InProgress' END
                WHERE id = ? AND pending_quantity >= ?
            """, (resolved_qty, resolved_qty, resolved_qty, task_id, resolved_qty))
            if cursor.rowcount == 0:
                return False
            cursor.execute("INSERT INTO rework_history (task_id, inspector_id, resolved_quantity, remarks, created_at) VALUES (?,?,?,?,GETDATE())", (task_id, inspector_id, resolved_qty, remarks))
            conn.commit()
        return True

    @handle_db_errors
    def get_rework_summary(self) -> Dict:
        """Return summary of pending rework tasks by source_station and line."""
        query = """
            SELECT 
                source_station,
                line,
                COUNT(*) as task_count,
                SUM(pending_quantity) as total_pending
            FROM rework_tasks
            WHERE pending_quantity > 0
            GROUP BY source_station, line
            ORDER BY source_station, line
        """
        rows = self.execute_query(query, fetch_all=True)
        total_query = "SELECT SUM(pending_quantity) as grand_total FROM rework_tasks WHERE pending_quantity > 0"
        total_row = self.execute_query(total_query, fetch_one=True)
        grand_total = total_row['grand_total'] if total_row else 0
        return {
            'details': rows,
            'grand_total': grand_total
        }

    # ========== DIRECT REWORK DETAILS ==========
    @handle_db_errors
    def save_rework_entries(self, inspection_id: int, entries: List[Tuple[str,str,str,str,str]]) -> bool:
        if not entries:
            return True
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for fault, pcb, material, fixing, solding in entries:
                cursor.execute("INSERT INTO rework_details (inspection_id, fault_name, pcb, material, fixing, solding, created_at) VALUES (?,?,?,?,?,?,GETDATE())", (inspection_id, fault, pcb, material, fixing, solding))
            conn.commit()
        return True

    @handle_db_errors
    def get_rework_details(self, inspection_id: int) -> List[Dict]:
        return self.execute_query("SELECT id, fault_name, pcb, material, fixing, solding, created_at FROM rework_details WHERE inspection_id = ? ORDER BY id", (inspection_id,), fetch_all=True)

    # ========== EXISTING PUBLIC API ==========
    @handle_db_errors
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        query = "SELECT id, username, password_hash, full_name, email, phone, role, department, is_active, last_login FROM users WHERE username = ? AND is_active = 1"
        user = self.execute_query(query, (username,), fetch_one=True)
        if user and self._verify_password(password, user['password_hash']):
            user.pop('password_hash', None)
            return user
        return None

    @handle_db_errors
    def update_last_login(self, user_id: int) -> bool:
        self.execute_query("UPDATE users SET last_login = GETDATE() WHERE id = ?", (user_id,))
        return True

    @handle_db_errors
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        return self.execute_query("SELECT id, username, full_name, email, phone, role, department, is_active, created_at, last_login FROM users WHERE id = ?", (user_id,), fetch_one=True)

    @handle_db_errors
    def get_all_users(self, active_only: bool = False) -> List[Dict]:
        query = "SELECT id, username, full_name, email, phone, role, department, is_active, created_at, last_login FROM users"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY full_name"
        return self.execute_query(query, fetch_all=True)

    @handle_db_errors
    def create_user(self, user_data: Dict) -> Optional[int]:
        pwd_hash = self._hash_password(user_data['password'])
        query = "INSERT INTO users (username, password_hash, full_name, email, phone, role, department, created_by) VALUES (?,?,?,?,?,?,?,?) SELECT SCOPE_IDENTITY()"
        params = (user_data['username'], pwd_hash, user_data['full_name'], user_data.get('email'), user_data.get('phone'), user_data.get('role','viewer'), user_data.get('department'), user_data.get('created_by',1))
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()[0]

    @handle_db_errors
    def update_user(self, user_id: int, user_data: Dict) -> bool:
        updates, params = [], []
        allowed = ['full_name','email','phone','role','department','is_active']
        for f in allowed:
            if f in user_data:
                updates.append(f"{f} = ?")
                params.append(user_data[f])
        if not updates:
            return False
        params.append(user_id)
        self.execute_query(f"UPDATE users SET {', '.join(updates)}, updated_at = GETDATE() WHERE id = ?", tuple(params))
        return True

    @handle_db_errors
    def get_all_products(self, status: str = None, category: str = None) -> List[Dict]:
        query = "SELECT id, product_code, product_name, category, batch_number, production_date, expiry_date, quantity, min_quantity, location, supplier, status, created_at FROM products WHERE (is_deleted=0 OR is_deleted IS NULL)"
        params = []
        if status:
            query += " AND status = ?"; params.append(status)
        if category:
            query += " AND category = ?"; params.append(category)
        query += " ORDER BY created_at DESC"
        return self.execute_query(query, tuple(params), fetch_all=True)

    @handle_db_errors
    def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        return self.execute_query("SELECT * FROM products WHERE id = ? AND (is_deleted=0 OR is_deleted IS NULL)", (product_id,), fetch_one=True)

    @handle_db_errors
    def get_product_by_code(self, product_code: str) -> Optional[Dict]:
        return self.execute_query("SELECT * FROM products WHERE product_code = ? AND (is_deleted=0 OR is_deleted IS NULL)", (product_code,), fetch_one=True)

    @handle_db_errors
    def add_product(self, product_data: Dict) -> Optional[int]:
        query = """
            INSERT INTO products (product_code, product_name, category, batch_number, production_date, expiry_date, specification, quantity, min_quantity, location, supplier, unit, created_by)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) SELECT SCOPE_IDENTITY()
        """
        params = (product_data['product_code'], product_data['product_name'], product_data.get('category'), product_data['batch_number'], product_data['production_date'], product_data.get('expiry_date'), product_data.get('specification'), product_data.get('quantity',0), product_data.get('min_quantity',0), product_data.get('location'), product_data.get('supplier'), product_data.get('unit','pcs'), product_data.get('created_by',1))
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()[0]

    @handle_db_errors
    def update_product(self, product_id: int, product_data: Dict) -> bool:
        updates, params = [], []
        allowed = ['product_name','category','sub_category','specification','quantity','min_quantity','location','supplier','unit','status']
        for f in allowed:
            if f in product_data:
                updates.append(f"{f} = ?"); params.append(product_data[f])
        if not updates:
            return False
        params.append(product_id)
        self.execute_query(f"UPDATE products SET {', '.join(updates)}, updated_at = GETDATE() WHERE id = ?", tuple(params))
        return True

    @handle_db_errors
    def delete_product(self, product_id: int, soft_delete: bool = True) -> bool:
        if soft_delete:
            self.execute_query("UPDATE products SET is_deleted = 1, status = 'Inactive' WHERE id = ?", (product_id,))
        else:
            self.execute_query("DELETE FROM products WHERE id = ?", (product_id,))
        return True

    @handle_db_errors
    def add_inspection(self, inspection_data: Dict) -> Optional[int]:
        qty = inspection_data.get('quantity_checked',0)
        accepted = inspection_data.get('accepted_quantity',0)
        rejected = qty - accepted
        quality = (accepted / qty * 100) if qty > 0 else 0
        code = f"QC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8].upper()}"
        query = """
            INSERT INTO inspections (inspection_code, product_id, inspector_id, inspection_type, quantity_checked, accepted_quantity, rejected_quantity, quality_score, defects, remarks, status, line, floor)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?) SELECT SCOPE_IDENTITY()
        """
        params = (code, inspection_data.get('product_id'), inspection_data['inspector_id'], inspection_data.get('inspection_type','Routine'), qty, accepted, rejected, quality, inspection_data.get('defects'), inspection_data.get('remarks'), 'Completed', inspection_data.get('line'), inspection_data.get('floor'))
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            insp_id = cursor.fetchone()[0]
            for defect in inspection_data.get('defect_list', []):
                self._add_defect(insp_id, defect)
            return insp_id

    def _add_defect(self, inspection_id: int, defect_data: Dict) -> Optional[int]:
        query = "INSERT INTO defects (inspection_id, defect_type, severity, quantity, description, location) VALUES (?,?,?,?,?,?) SELECT SCOPE_IDENTITY()"
        params = (inspection_id, defect_data['defect_type'], defect_data.get('severity','Minor'), defect_data.get('quantity',1), defect_data.get('description'), defect_data.get('location'))
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()[0]

    @handle_db_errors
    def get_all_inspections(self, filters: Dict = None) -> List[Dict]:
        query = """
            SELECT i.id, i.inspection_code, i.inspection_type, p.product_name, p.product_code, p.batch_number, u.full_name as inspector_name,
                   i.inspection_date, i.quantity_checked, i.accepted_quantity, i.rejected_quantity, i.quality_score, i.status, i.defects, i.remarks, i.line, i.floor, i.created_at
            FROM inspections i
            LEFT JOIN products p ON i.product_id = p.id
            LEFT JOIN users u ON i.inspector_id = u.id
            WHERE 1=1
        """
        params = []
        if filters:
            if filters.get('status'):
                query += " AND i.status = ?"; params.append(filters['status'])
            if filters.get('product_id'):
                query += " AND i.product_id = ?"; params.append(filters['product_id'])
            if filters.get('inspector_id'):
                query += " AND i.inspector_id = ?"; params.append(filters['inspector_id'])
            if filters.get('date_from'):
                query += " AND CAST(i.inspection_date AS DATE) >= ?"; params.append(filters['date_from'])
            if filters.get('date_to'):
                query += " AND CAST(i.inspection_date AS DATE) <= ?"; params.append(filters['date_to'])
        query += " ORDER BY i.inspection_date DESC"
        return self.execute_query(query, tuple(params), fetch_all=True)

    @handle_db_errors
    def get_inspection_by_id(self, inspection_id: int) -> Optional[Dict]:
        insp = self.execute_query("SELECT * FROM inspections WHERE id = ?", (inspection_id,), fetch_one=True)
        if insp:
            insp['defects_list'] = self.execute_query("SELECT * FROM defects WHERE inspection_id = ? ORDER BY severity DESC", (inspection_id,), fetch_all=True)
        return insp

    @handle_db_errors
    def get_inspection_statistics(self) -> Dict:
        stats = {}
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM products WHERE (is_deleted=0 OR is_deleted IS NULL)"); stats['total_products'] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM products WHERE status='Active' AND (is_deleted=0 OR is_deleted IS NULL)"); stats['active_products'] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM inspections"); stats['total_inspections'] = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM inspections WHERE CAST(inspection_date AS DATE) = CAST(GETDATE() AS DATE)"); stats['today_inspections'] = cursor.fetchone()[0]
            cursor.execute("SELECT AVG(CAST(quality_score AS FLOAT)) FROM inspections WHERE quality_score IS NOT NULL"); result = cursor.fetchone()[0]; stats['avg_quality_score'] = float(result) if result else 0
            cursor.execute("SELECT CASE WHEN COUNT(*)>0 THEN CAST(SUM(CASE WHEN quality_score>=80 THEN 1 ELSE 0 END) AS FLOAT)*100/COUNT(*) ELSE 0 END FROM inspections WHERE quality_score IS NOT NULL"); result = cursor.fetchone()[0]; stats['pass_rate'] = float(result) if result else 0
            cursor.execute("SELECT CASE WHEN SUM(quantity_checked)>0 THEN CAST(SUM(rejected_quantity) AS FLOAT)*100/SUM(quantity_checked) ELSE 0 END FROM inspections"); result = cursor.fetchone()[0]; stats['rejection_rate'] = float(result) if result else 0
            cursor.execute("SELECT TOP (5) i.inspection_code, ISNULL(p.product_name,'Unknown') as product_name, i.quality_score, i.status, i.inspection_date FROM inspections i LEFT JOIN products p ON i.product_id = p.id ORDER BY i.inspection_date DESC")
            recent = cursor.fetchall()
            stats['recent_inspections'] = [{'code':r[0],'product':r[1],'score':float(r[2]) if r[2] else 0,'status':r[3],'date':r[4]} for r in recent]
        return stats

    @handle_db_errors
    def get_recent_inspections(self, limit: int = 10) -> List[Dict]:
        query = """
            SELECT TOP (?) i.id, i.inspection_code, i.inspection_type, i.inspection_date, i.status, i.quality_score,
                ISNULL(p.product_name,'N/A') as product_name, ISNULL(u.full_name,'Unknown') as inspector_name
            FROM inspections i LEFT JOIN products p ON i.product_id = p.id LEFT JOIN users u ON i.inspector_id = u.id
            ORDER BY i.inspection_date DESC
        """
        return self.execute_query(query, (limit,), fetch_all=True)

    @handle_db_errors
    def check_connection(self) -> bool:
        try:
            with self.get_connection() as conn:
                conn.cursor().execute("SELECT 1")
            return True
        except Exception:
            return False

    @handle_db_errors
    def add_notification(self, user_id: int, title: str, message: str, notification_type: str = 'info') -> bool:
        self.execute_query("INSERT INTO notifications (user_id, title, message, type) VALUES (?,?,?,?)", (user_id, title, message, notification_type))
        return True

    @handle_db_errors
    def get_notifications(self, user_id: int, unread_only: bool = False) -> List[Dict]:
        query = "SELECT * FROM notifications WHERE user_id = ?"
        params = [user_id]
        if unread_only:
            query += " AND is_read = 0"
        query += " ORDER BY created_at DESC"
        return self.execute_query(query, tuple(params), fetch_all=True)

    @handle_db_errors
    def mark_notification_read(self, notification_id: int) -> bool:
        self.execute_query("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
        return True

    @handle_db_errors
    def log_audit(self, table_name: str, record_id: int, action: str, old_value: str = None, new_value: str = None, changed_by: int = None, ip: str = None) -> bool:
        self.execute_query("INSERT INTO audit_log (table_name, record_id, action, old_value, new_value, changed_by, ip_address) VALUES (?,?,?,?,?,?,?)", (table_name, record_id, action, old_value, new_value, changed_by, ip))
        return True

    @handle_db_errors
    def get_audit_trail(self, table_name: str = None, record_id: int = None, days: int = 30) -> List[Dict]:
        query = "SELECT a.*, u.full_name as changed_by_name FROM audit_log a LEFT JOIN users u ON a.changed_by = u.id WHERE a.changed_at >= DATEADD(day, -?, GETDATE())"
        params = [days]
        if table_name:
            query += " AND a.table_name = ?"; params.append(table_name)
        if record_id:
            query += " AND a.record_id = ?"; params.append(record_id)
        query += " ORDER BY a.changed_at DESC"
        return self.execute_query(query, tuple(params), fetch_all=True)

    def close_all_connections(self) -> None:
        for conn in self._connection_pool:
            try:
                conn.close()
            except Exception:
                pass
        self._connection_pool.clear()

    def close(self) -> None:
        self.close_all_connections()


# ========== VALIDATOR ==========
class DataValidator:
    @staticmethod
    def validate_product_data(data: Dict) -> Tuple[bool, str]:
        required = ['product_code', 'product_name', 'batch_number', 'production_date']
        for f in required:
            if not data.get(f):
                return False, f"Missing {f}"
        if len(data['product_code'])>50:
            return False, "Product code too long"
        if len(data['product_name'])>100:
            return False, "Product name too long"
        return True, "Valid"

    @staticmethod
    def validate_inspection_data(data: Dict) -> Tuple[bool, str]:
        required = ['product_id', 'inspector_id', 'quantity_checked']
        for f in required:
            if data.get(f) is None:
                return False, f"Missing {f}"
        if data['quantity_checked'] <= 0:
            return False, "Quantity must be >0"
        if data.get('accepted_quantity',0) > data['quantity_checked']:
            return False, "Accepted cannot exceed checked"
        return True, "Valid"

    @staticmethod
    def validate_user_data(data: Dict) -> Tuple[bool, str]:
        required = ['username', 'password', 'full_name']
        for f in required:
            if not data.get(f):
                return False, f"Missing {f}"
        if len(data['username'])<3:
            return False, "Username too short"
        if len(data['password'])<6:
            return False, "Password too short"
        valid_roles = ['admin','inspector','viewer','manager']
        if data.get('role') and data['role'] not in valid_roles:
            return False, f"Invalid role"
        return True, "Valid"


# ========== TEST ==========
if __name__ == "__main__":
    print("Testing database...")
    db = Database()
    print("Initialized OK")
    db.close()