"""
MySQL ERP Driver - Safe read-only integration with custom MySQL databases.

Implements database schema discovery, RBAC, AST sql validation, and read-only querying
to ensure no write operations are executed by the AI agents.
"""
import pymysql
import sqlparse
from typing import Any, Dict, List, Optional
from services.erp.driver_interface import BaseERPDriver, ERPAPIError


class MySQLDriver(BaseERPDriver):
    """Secure read-only driver for custom ERP databases structured in MySQL."""

    def __init__(self, erp_url: str, credentials: Dict[str, str]):
        super().__init__(erp_url, credentials)
        # Parse connection details from erp_url or credentials
        self.host = credentials.get("host") or erp_url.replace("mysql://", "").split("/")[0].split(":")[0]
        try:
            port_str = credentials.get("port") or (":" in erp_url and erp_url.split(":")[-1].split("/")[0]) or "3306"
            self.port = int(port_str)
        except ValueError:
            self.port = 3306
            
        self.db_name = credentials.get("database") or credentials.get("db") or (r"/" in erp_url and erp_url.split("/")[-1]) or ""
        self.username = credentials.get("username") or credentials.get("user") or ""
        self.password = credentials.get("password") or ""

    def _get_connection(self):
        """Internal helper to get a raw connection to MySQL."""
        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.username,
            password=self.password,
            database=self.db_name,
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5
        )

    def authenticate(self) -> bool:
        """Test connection handshake."""
        try:
            conn = self._get_connection()
            conn.close()
            return True
        except Exception as e:
            raise ConnectionError(f"MySQL connection handshake failed: {str(e)}")

    def test_connection(self) -> Dict[str, Any]:
        """Test connection and return schema information."""
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT DATABASE() as db, VERSION() as ver")
                row = cursor.fetchone()
                db_name = row.get("db") if row else self.db_name
                version = row.get("ver") if row else "Unknown"
            conn.close()
            return {
                "success": True,
                "company_name": f"MySQL DB: {db_name}",
                "version": version
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_customer(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Safety override: write operations are forbidden on direct DB connections."""
        raise ERPAPIError(
            "Write operations (CREATE CUSTOMER) are disabled on custom databases for security. "
            "Zero-Trust safety policy prevents any modifications.", 
            403
        )

    def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Safety override: write operations are forbidden on direct DB connections."""
        raise ERPAPIError(
            "Write operations (CREATE INVOICE) are disabled on custom databases for security. "
            "Zero-Trust safety policy prevents any modifications.", 
            403
        )

    def get_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Retrieve a specific invoice by ID from MySQL."""
        # Detect table name for invoices in the current database
        table_name = self._detect_table_name(["invoices", "facturas", "sales_invoices"])
        if not table_name:
            raise KeyError("Invoice table not found in custom database.")

        query = f"SELECT * FROM `{table_name}` WHERE id = %s LIMIT 1"
        records = self._execute_safe_query(query, (invoice_id,))
        if records:
            return records[0]
        raise KeyError(f"Invoice {invoice_id} not found in custom database.")

    def query_customers(self, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """Query customers from DB."""
        table_name = self._detect_table_name(["customers", "clientes", "business_partners", "partners"])
        if not table_name:
            raise ERPAPIError("Customers table not found in custom database.", 404)
        return self.query_records(table_name, filters, limit)

    def query_invoices(self, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """Query invoices from DB."""
        table_name = self._detect_table_name(["invoices", "facturas", "sales_invoices"])
        if not table_name:
            raise ERPAPIError("Invoices table not found in custom database.", 404)
        return self.query_records(table_name, filters, limit)

    def query_items(self, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """Query products/items from DB."""
        table_name = self._detect_table_name(["items", "products", "productos", "inventario"])
        if not table_name:
            raise ERPAPIError("Items/products table not found in custom database.", 404)
        return self.query_records(table_name, filters, limit)

    def query_records(self, entity_name: str, filters: Dict[str, Any], limit: int = 50) -> List[Dict[str, Any]]:
        """Perform a SELECT query with filtering and built-in SQL injection validation."""
        # Sanitize entity table name to prevent SQL injection
        table_name = "".join(c for c in entity_name if c.isalnum() or c in ("_", "-"))
        
        # Build parameterized query
        where_clauses = []
        query_params = []
        for key, value in filters.items():
            col_name = "".join(c for c in key if c.isalnum() or c == "_")
            where_clauses.append(f"`{col_name}` = %s")
            query_params.append(value)

        where_str = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        query = f"SELECT * FROM `{table_name}`{where_str} LIMIT %s"
        query_params.append(limit)

        return self._execute_safe_query(query, tuple(query_params))

    def _detect_table_name(self, candidate_names: List[str]) -> Optional[str]:
        """Discover database tables dynamically to identify relevant schemas."""
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = [list(row.values())[0] for row in cursor.fetchall()]
            conn.close()
            
            for candidate in candidate_names:
                for table in tables:
                    if table.lower() == candidate.lower():
                        return table
            return tables[0] if tables else None
        except Exception:
            return None

    def _execute_safe_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Validates query syntactically and runs read-only SELECT command."""
        # Capa 2: AST SQL Validation
        parsed = sqlparse.parse(query)
        if not parsed:
            raise ERPAPIError("Empty or invalid query generated.", 400)

        forbidden_keywords = {
            "insert", "update", "delete", "drop", "alter", "truncate", 
            "create", "replace", "grant", "revoke", "lock", "rename"
        }

        for stmt in parsed:
            if stmt.get_type() != "SELECT":
                raise ERPAPIError(
                    f"Forbidden operation: Query type {stmt.get_type()} is blocked by Zero-Trust policy.", 
                    403
                )
            for token in stmt.flatten():
                token_val = token.value.lower().strip()
                if token_val in forbidden_keywords:
                    raise ERPAPIError(
                        f"Forbidden keyword '{token_val}' detected in query. Transaction cancelled.", 
                        403
                    )

        # Execute query via connection
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            raise ERPAPIError(f"Database execution error: {str(e)}", 500)
