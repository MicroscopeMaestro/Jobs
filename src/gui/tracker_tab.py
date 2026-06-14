import os
import json
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QMessageBox, QInputDialog, QComboBox, QDialog,
                             QFormLayout, QLineEdit)
from PySide6.QtCore import Qt

class AddEntryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Application")
        self.resize(300, 200)
        
        layout = QFormLayout(self)
        
        self.company_input = QLineEdit()
        self.position_input = QLineEdit()
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Draft", "Applied", "Interviewing", "Offer", "Rejected"])
        self.status_combo.setCurrentText("Applied")
        self.notes_input = QLineEdit()
        
        layout.addRow("Company:", self.company_input)
        layout.addRow("Position:", self.position_input)
        layout.addRow("Status:", self.status_combo)
        layout.addRow("Notes:", self.notes_input)
        
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        
        layout.addRow(btn_layout)
        
    def get_data(self):
        return {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "company": self.company_input.text().strip(),
            "position": self.position_input.text().strip(),
            "status": self.status_combo.currentText(),
            "notes": self.notes_input.text().strip()
        }

class TrackerTab(QWidget):
    def __init__(self, project_root, parent=None):
        super().__init__(parent)
        self.project_root = project_root
        self.tracker_file = os.path.join(project_root, "data", "tracker.json")
        self.entries = []
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.add_btn = QPushButton("➕ Add Entry")
        self.add_btn.clicked.connect(self.on_add_entry)
        
        self.status_btn = QPushButton("🔄 Update Status")
        self.status_btn.clicked.connect(self.on_update_status)
        
        self.del_btn = QPushButton("➖ Delete")
        self.del_btn.clicked.connect(self.on_delete_entry)
        
        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.status_btn)
        toolbar.addWidget(self.del_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Date", "Company", "Position", "Status", "Notes"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        
    def load_data(self):
        if not os.path.exists(self.tracker_file):
            self.entries = []
            return
            
        try:
            with open(self.tracker_file, 'r', encoding='utf-8') as f:
                self.entries = json.load(f)
            self.refresh_table()
        except Exception as e:
            print(f"Error loading tracker data: {e}")
            self.entries = []
            
    def save_data(self):
        os.makedirs(os.path.dirname(self.tracker_file), exist_ok=True)
        try:
            with open(self.tracker_file, 'w', encoding='utf-8') as f:
                json.dump(self.entries, f, indent=4)
        except Exception as e:
            print(f"Error saving tracker data: {e}")
            
    def refresh_table(self):
        self.table.setRowCount(0)
        for row_idx, entry in enumerate(reversed(self.entries)): # Newest first
            self.table.insertRow(row_idx)
            self.table.setItem(row_idx, 0, QTableWidgetItem(entry.get("date", "")))
            self.table.setItem(row_idx, 1, QTableWidgetItem(entry.get("company", "")))
            self.table.setItem(row_idx, 2, QTableWidgetItem(entry.get("position", "")))
            
            status_item = QTableWidgetItem(entry.get("status", ""))
            # Color code status
            status = entry.get("status", "").lower()
            if status == "offer":
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            elif status == "rejected":
                status_item.setForeground(Qt.GlobalColor.red)
            elif status == "interviewing":
                status_item.setForeground(Qt.GlobalColor.blue)
                
            self.table.setItem(row_idx, 3, status_item)
            self.table.setItem(row_idx, 4, QTableWidgetItem(entry.get("notes", "")))
            
        self.table.resizeColumnsToContents()
        self.table.setColumnWidth(1, 200) # Company
        self.table.setColumnWidth(2, 250) # Position
            
    def on_add_entry(self):
        dlg = AddEntryDialog(self)
        if dlg.exec():
            data = dlg.get_data()
            if data["company"] or data["position"]:
                self.entries.append(data)
                self.save_data()
                self.refresh_table()
                
    def get_real_index(self, row):
        # Table shows reversed list, so we map visual row to actual list index
        return len(self.entries) - 1 - row

    def on_update_status(self):
        curr_row = self.table.currentRow()
        if curr_row < 0:
            QMessageBox.warning(self, "Select row", "Please select an application to update.")
            return
            
        real_idx = self.get_real_index(curr_row)
        entry = self.entries[real_idx]
        
        statuses = ["Draft", "Applied", "Interviewing", "Offer", "Rejected"]
        current = entry.get("status", "Applied")
        try:
            curr_idx = statuses.index(current)
        except ValueError:
            curr_idx = 0
            
        status, ok = QInputDialog.getItem(self, "Update Status", "Select new status:", statuses, curr_idx, False)
        if ok and status:
            self.entries[real_idx]["status"] = status
            self.save_data()
            self.refresh_table()
            
    def on_delete_entry(self):
        curr_row = self.table.currentRow()
        if curr_row < 0:
            QMessageBox.warning(self, "Select row", "Please select an application to delete.")
            return
            
        company = self.table.item(curr_row, 1).text()
        position = self.table.item(curr_row, 2).text()
        
        reply = QMessageBox.question(self, "Confirm Delete", f"Delete application for '{position}' at '{company}'?", 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                                     
        if reply == QMessageBox.StandardButton.Yes:
            real_idx = self.get_real_index(curr_row)
            del self.entries[real_idx]
            self.save_data()
            self.refresh_table()

    def auto_log_application(self, company, position):
        """Called externally when a new application is successfully compiled."""
        # Avoid instant duplicates (same company and position on the same day)
        today = datetime.now().strftime("%Y-%m-%d")
        for entry in self.entries:
            if entry.get("date") == today and entry.get("company") == company and entry.get("position") == position:
                return # Already logged today
                
        self.entries.append({
            "date": today,
            "company": company,
            "position": position,
            "status": "Applied",
            "notes": "Auto-logged by AI compiler"
        })
        self.save_data()
        self.refresh_table()
