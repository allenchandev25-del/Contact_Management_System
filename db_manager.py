import mysql.connector
from config import DB_CONFIG

class DBManager:
    def __init__(self):
        self.conn = None
        self.cursor = None

    def connect(self):
        """Establish a connection to the database."""
        try:
            self.conn = mysql.connector.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor(dictionary=True)
            self.ensure_schema() # Automatically ensure schema is up-to-date
            return True
        except mysql.connector.Error as err:
            print(f"Error connecting to MySQL: {err}")
            return False

    def ensure_schema(self):
        """Add new columns if they don't exist."""
        try:
            # Check existing columns
            self.cursor.execute("DESCRIBE contacts")
            columns = [col['Field'] for col in self.cursor.fetchall()]
            
            if 'category' not in columns:
                self.cursor.execute("ALTER TABLE contacts ADD COLUMN category VARCHAR(50) DEFAULT 'Other'")
            if 'birthday' not in columns:
                self.cursor.execute("ALTER TABLE contacts ADD COLUMN birthday VARCHAR(20)")
            
            self.conn.commit()
        except mysql.connector.Error as err:
            print(f"Error updating schema: {err}")

    def close(self):
        """Close current connection."""
        if self.conn:
            self.cursor.close()
            self.conn.close()

    def add_contact(self, name, phone, email, address, category, birthday):
        """Insert a contact into the database."""
        if not self.connect(): return False
        try:
            query = "INSERT INTO contacts (name, phone, email, address, category, birthday) VALUES (%s, %s, %s, %s, %s, %s)"
            self.cursor.execute(query, (name, phone, email, address, category, birthday))
            self.conn.commit()
            return True
        finally:
            self.close()

    def get_all_contacts(self):
        """Retrieve all contacts from the database."""
        if not self.connect(): return []
        try:
            self.cursor.execute("SELECT * FROM contacts ORDER BY name ASC")
            return self.cursor.fetchall()
        finally:
            self.close()

    def search_contacts(self, term):
        """Find contacts matching a search word."""
        if not self.connect(): return []
        try:
            query = """SELECT * FROM contacts 
                       WHERE name LIKE %s OR phone LIKE %s OR email LIKE %s OR category LIKE %s
                       ORDER BY name ASC"""
            search_param = f"%{term}%"
            self.cursor.execute(query, (search_param, search_param, search_param, search_param))
            return self.cursor.fetchall()
        finally:
            self.close()

    def update_contact(self, contact_id, name, phone, email, address, category, birthday):
        """Update an existing contact by ID."""
        if not self.connect(): return False
        try:
            query = "UPDATE contacts SET name=%s, phone=%s, email=%s, address=%s, category=%s, birthday=%s WHERE id=%s"
            self.cursor.execute(query, (name, phone, email, address, category, birthday, contact_id))
            self.conn.commit()
            return True
        finally:
            self.close()

    def delete_contact(self, contact_id):
        """Delete a contact by ID."""
        if not self.connect(): return False
        try:
            self.cursor.execute("DELETE FROM contacts WHERE id=%s", (contact_id,))
            self.conn.commit()
            return True
        finally:
            self.close()
