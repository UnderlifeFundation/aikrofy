"""
Google Sheets Integration
Inventory and data management via Google Sheets
"""
import os
from typing import List, Dict, Optional, Any
import gspread
from google.oauth2.service_account import Credentials


class GoogleSheetsIntegration:
    """Google Sheets integration for inventory management"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.readonly'
    ]
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Google Sheets integration
        
        Args:
            credentials_path: Path to service account JSON file
        """
        self.credentials_path = credentials_path or os.getenv('GOOGLE_CREDENTIALS_PATH')
        self._client = None
    
    def _get_client(self):
        """Get or create gspread client"""
        if self._client:
            return self._client
        
        if not self.credentials_path or not os.path.exists(self.credentials_path):
            raise ValueError("Google credentials not configured")
        
        credentials = Credentials.from_service_account_file(
            self.credentials_path,
            scopes=self.SCOPES
        )
        
        self._client = gspread.authorize(credentials)
        return self._client
    
    def open_spreadsheet(self, spreadsheet_id: str):
        """Open a spreadsheet by ID"""
        client = self._get_client()
        return client.open_by_key(spreadsheet_id)
    
    def get_inventory(
        self,
        spreadsheet_id: str,
        sheet_name: str = 'Inventory',
        include_headers: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get inventory data from a spreadsheet
        
        Args:
            spreadsheet_id: Google Sheets ID
            sheet_name: Name of the sheet containing inventory
            include_headers: Whether to include header row
        
        Returns:
            List of inventory items as dictionaries
        """
        try:
            spreadsheet = self.open_spreadsheet(spreadsheet_id)
            worksheet = spreadsheet.worksheet(sheet_name)
            
            # Get all records (assumes first row is headers)
            records = worksheet.get_all_records()
            
            return records
        except Exception as e:
            raise Exception(f"Failed to get inventory: {str(e)}")
    
    def search_inventory(
        self,
        spreadsheet_id: str,
        query: str,
        sheet_name: str = 'Inventory',
        search_columns: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search inventory for matching items
        
        Args:
            spreadsheet_id: Google Sheets ID
            query: Search query
            sheet_name: Name of the sheet
            search_columns: Columns to search in (default: all)
        
        Returns:
            List of matching items
        """
        inventory = self.get_inventory(spreadsheet_id, sheet_name)
        
        query_lower = query.lower()
        results = []
        
        for item in inventory:
            for key, value in item.items():
                # Skip if search_columns specified and key not in list
                if search_columns and key not in search_columns:
                    continue
                
                if str(value).lower().find(query_lower) != -1:
                    results.append(item)
                    break
        
        return results
    
    def get_product_by_code(
        self,
        spreadsheet_id: str,
        product_code: str,
        sheet_name: str = 'Inventory',
        code_column: str = 'Code'
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific product by its code
        
        Args:
            spreadsheet_id: Google Sheets ID
            product_code: Product code to find
            sheet_name: Name of the sheet
            code_column: Column name containing product codes
        
        Returns:
            Product data or None if not found
        """
        inventory = self.get_inventory(spreadsheet_id, sheet_name)
        
        for item in inventory:
            if str(item.get(code_column, '')).lower() == product_code.lower():
                return item
        
        return None
    
    def check_stock(
        self,
        spreadsheet_id: str,
        product_code: str,
        sheet_name: str = 'Inventory',
        code_column: str = 'Code',
        quantity_column: str = 'Quantity'
    ) -> Dict[str, Any]:
        """
        Check stock availability for a product
        
        Args:
            spreadsheet_id: Google Sheets ID
            product_code: Product code
            sheet_name: Name of the sheet
            code_column: Column for product codes
            quantity_column: Column for quantities
        
        Returns:
            Stock information
        """
        product = self.get_product_by_code(
            spreadsheet_id, product_code, sheet_name, code_column
        )
        
        if not product:
            return {
                'found': False,
                'product_code': product_code,
                'message': 'Product not found'
            }
        
        quantity = product.get(quantity_column, 0)
        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            quantity = 0
        
        return {
            'found': True,
            'product_code': product_code,
            'product': product,
            'quantity': quantity,
            'in_stock': quantity > 0,
            'message': f"{'In stock' if quantity > 0 else 'Out of stock'} ({quantity} available)"
        }
    
    def update_inventory(
        self,
        spreadsheet_id: str,
        product_code: str,
        updates: Dict[str, Any],
        sheet_name: str = 'Inventory',
        code_column: str = 'Code'
    ) -> bool:
        """
        Update inventory item
        
        Args:
            spreadsheet_id: Google Sheets ID
            product_code: Product code to update
            updates: Dictionary of column: value updates
            sheet_name: Name of the sheet
            code_column: Column for product codes
        
        Returns:
            True if successful
        """
        try:
            spreadsheet = self.open_spreadsheet(spreadsheet_id)
            worksheet = spreadsheet.worksheet(sheet_name)
            
            # Find the row
            cell = worksheet.find(product_code)
            if not cell:
                return False
            
            row = cell.row
            
            # Get headers
            headers = worksheet.row_values(1)
            
            # Update each field
            for column_name, value in updates.items():
                if column_name in headers:
                    col = headers.index(column_name) + 1
                    worksheet.update_cell(row, col, value)
            
            return True
        except Exception:
            return False
