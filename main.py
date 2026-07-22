import tkinter as tk
import csv
from tkinter import filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from db_manager import DBManager
from config import APP_TITLE, THEME, WINDOW_SIZE, FONT_BOLD, FONT_NORMAL, CATEGORIES, CATEGORY_COLORS

class ContactApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.style = ttk.Style(theme=THEME)
        self.db = DBManager()
        self.selected_id = None

        self.setup_ui()
        self.load_contacts()

    def setup_ui(self):
        """Build the modular UI components."""
        # Main Container
        self.main_frame = ttk.Frame(self.root, padding=20)
        self.main_frame.pack(fill=BOTH, expand=YES)

        # Header with Theme Toggle
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=X, pady=(0, 20))

        ttk.Label(header_frame, text="ProContact Manager ✨", font=("Segoe UI", 28, "bold"), bootstyle=PRIMARY).pack(side=LEFT)
        
        self.theme_btn = ttk.Checkbutton(header_frame, text="Dark Mode", bootstyle="round-toggle", command=self.toggle_theme)
        self.theme_btn.pack(side=RIGHT, pady=10)
        self.theme_btn.state(['selected']) # Default to dark

        # Statistics Dashboard
        self.stats_frame = ttk.Frame(self.main_frame)
        self.stats_frame.pack(fill=X, pady=(0, 20))
        self.update_stats_ui()

        # Content: Sidebar (Left) and List (Right)
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill=BOTH, expand=YES)

        # ------------------ LEFT SIDEBAR (INPUT) ------------------
        self.sidebar = ttk.LabelFrame(self.content_frame, text=" Contact Details ")
        self.sidebar.pack(side=LEFT, fill=Y, padx=(0, 15))

        # Inner frame for padding (since LabelFrame doesn't support padding in some Tcl versions)
        self.sidebar_inner = ttk.Frame(self.sidebar, padding=15)
        self.sidebar_inner.pack(fill=BOTH, expand=YES)

        # Input Fields
        self.entries = {}
        
        # Standard Fields
        fields = [("Name:", "name"), ("Phone:", "phone"), ("Email:", "email"), ("Birthday:", "birthday")]
        for label_text, attr in fields:
            ttk.Label(self.sidebar_inner, text=label_text, font=FONT_NORMAL).pack(anchor=W, pady=(8, 2))
            entry = ttk.Entry(self.sidebar_inner, width=30)
            entry.pack(fill=X, pady=2)
            self.entries[attr] = entry

        # Category Dropdown
        ttk.Label(self.sidebar_inner, text="Category:", font=FONT_NORMAL).pack(anchor=W, pady=(8, 2))
        self.cat_var = tk.StringVar(value="Other")
        self.cat_combo = ttk.Combobox(self.sidebar_inner, textvariable=self.cat_var, values=CATEGORIES, state="readonly")
        self.cat_combo.pack(fill=X, pady=2)
        self.entries['category'] = self.cat_combo

        # Address Field (Text instead of Entry for better space)
        ttk.Label(self.sidebar_inner, text="Address:", font=FONT_NORMAL).pack(anchor=W, pady=(8, 2))
        self.address_entry = ttk.Entry(self.sidebar_inner, width=30)
        self.address_entry.pack(fill=X, pady=2)
        self.entries['address'] = self.address_entry

        # Buttons (Action)
        self.btn_frame = ttk.Frame(self.sidebar_inner)
        self.btn_frame.pack(fill=X, pady=(25, 0))

        self.btn_add = ttk.Button(self.btn_frame, text="➕ Add", width=12, bootstyle=SUCCESS, command=self.add_contact)
        self.btn_add.grid(row=0, column=0, padx=5, pady=5)

        self.btn_update = ttk.Button(self.btn_frame, text="💾 Update", width=12, bootstyle=WARNING, command=self.update_contact)
        self.btn_update.grid(row=0, column=1, padx=5, pady=5)

        self.btn_delete = ttk.Button(self.btn_frame, text="🗑️ Delete", width=12, bootstyle=DANGER, command=self.delete_contact)
        self.btn_delete.grid(row=1, column=0, padx=5, pady=5)

        self.btn_clear = ttk.Button(self.btn_frame, text="🧹 Clear", width=12, bootstyle=SECONDARY, command=self.clear_fields)
        self.btn_clear.grid(row=1, column=1, padx=5, pady=5)

        # ------------------ RIGHT CONTENT (SEARCH & LIST) ------------------
        self.right_frame = ttk.Frame(self.content_frame)
        self.right_frame.pack(side=RIGHT, fill=BOTH, expand=YES)

        # Search Bar
        self.search_frame = ttk.Frame(self.right_frame)
        self.search_frame.pack(fill=X, pady=(0, 10))

        ttk.Label(self.search_frame, text="Search:", font=FONT_NORMAL).pack(side=LEFT, padx=(0, 10))
        self.search_entry = ttk.Entry(self.search_frame, bootstyle=PRIMARY)
        self.search_entry.pack(side=LEFT, fill=X, expand=YES, padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda e: self.search_contacts())

        self.btn_refresh = ttk.Button(self.search_frame, text="🔄 Refresh", bootstyle="info-outline", command=self.load_contacts)
        self.btn_refresh.pack(side=RIGHT, padx=5)

        self.btn_export = ttk.Button(self.search_frame, text="📥 Export CSV", bootstyle="success-outline", command=self.export_csv)
        self.btn_export.pack(side=RIGHT, padx=5)

        # Contact List (Treeview)
        tree_columns = ("ID", "Name", "Phone", "Email", "Category", "Birthday", "Address")
        self.tree = ttk.Treeview(self.right_frame, columns=tree_columns, show="headings", bootstyle=INFO)
        
        column_widths = {"ID": 50, "Name": 150, "Phone": 120, "Email": 180, "Category": 100, "Birthday": 100, "Address": 200}
        
        for col in tree_columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor=W, width=column_widths.get(col, 150))
        self.tree.pack(fill=BOTH, expand=YES)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # Scrollbar for Treeview
        self.scrollbar = ttk.Scrollbar(self.tree, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.pack(side=RIGHT, fill=Y)


    def update_stats_ui(self):
        """Update the dashboard stats."""
        for widget in self.stats_frame.winfo_children():
            widget.destroy()

        contacts = self.db.get_all_contacts()
        total = len(contacts)
        
        # Total Card
        card = ttk.Frame(self.stats_frame, bootstyle=SECONDARY, padding=10)
        card.pack(side=LEFT, padx=5, fill=X, expand=YES)
        ttk.Label(card, text="Total Contacts", font=FONT_NORMAL).pack()
        ttk.Label(card, text=str(total), font=("Segoe UI", 18, "bold")).pack()

        # Category Breakdown
        counts = {cat: 0 for cat in CATEGORIES}
        for c in contacts:
            cat = c.get('category', 'Other')
            if cat in counts: counts[cat] += 1
        
        for cat, count in counts.items():
            if count > 0:
                color = CATEGORY_COLORS.get(cat, "secondary")
                card = ttk.Frame(self.stats_frame, bootstyle=color, padding=10)
                card.pack(side=LEFT, padx=5, fill=X, expand=YES)
                ttk.Label(card, text=cat, font=FONT_NORMAL, bootstyle=f"{color}-inverse").pack()
                ttk.Label(card, text=str(count), font=("Segoe UI", 18, "bold"), bootstyle=f"{color}-inverse").pack()

    def toggle_theme(self):
        """Switch between dark and light themes."""
        theme = "superhero" if self.theme_btn.instate(['selected']) else "flatly"
        self.style.theme_use(theme)

    def get_input_data(self):
        """Retrieve data from entry widgets."""
        data = {attr: entry.get().strip() for attr, entry in self.entries.items()}
        return data

    def validate_input(self, data):
        """Basic validation."""
        if not data['name'] or not data['phone']:
            messagebox.showwarning("Incomplete Data", "Name and Phone Number are required fields!")
            return False
        return True

    def clear_fields(self):
        """Reset input fields and selection."""
        for entry in self.entries.values():
            entry.delete(0, END)
        self.selected_id = None
        self.tree.selection_remove(self.tree.selection())

    def load_contacts(self):
        """Fetch all contacts from database and update Treeview."""
        self.tree.delete(*self.tree.get_children())
        contacts = self.db.get_all_contacts()
        for c in contacts:
            self.tree.insert("", END, values=(c['id'], c['name'], c['phone'], c['email'], c['category'], c['birthday'], c['address']))
        self.update_stats_ui()

    def search_contacts(self):
        """Search contacts in database and update Treeview."""
        query = self.search_entry.get().strip()
        if not query:
            self.load_contacts()
            return
        
        self.tree.delete(*self.tree.get_children())
        contacts = self.db.search_contacts(query)
        for c in contacts:
            self.tree.insert("", END, values=(c['id'], c['name'], c['phone'], c['email'], c['category'], c['birthday'], c['address']))

    def add_contact(self):
        """Insert new contact."""
        data = self.get_input_data()
        if self.validate_input(data):
            if self.db.add_contact(data['name'], data['phone'], data['email'], data['address'], data['category'], data['birthday']):
                ttk.dialogs.Messagebox.show_info("Success", "Contact added successfully!")
                self.clear_fields()
                self.load_contacts()
            else:
                ttk.dialogs.Messagebox.show_error("Error", "Could not connect to database or add contact.")

    def on_select(self, event):
        """Handle contact selection from list."""
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            values = item['values']
            self.selected_id = values[0]
            
            # Populate entry widgets
            for i, attr in enumerate(["name", "phone", "email", "category", "birthday", "address"]):
                if attr == 'category':
                    self.cat_var.set(values[i+1])
                else:
                    self.entries[attr].delete(0, END)
                    self.entries[attr].insert(0, values[i+1])

    def update_contact(self):
        """Update existing contact."""
        if not self.selected_id:
            ttk.dialogs.Messagebox.show_warning("No Selection", "Please select a contact from the list first!")
            return
        
        data = self.get_input_data()
        if self.validate_input(data):
            if self.db.update_contact(self.selected_id, data['name'], data['phone'], data['email'], data['address'], data['category'], data['birthday']):
                ttk.dialogs.Messagebox.show_info("Success", "Contact updated successfully!")
                self.clear_fields()
                self.load_contacts()

    def delete_contact(self):
        """Delete selected contact."""
        if not self.selected_id:
            ttk.dialogs.Messagebox.show_warning("No Selection", "Please select a contact from the list first!")
            return
        
        if ttk.dialogs.Messagebox.ask_yesno("Confirm Delete", "Are you sure you want to delete this contact?"):
            if self.db.delete_contact(self.selected_id):
                ttk.dialogs.Messagebox.show_info("Success", "Contact deleted successfully!")
                self.clear_fields()
                self.load_contacts()

    def export_csv(self):
        """Export current contact list to CSV."""
        contacts = self.db.get_all_contacts()
        if not contacts:
            ttk.dialogs.Messagebox.show_warning("No Data", "There are no contacts to export.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=contacts[0].keys())
                    writer.writeheader()
                    writer.writerows(contacts)
                ttk.dialogs.Messagebox.show_info("Success", f"Contacts exported to {file_path}")
            except Exception as e:
                ttk.dialogs.Messagebox.show_error("Error", f"Failed to export CSV: {e}")

if __name__ == "__main__":
    root = ttk.Window(themename=THEME)
    app = ContactApp(root)
    root.mainloop()
