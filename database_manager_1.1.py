import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog, scrolledtext
import sqlite3
import os
import csv
import shutil
import json
import datetime

class DataManager:
    def __init__(self, root):
        self.root = root
        self.root.title("SQLite Database Manager [Version: 1.1]")
        self.current_db = None
        self.current_table = None
        self.sidebar = None            # For table context sidebar
        self.data_context_menu = None  # Context menu for data rows

        # Additional attributes
        self.query_history = []        # Stores executed queries
        self.log = []                  # Stores log messages
        self.last_operation = None     # Stores last operation for undo
        self.dark_mode = False         # Flag for dark mode

        # Create menu bar
        self.menu_bar = tk.Menu(root)

        # ------------------- File Menu ------------------- #
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.file_menu.add_command(label="New Database", command=self.new_database)
        self.file_menu.add_command(label="Open Database", command=self.open_database)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Run Query", command=self.run_query_window)
        self.file_menu.add_command(label="Backup Database", command=self.backup_database)
        self.file_menu.add_command(label="Import CSV", command=self.import_csv_to_table)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="About", command=self.show_about)
        self.file_menu.add_command(label="Changelog", command=self.show_changelog)
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=root.quit)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)

        # ------------------- Tools Menu ------------------- #
        self.tools_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.tools_menu.add_command(label="Export Schema", command=self.export_schema)
        self.tools_menu.add_command(label="Run SQL Script", command=self.run_sql_script)
        self.tools_menu.add_command(label="Import JSON", command=self.import_json)
        self.tools_menu.add_command(label="Generate Sample Data", command=self.generate_sample_data)
        self.tools_menu.add_command(label="Drop All Tables", command=self.drop_all_tables)
        self.tools_menu.add_command(label="Undo Last Operation", command=self.undo_last_operation)
        self.tools_menu.add_command(label="Database Summary", command=self.show_database_summary)
        self.tools_menu.add_command(label="Toggle Dark Mode", command=self.toggle_dark_mode)
        self.tools_menu.add_command(label="Reset Filters", command=self.reset_filters)
        self.menu_bar.add_cascade(label="Tools", menu=self.tools_menu)

        # ------------------- Predefined Queries Menu ------------------- #
        self.predefined_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.predefined_menu.add_command(label="Show Table Row Count", command=self.predefined_row_count)
        self.predefined_menu.add_command(label="List All Tables", command=self.predefined_list_tables)
        self.menu_bar.add_cascade(label="Predefined Queries", menu=self.predefined_menu)

        # ------------------- Help Menu ------------------- #
        self.help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.help_menu.add_command(label="Documentation", command=self.show_documentation)
        self.help_menu.add_command(label="View Log", command=self.view_log)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)

        self.root.config(menu=self.menu_bar)

        # ------------------- Main Frame ------------------- #
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Database Info
        self.db_info_frame = ttk.LabelFrame(self.main_frame, text="Database Information")
        self.db_info_frame.pack(fill=tk.X, pady=5)
        self.db_path_label = ttk.Label(self.db_info_frame, text="No database selected")
        self.db_path_label.pack(side=tk.LEFT, padx=5)

        # Left Frame for Tables
        self.left_frame = ttk.Frame(self.main_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        # Tables List
        self.tables_frame = ttk.LabelFrame(self.left_frame, text="Tables")
        self.tables_frame.pack(fill=tk.BOTH, expand=True)
        self.tables_tree = ttk.Treeview(self.tables_frame, height=15)
        self.tables_tree.pack(fill=tk.BOTH, expand=True)
        # Bind left-click for loading data and right-click for table sidebar
        self.tables_tree.bind("<<TreeviewSelect>>", self.load_table_data)
        self.tables_tree.bind("<Button-3>", self.show_table_sidebar)

        # Table Controls (Create, Delete, and Refresh)
        self.table_controls = ttk.Frame(self.left_frame)
        self.table_controls.pack(pady=5)
        self.create_table_btn = ttk.Button(self.table_controls, text="Create Table", command=self.create_table_dialog)
        self.create_table_btn.pack(side=tk.LEFT, padx=2)
        self.delete_table_btn = ttk.Button(self.table_controls, text="Delete Table", command=self.delete_table)
        self.delete_table_btn.pack(side=tk.LEFT, padx=2)
        self.refresh_tables_btn = ttk.Button(self.table_controls, text="Refresh Tables", command=self.load_tables)
        self.refresh_tables_btn.pack(side=tk.LEFT, padx=2)

        # Right Frame for Data Display
        self.data_frame = ttk.LabelFrame(self.main_frame, text="Table Data")
        self.data_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # Data Search Field with Reset button
        self.search_var = tk.StringVar()
        search_frame = ttk.Frame(self.data_frame)
        search_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.search_entry.bind("<KeyRelease>", self.filter_data)
        self.reset_search_btn = ttk.Button(search_frame, text="Reset", command=self.reset_filters)
        self.reset_search_btn.pack(side=tk.LEFT, padx=5)

        # Data Treeview
        self.data_tree = ttk.Treeview(self.data_frame)
        self.data_tree.pack(fill=tk.BOTH, expand=True)
        # Bind right-click for data context menu and double-click for row details
        self.data_tree.bind("<Button-3>", self.show_data_context_menu)
        self.data_tree.bind("<Double-1>", self.show_row_details)

        # Data Controls (Add, Edit, Delete, Refresh, Export buttons)
        self.data_controls = ttk.Frame(self.data_frame)
        self.data_controls.pack(pady=5)
        self.add_data_btn = ttk.Button(self.data_controls, text="Add Data", command=self.add_data_dialog)
        self.add_data_btn.pack(side=tk.LEFT, padx=2)
        self.edit_data_btn = ttk.Button(self.data_controls, text="Edit Data", command=self.edit_data_dialog)
        self.edit_data_btn.pack(side=tk.LEFT, padx=2)
        self.delete_data_btn = ttk.Button(self.data_controls, text="Delete Data", command=self.delete_data)
        self.delete_data_btn.pack(side=tk.LEFT, padx=2)
        self.refresh_data_btn = ttk.Button(self.data_controls, text="Refresh Data", command=lambda: self.load_table_data(None))
        self.refresh_data_btn.pack(side=tk.LEFT, padx=2)
        self.export_data_btn = ttk.Button(self.data_controls, text="Export Table to CSV", command=self.export_table_csv)
        self.export_data_btn.pack(side=tk.LEFT, padx=2)

        # Additional friendly feature: Status Bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(self.main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w")
        self.status_bar.pack(fill=tk.X, padx=2, pady=(2,0))

    # --------------------- Logging Helper --------------------- #
    def log_operation(self, message):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.log.append(entry)
        print(entry)

    # --------------------- Status Helper --------------------- #
    def set_status(self, message):
        self.status_var.set(message)
        self.log_operation(message)
        self.root.after(3000, lambda: self.status_var.set("Ready"))

    # --------------------- Database & Table Functions --------------------- #
    def new_database(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite Database", "*.db")])
        if file_path:
            try:
                open(file_path, 'w').close()
                self.current_db = file_path
                self.db_path_label.config(text=file_path)
                self.load_tables()
                messagebox.showinfo("Success", "New database created successfully")
                self.set_status("New database created successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create database: {str(e)}")

    def open_database(self):
        file_path = filedialog.askopenfilename(filetypes=[("SQLite Database", "*.db")])
        if file_path:
            self.current_db = file_path
            self.db_path_label.config(text=file_path)
            self.load_tables()
            self.set_status("Database opened")

    def backup_database(self):
        if not self.current_db:
            messagebox.showwarning("Warning", "No database to backup")
            return
        backup_path = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite Database", "*.db")],
                                                  title="Backup Database As")
        if backup_path:
            try:
                shutil.copy(self.current_db, backup_path)
                messagebox.showinfo("Success", f"Database backed up to {backup_path}")
                self.set_status("Database backed up")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to backup database: {str(e)}")

    def import_csv_to_table(self):
        if not self.current_table:
            messagebox.showwarning("Warning", "Please select a table to import data into")
            return
        file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")],
                                               title="Select CSV File")
        if file_path:
            try:
                conn = sqlite3.connect(self.current_db)
                cursor = conn.cursor()
                with open(file_path, "r", encoding="utf-8") as f:
                    reader = csv.reader(f)
                    headers = next(reader)  # assume first row is header
                    for row in reader:
                        placeholders = ", ".join(["?"] * len(row))
                        query = f"INSERT INTO {self.current_table} VALUES ({placeholders})"
                        cursor.execute(query, row)
                conn.commit()
                conn.close()
                self.load_table_data(None)
                messagebox.showinfo("Success", f"Data imported from {file_path}")
                self.set_status("CSV data imported")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import CSV: {str(e)}")

    def load_tables(self):
        self.tables_tree.delete(*self.tables_tree.get_children())
        if self.current_db:
            try:
                conn = sqlite3.connect(self.current_db)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                for table in tables:
                    self.tables_tree.insert("", tk.END, text=table[0], values=table[0])
                conn.close()
                self.set_status("Tables loaded")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load tables: {str(e)}")

    def create_table_dialog(self):
        if not self.current_db:
            messagebox.showwarning("Warning", "Please create or open a database first")
            return

        self.table_dialog = tk.Toplevel(self.root)
        self.table_dialog.title("Create Table")

        ttk.Label(self.table_dialog, text="Table Name:").grid(row=0, column=0, padx=5, pady=5)
        self.table_name_entry = ttk.Entry(self.table_dialog)
        self.table_name_entry.grid(row=0, column=1, padx=5, pady=5)

        self.columns = []
        self.add_column_fields()

        ttk.Button(self.table_dialog, text="Add Column", command=self.add_column_fields).grid(row=999, column=0, pady=10)
        ttk.Button(self.table_dialog, text="Create Table", command=self.create_table).grid(row=999, column=1, pady=10)

    def add_column_fields(self, row=None):
        row = len(self.columns) + 1 if row is None else row
        column_frame = ttk.Frame(self.table_dialog)
        column_frame.grid(row=row, column=0, columnspan=2, sticky="ew")
        ttk.Label(column_frame, text="Column Name:").pack(side=tk.LEFT)
        name_entry = ttk.Entry(column_frame)
        name_entry.pack(side=tk.LEFT, padx=5)
        ttk.Label(column_frame, text="Data Type:").pack(side=tk.LEFT)
        type_combobox = ttk.Combobox(column_frame, values=["TEXT", "INTEGER", "REAL", "BLOB", "NULL"], state="readonly")
        type_combobox.pack(side=tk.LEFT, padx=5)
        ttk.Label(column_frame, text="Constraints:").pack(side=tk.LEFT)
        constraints_entry = ttk.Entry(column_frame)
        constraints_entry.pack(side=tk.LEFT, padx=5)
        self.columns.append((name_entry, type_combobox, constraints_entry))

    def create_table(self):
        table_name = self.table_name_entry.get().strip()
        if not table_name:
            messagebox.showwarning("Warning", "Please enter a table name")
            return

        columns = []
        for col in self.columns:
            name = col[0].get().strip()
            dtype = col[1].get().strip()
            constraints = col[2].get().strip()
            if name and dtype:
                column_def = f"{name} {dtype} {constraints}".strip()
                columns.append(column_def)

        if not columns:
            messagebox.showwarning("Warning", "Please add at least one column")
            return

        try:
            conn = sqlite3.connect(self.current_db)
            cursor = conn.cursor()
            query = f"CREATE TABLE {table_name} ({', '.join(columns)})"
            cursor.execute(query)
            conn.commit()
            conn.close()
            self.load_tables()
            self.table_dialog.destroy()
            messagebox.showinfo("Success", "Table created successfully")
            self.set_status("Table created successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create table: {str(e)}")

    def delete_table(self):
        selected = self.tables_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a table to delete")
            return
        table_name = self.tables_tree.item(selected[0], "text")
        if messagebox.askyesno("Confirm", f"Delete table '{table_name}'?"):
            try:
                conn = sqlite3.connect(self.current_db)
                cursor = conn.cursor()
                cursor.execute(f"DROP TABLE {table_name}")
                conn.commit()
                conn.close()
                self.load_tables()
                messagebox.showinfo("Success", "Table deleted successfully")
                self.set_status("Table deleted successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete table: {str(e)}")

    def load_table_data(self, event):
        selected = self.tables_tree.selection()
        if not selected:
            return
        self.current_table = self.tables_tree.item(selected[0], "text")
        self.data_tree.delete(*self.data_tree.get_children())
        try:
            conn = sqlite3.connect(self.current_db)
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            columns_info = cursor.fetchall()
            columns = [col[1] for col in columns_info]
            self.data_tree["columns"] = columns
            self.data_tree["show"] = "headings"
            for col in columns:
                self.data_tree.heading(col, text=col)
                self.data_tree.column(col, width=100)
            cursor.execute(f"SELECT * FROM {self.current_table}")
            self.all_rows = cursor.fetchall()  # Store rows for searching/filtering
            for row in self.all_rows:
                self.data_tree.insert("", tk.END, values=row)
            conn.close()
            self.set_status("Table data loaded")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load table data: {str(e)}")

    # --------------------- Data Row Operations --------------------- #
    def add_data_dialog(self):
        if not self.current_table:
            messagebox.showwarning("Warning", "Please select a table first")
            return
        self.data_dialog = tk.Toplevel(self.root)
        self.data_dialog.title("Add Data")
        try:
            conn = sqlite3.connect(self.current_db)
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            columns = cursor.fetchall()
            conn.close()
            self.data_entries = []
            for i, col in enumerate(columns):
                ttk.Label(self.data_dialog, text=col[1]).grid(row=i, column=0, padx=5, pady=2)
                entry = ttk.Entry(self.data_dialog)
                entry.grid(row=i, column=1, padx=5, pady=2)
                self.data_entries.append(entry)
            ttk.Button(self.data_dialog, text="Add", command=self.add_data).grid(row=len(columns), column=0, columnspan=2, pady=10)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load columns: {str(e)}")

    def add_data(self):
        try:
            conn = sqlite3.connect(self.current_db)
            cursor = conn.cursor()
            columns = []
            values = []
            for entry in self.data_entries:
                row = entry.grid_info()["row"]
                label_widgets = entry.master.grid_slaves(row=row, column=0)
                if label_widgets:
                    col_name = label_widgets[0]["text"]
                    columns.append(col_name)
                else:
                    continue
                values.append(entry.get())
            query = f"INSERT INTO {self.current_table} ({', '.join(columns)}) VALUES ({', '.join(['?']*len(values))})"
            cursor.execute(query, values)
            conn.commit()
            conn.close()
            self.last_operation = {"action": "add", "data": values, "columns": columns}
            self.load_table_data(None)
            self.data_dialog.destroy()
            messagebox.showinfo("Success", "Data added successfully")
            self.set_status("Data added successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add data: {str(e)}")

    def edit_data_dialog(self):
        selected = self.data_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a record to edit")
            return
        self.edit_data_window = tk.Toplevel(self.root)
        self.edit_data_window.title("Edit Data")
        try:
            conn = sqlite3.connect(self.current_db)
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            columns = [col[1] for col in cursor.fetchall()]
            values = self.data_tree.item(selected[0], "values")
            self.edit_entries = []
            for i, (col, val) in enumerate(zip(columns, values)):
                ttk.Label(self.edit_data_window, text=col).grid(row=i, column=0, padx=5, pady=2)
                entry = ttk.Entry(self.edit_data_window)
                entry.insert(0, val)
                entry.grid(row=i, column=1, padx=5, pady=2)
                self.edit_entries.append(entry)
            ttk.Button(self.edit_data_window, text="Update",
                       command=lambda: self.update_data(selected[0])).grid(row=len(columns), column=0, columnspan=2, pady=10)
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data: {str(e)}")

    def update_data(self, item_id):
        try:
            conn = sqlite3.connect(self.current_db)
            cursor = conn.cursor()
            columns = []
            for entry in self.edit_entries:
                row = entry.grid_info()["row"]
                label_widgets = self.edit_data_window.grid_slaves(row=row, column=0)
                if label_widgets:
                    columns.append(label_widgets[0]["text"])
            values = [entry.get() for entry in self.edit_entries]
            primary_key = self.get_primary_key()
            pk_value = self.data_tree.item(item_id, "values")[0]
            set_clause = ", ".join([f"{col} = ?" for col in columns])
            query = f"UPDATE {self.current_table} SET {set_clause} WHERE {primary_key} = ?"
            cursor.execute(query, values + [pk_value])
            conn.commit()
            conn.close()
            self.last_operation = {"action": "edit", "old": self.data_tree.item(item_id, "values"), "new": values, "columns": columns, "pk": pk_value}
            self.load_table_data(None)
            self.edit_data_window.destroy()
            messagebox.showinfo("Success", "Data updated successfully")
            self.set_status("Data updated successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update data: {str(e)}")

    def delete_data(self):
        selected = self.data_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select record(s) to delete")
            return
        if messagebox.askyesno("Confirm", "Delete selected record(s)?"):
            try:
                conn = sqlite3.connect(self.current_db)
                cursor = conn.cursor()
                primary_key = self.get_primary_key()
                deleted_rows = []
                for item in selected:
                    value = self.data_tree.item(item, "values")[0]
                    deleted_rows.append(self.data_tree.item(item, "values"))
                    cursor.execute(f"DELETE FROM {self.current_table} WHERE {primary_key} = ?", (value,))
                conn.commit()
                conn.close()
                self.last_operation = {"action": "delete", "rows": deleted_rows, "pk": primary_key}
                self.load_table_data(None)
                messagebox.showinfo("Success", "Data deleted successfully")
                self.set_status("Data deleted successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete data: {str(e)}")

    def get_primary_key(self):
        try:
            conn = sqlite3.connect(self.current_db)
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            for col in cursor.fetchall():
                if col[5] == 1:
                    conn.close()
                    return col[1]
            conn.close()
            return "rowid"
        except Exception as e:
            return "rowid"

    # --------------------- Right-Click Context Menus & Row Details --------------------- #
    def show_table_sidebar(self, event):
        row_id = self.tables_tree.identify_row(event.y)
        if not row_id:
            return
        self.tables_tree.selection_set(row_id)
        table_name = self.tables_tree.item(row_id, "text")
        if self.sidebar is not None and self.sidebar.winfo_exists():
            self.sidebar.destroy()
        self.sidebar = tk.Toplevel(self.root)
        self.sidebar.title(f"Table Options: {table_name}")
        self.sidebar.geometry("+{}+{}".format(event.x_root, event.y_root))
        self.sidebar.attributes("-topmost", True)
        ttk.Button(self.sidebar, text="Edit Table Name", command=lambda: self.edit_table_name(table_name)).pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(self.sidebar, text="View Table Schema", command=lambda: self.edit_table_schema(table_name)).pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(self.sidebar, text="Delete Table", command=lambda: self.delete_table_by_sidebar(table_name)).pack(fill=tk.X, padx=10, pady=5)

    def delete_table_by_sidebar(self, table_name):
        if messagebox.askyesno("Confirm", f"Delete table '{table_name}'?"):
            try:
                conn = sqlite3.connect(self.current_db)
                cursor = conn.cursor()
                cursor.execute(f"DROP TABLE {table_name}")
                conn.commit()
                conn.close()
                self.load_tables()
                messagebox.showinfo("Success", "Table deleted successfully")
                if self.sidebar is not None:
                    self.sidebar.destroy()
                self.set_status("Table deleted successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete table: {str(e)}")

    def edit_table_name(self, old_name):
        new_name = simpledialog.askstring("Edit Table Name", f"Enter new name for table '{old_name}':")
        if new_name and new_name.strip():
            try:
                conn = sqlite3.connect(self.current_db)
                cursor = conn.cursor()
                cursor.execute(f"ALTER TABLE {old_name} RENAME TO {new_name.strip()}")
                conn.commit()
                conn.close()
                self.load_tables()
                messagebox.showinfo("Success", f"Table renamed to '{new_name.strip()}'")
                if self.sidebar is not None:
                    self.sidebar.destroy()
                self.set_status("Table renamed successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to rename table: {str(e)}")

    def edit_table_schema(self, table_name):
        try:
            conn = sqlite3.connect(self.current_db)
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            schema_info = cursor.fetchall()
            conn.close()
            schema_text = f"Schema for table '{table_name}':\n\n"
            schema_text += "cid | name | type | notnull | dflt_value | pk\n"
            schema_text += "-" * 50 + "\n"
            for col in schema_info:
                schema_text += " | ".join(str(item) for item in col) + "\n"
            schema_window = tk.Toplevel(self.root)
            schema_window.title(f"Schema of {table_name}")
            text_widget = scrolledtext.ScrolledText(schema_window, width=60, height=15)
            text_widget.pack(fill=tk.BOTH, expand=True)
            text_widget.insert(tk.END, schema_text)
            text_widget.configure(state="disabled")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to retrieve schema: {str(e)}")

    def show_data_context_menu(self, event):
        row_id = self.data_tree.identify_row(event.y)
        if not row_id:
            return
        self.data_tree.selection_set(row_id)
        if self.data_context_menu is None:
            self.data_context_menu = tk.Menu(self.root, tearoff=0)
            self.data_context_menu.add_command(label="Edit Row", command=self.edit_data_dialog)
            self.data_context_menu.add_command(label="Delete Row(s)", command=self.delete_data)
            self.data_context_menu.add_separator()
            self.data_context_menu.add_command(label="Export Table to CSV", command=self.export_table_csv)
        self.data_context_menu.post(event.x_root, event.y_root)

    def show_row_details(self, event):
        # On double-click, show details of the selected row
        row_id = self.data_tree.identify_row(event.y)
        if not row_id:
            return
        row_values = self.data_tree.item(row_id, "values")
        detail_win = tk.Toplevel(self.root)
        detail_win.title("Row Details")
        text = scrolledtext.ScrolledText(detail_win, width=60, height=10)
        text.pack(fill=tk.BOTH, expand=True)
        detail_text = "\n".join(str(val) for val in row_values)
        text.insert(tk.END, detail_text)
        text.configure(state="disabled")

    # --------------------- Additional Features --------------------- #
    def export_table_csv(self):
        if not self.current_table:
            messagebox.showwarning("Warning", "Please select a table first")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")],
                                                 title="Export Table to CSV")
        if file_path:
            try:
                conn = sqlite3.connect(self.current_db)
                cursor = conn.cursor()
                cursor.execute(f"SELECT * FROM {self.current_table}")
                rows = cursor.fetchall()
                cursor.execute(f"PRAGMA table_info({self.current_table})")
                headers = [col[1] for col in cursor.fetchall()]
                conn.close()
                with open(file_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
                    writer.writerows(rows)
                messagebox.showinfo("Success", f"Data exported to {file_path}")
                self.set_status("Data exported to CSV")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export data: {str(e)}")

    def run_query_window(self):
        if not self.current_db:
            messagebox.showwarning("Warning", "Please open a database first")
            return

        query_win = tk.Toplevel(self.root)
        query_win.title("Run SQL Query")
        ttk.Label(query_win, text="Enter SQL Query:").pack(padx=5, pady=5)
        query_text = scrolledtext.ScrolledText(query_win, width=80, height=10)
        query_text.pack(padx=5, pady=5)
        # Clear Query Editor button
        clear_btn = ttk.Button(query_win, text="Clear", command=lambda: query_text.delete("1.0", tk.END))
        clear_btn.pack(pady=2)
        ttk.Label(query_win, text="Results:").pack(padx=5, pady=5)
        results_text = scrolledtext.ScrolledText(query_win, width=80, height=15)
        results_text.pack(padx=5, pady=5)
        results_text.configure(state="disabled")

        def execute_query():
            sql = query_text.get("1.0", tk.END).strip()
            if not sql:
                messagebox.showwarning("Warning", "Please enter a SQL query")
                return
            try:
                conn = sqlite3.connect(self.current_db)
                cursor = conn.cursor()
                cursor.execute(sql)
                if sql.lower().startswith("select"):
                    rows = cursor.fetchall()
                    headers = [description[0] for description in cursor.description]
                    output = "\t".join(headers) + "\n" + "-" * 50 + "\n"
                    for row in rows:
                        output += "\t".join(str(item) for item in row) + "\n"
                else:
                    conn.commit()
                    output = "Query executed successfully."
                conn.close()
                results_text.configure(state="normal")
                results_text.delete("1.0", tk.END)
                results_text.insert(tk.END, output)
                results_text.configure(state="disabled")
                self.query_history.append(sql)
                self.set_status("Query executed")
            except Exception as e:
                messagebox.showerror("Error", f"Query failed: {str(e)}")

        ttk.Button(query_win, text="Run Query", command=execute_query).pack(pady=5)

    def show_tutorial(self):
        tutorial_window = tk.Toplevel(self.root)
        tutorial_window.title("Tutorial")
        tutorial_text = scrolledtext.ScrolledText(tutorial_window, width=80, height=25)
        tutorial_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        tutorial_content = (
            "SQLite Tutorial\n"
            "----------------\n\n"
            "Data Types:\n"
            " - TEXT: Used for text strings.\n"
            " - INTEGER: Used for whole numbers.\n"
            " - REAL: Used for floating-point numbers.\n"
            " - BLOB: Used for binary data.\n"
            " - NULL: Represents a NULL value.\n\n"
            "Constraints:\n"
            " - PRIMARY KEY: Uniquely identifies each record.\n"
            " - NOT NULL: Ensures a column cannot have a NULL value.\n"
            " - UNIQUE: Ensures all values in a column are different.\n"
            " - CHECK: Ensures values satisfy a specified condition.\n"
            " - DEFAULT: Sets a default value if none is provided.\n\n"
            "Extra Features:\n"
            " - Run Query: Execute arbitrary SQL queries against the current database.\n"
            " - Backup Database: Create a backup copy of the current database file.\n"
            " - Import CSV/JSON: Import data from CSV/JSON files into the selected table.\n"
            " - Export to CSV: Export table data to a CSV file for use in spreadsheets.\n"
            " - Refresh: Quickly update the tables and data views.\n"
            " - Search: Filter data rows by keywords.\n\n"
            "Additional Features Added:\n"
            " - Query History, Clear Query Editor, Export Schema, Run SQL Script,\n"
            "   Generate Sample Data, Drop All Tables, Undo Last Operation,\n"
            "   Database Summary, Toggle Dark Mode, Predefined Queries,\n"
            "   Multi-Row Deletion, Row Details Popup, and more.\n\n"
            "Usage:\n"
            "This SQLite Database Manager allows you to create and manage databases,\n"
            "tables, and data. Right-click on table names or data rows to access\n"
            "context-specific options.\n"
        )
        tutorial_text.insert(tk.END, tutorial_content)
        tutorial_text.configure(state="disabled")

    # --------------------- Data Filtering (Search Feature) --------------------- #
    def filter_data(self, event):
        if not hasattr(self, 'all_rows'):
            return
        search_term = self.search_var.get().lower()
        self.data_tree.delete(*self.data_tree.get_children())
        for row in self.all_rows:
            if not search_term or any(search_term in str(cell).lower() for cell in row):
                self.data_tree.insert("", tk.END, values=row)

    def reset_filters(self):
        self.search_var.set("")
        if hasattr(self, 'all_rows'):
            self.data_tree.delete(*self.data_tree.get_children())
            for row in self.all_rows:
                self.data_tree.insert("", tk.END, values=row)
        self.set_status("Filters reset")

    # --------------------- New Feature Methods --------------------- #
    def show_about(self):
        about_text = (
            "This is a Database Manager by Python and SQLite for Database Control.\n\n"
            "This is made by ChatGPT, Gemini and Deepseek\n"
            "and the Ideas by TarangoHasan and Some Ideas by That Artificial Intelligence\n\n"
            "Thank you for using this application!"
        )
        messagebox.showinfo("About", about_text)
        self.log_operation("Displayed About dialog")

    def show_changelog(self):
        changelog = (
        "Changelog [Version 1.0]:\n"
        "---------------------------\n"
        "1. Initial release with basic database operations.\n"
        "2. Added create, open, backup, and import CSV features.\n"
        "3. Implemented table and data management functionalities.\n\n"
        "Changelog [Version 1.1]:\n"
        "---------------------------\n"
        "1. Implemented About and Changelog dialogs.\n"
        "2. Added Query History and a Clear Query Editor button in the query window.\n"
        "3. Introduced Export Schema, Run SQL Script, Import JSON, and Generate Sample Data features.\n"
        "4. Added Drop All Tables and Undo Last Operation functionalities.\n"
        "5. Included Database Summary, Toggle Dark Mode, and Reset Filters options.\n"
        "6. Enabled Predefined Queries for quick stats (e.g., table row count).\n"
        "7. Added multi-row deletion and a Row Details popup on double-click.\n"
        "8. Enhanced UI and functionality with additional tools and logging features.\n"
    )
        changelog_win = tk.Toplevel(self.root)
        changelog_win.title("Changelog")
        text_widget = scrolledtext.ScrolledText(changelog_win, width=70, height=15)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, changelog)
        text_widget.configure(state="disabled")
        self.log_operation("Displayed Changelog")

    def export_schema(self):
        if not self.current_db:
            messagebox.showwarning("Warning", "Please open a database first")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")],
                                                 title="Export Database Schema")
        if file_path:
            try:
                conn = sqlite3.connect(self.current_db)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                schema_text = ""
                for table in tables:
                    table_name = table[0]
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    schema_info = cursor.fetchall()
                    schema_text += f"Schema for {table_name}:\n"
                    schema_text += "cid | name | type | notnull | dflt_value | pk\n"
                    schema_text += "-" * 40 + "\n"
                    for col in schema_info:
                        schema_text += " | ".join(str(item) for item in col) + "\n"
                    schema_text += "\n"
                conn.close()
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(schema_text)
                messagebox.showinfo("Success", f"Schema exported to {file_path}")
                self.set_status("Schema exported")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export schema: {str(e)}")

    def run_sql_script(self):
        if not self.current_db:
            messagebox.showwarning("Warning", "Please open a database first")
            return
        file_path = filedialog.askopenfilename(filetypes=[("SQL Files", "*.sql")], title="Select SQL Script")
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    script = f.read()
                conn = sqlite3.connect(self.current_db)
                cursor = conn.cursor()
                cursor.executescript(script)
                conn.commit()
                conn.close()
                messagebox.showinfo("Success", "SQL script executed successfully")
                self.set_status("SQL script executed")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to execute script: {str(e)}")

    def import_json(self):
        if not self.current_table:
            messagebox.showwarning("Warning", "Please select a table to import data into")
            return
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")], title="Select JSON File")
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Expecting a list of dictionaries
                if not isinstance(data, list):
                    raise ValueError("JSON data must be a list of objects")
                conn = sqlite3.connect(self.current_db)
                cursor = conn.cursor()
                for item in data:
                    keys = item.keys()
                    placeholders = ", ".join(["?"] * len(keys))
                    columns = ", ".join(keys)
                    query = f"INSERT INTO {self.current_table} ({columns}) VALUES ({placeholders})"
                    cursor.execute(query, tuple(item[key] for key in keys))
                conn.commit()
                conn.close()
                self.load_table_data(None)
                messagebox.showinfo("Success", f"Data imported from {file_path}")
                self.set_status("JSON data imported")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import JSON: {str(e)}")

    def generate_sample_data(self):
        if not self.current_table:
            messagebox.showwarning("Warning", "Please select a table to generate sample data into")
            return
        try:
            conn = sqlite3.connect(self.current_db)
            cursor = conn.cursor()
            # This is a simple sample insertion. In a real scenario, generate data based on schema.
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            columns = [col[1] for col in cursor.fetchall()]
            sample_values = ["Sample" for _ in columns]
            query = f"INSERT INTO {self.current_table} ({', '.join(columns)}) VALUES ({', '.join(['?']*len(columns))})"
            cursor.execute(query, sample_values)
            conn.commit()
            conn.close()
            self.load_table_data(None)
            messagebox.showinfo("Success", "Sample data generated successfully")
            self.set_status("Sample data generated")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate sample data: {str(e)}")

    def drop_all_tables(self):
        if not self.current_db:
            messagebox.showwarning("Warning", "No database open")
            return
        if messagebox.askyesno("Confirm", "Are you sure you want to drop ALL tables? This action cannot be undone."):
            try:
                conn = sqlite3.connect(self.current_db)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                for table in tables:
                    cursor.execute(f"DROP TABLE {table[0]}")
                conn.commit()
                conn.close()
                self.load_tables()
                messagebox.showinfo("Success", "All tables dropped successfully")
                self.set_status("All tables dropped")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to drop all tables: {str(e)}")

    def undo_last_operation(self):
        if not self.last_operation:
            messagebox.showinfo("Info", "No operation to undo")
            return
        try:
            conn = sqlite3.connect(self.current_db)
            cursor = conn.cursor()
            op = self.last_operation
            if op["action"] == "add":
                # For an add, delete the last inserted row using primary key if possible
                primary_key = self.get_primary_key()
                cursor.execute(f"DELETE FROM {self.current_table} WHERE {primary_key} = (SELECT {primary_key} FROM {self.current_table} ORDER BY {primary_key} DESC LIMIT 1)")
            elif op["action"] == "delete":
                # For delete, re-insert deleted rows (this is basic and may not restore auto-incremented keys)
                columns = [f"col{i}" for i in range(1, len(op["rows"][0])+1)]
                for row in op["rows"]:
                    placeholders = ", ".join(["?"] * len(row))
                    query = f"INSERT INTO {self.current_table} VALUES ({placeholders})"
                    cursor.execute(query, row)
            elif op["action"] == "edit":
                # For edit, revert to old values
                set_clause = ", ".join([f"{col} = ?" for col in op["columns"]])
                query = f"UPDATE {self.current_table} SET {set_clause} WHERE {self.get_primary_key()} = ?"
                cursor.execute(query, op["old"] + [op["pk"]])
            conn.commit()
            conn.close()
            self.last_operation = None
            self.load_table_data(None)
            messagebox.showinfo("Success", "Undo successful")
            self.set_status("Last operation undone")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to undo operation: {str(e)}")

    def show_database_summary(self):
        if not self.current_db:
            messagebox.showwarning("Warning", "No database open")
            return
        try:
            file_size = os.path.getsize(self.current_db)
            conn = sqlite3.connect(self.current_db)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            conn.close()
            summary = f"Database File: {self.current_db}\nSize: {file_size} bytes\nTables: {table_count}"
            messagebox.showinfo("Database Summary", summary)
            self.log_operation("Displayed Database Summary")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to retrieve database summary: {str(e)}")

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        bg_color = "#2e2e2e" if self.dark_mode else "SystemButtonFace"
        fg_color = "#ffffff" if self.dark_mode else "black"
        # Apply colors to main window and some widgets
        self.root.configure(bg=bg_color)
        self.main_frame.configure(style="Dark.TFrame" if self.dark_mode else "TFrame")
        self.set_status("Dark mode enabled" if self.dark_mode else "Dark mode disabled")
        self.log_operation("Toggled Dark Mode")

    def predefined_row_count(self):
        if not self.current_table:
            messagebox.showwarning("Warning", "Please select a table")
            return
        try:
            conn = sqlite3.connect(self.current_db)
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {self.current_table}")
            count = cursor.fetchone()[0]
            conn.close()
            messagebox.showinfo("Row Count", f"Table '{self.current_table}' has {count} rows.")
            self.log_operation(f"Displayed row count for {self.current_table}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to count rows: {str(e)}")

    def predefined_list_tables(self):
        if not self.current_db:
            messagebox.showwarning("Warning", "No database open")
            return
        try:
            conn = sqlite3.connect(self.current_db)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [table[0] for table in cursor.fetchall()]
            conn.close()
            messagebox.showinfo("Tables", "Tables:\n" + "\n".join(tables))
            self.log_operation("Listed all tables")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to list tables: {str(e)}")

    def show_documentation(self):
        doc_win = tk.Toplevel(self.root)
        doc_win.title("Documentation")
        doc_text = scrolledtext.ScrolledText(doc_win, width=80, height=25)
        doc_text.pack(fill=tk.BOTH, expand=True)
        documentation = (
            "Documentation:\n"
            "-----------------\n"
            "This application is a full-featured SQLite Database Manager built using Python and Tkinter.\n"
            "Features include:\n"
            " - Creating, opening, and backing up databases.\n"
            " - Creating, renaming, deleting, and viewing table schemas.\n"
            " - Importing data from CSV and JSON files.\n"
            " - Running arbitrary SQL queries with query history.\n"
            " - Exporting data to CSV.\n"
            " - Additional tools such as exporting schema, running SQL scripts, generating sample data,\n"
            "   dropping all tables, undoing last operations, and more.\n\n"
            "For further assistance, refer to the tutorial and changelog included in the application."
        )
        doc_text.insert(tk.END, documentation)
        doc_text.configure(state="disabled")
        self.log_operation("Displayed Documentation")

    def view_log(self):
        log_win = tk.Toplevel(self.root)
        log_win.title("Application Log")
        log_text = scrolledtext.ScrolledText(log_win, width=80, height=20)
        log_text.pack(fill=tk.BOTH, expand=True)
        log_text.insert(tk.END, "\n".join(self.log))
        log_text.configure(state="disabled")
        self.log_operation("Viewed application log")

if __name__ == "__main__":
    root = tk.Tk()
    app = DataManager(root)
    root.mainloop()
