#!/usr/bin/env python3
"""
SCHOOL FEE MANAGER 2026 - Professional Edition
Cross-platform: Works on Windows & Linux
Complete with Save/Save As, Print, CSV Export, Undo, Delete, Clear All
"""

import sys
import os
import sqlite3
import csv
import shutil
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtPrintSupport import QPrinter, QPrintDialog

# Detect platform for any platform-specific adjustments
IS_WINDOWS = sys.platform == 'win32'
IS_LINUX = sys.platform == 'linux'

# Database path - platform independent
DB_PATH = Path.home() / "school_fee.db"


class SchoolFeeManager(QMainWindow):
    def __init__(self):
        super().__init__()

        # YOUR CLASSES
        self.classes = [
            "Lily", "Buttercup", "Infant Foundation 1", "Infant Foundation 2",
            "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5",
            "JSS 1", "JSS 2"
        ]

        # YOUR 9 FEE CATEGORIES
        self.fee_categories = [
            "Registration", "Tuition", "Books", "Uniform", "Medicals",
            "Toiletries", "End of Year", "After School Care", "Abacus/Coding"
        ]

        self.current_term = "First Term 2026"
        self.current_file = None
        self.undo_stack = []  # For undo functionality
        self.redo_stack = []  # For redo functionality

        # Fixed amounts per class
        self.fixed_amounts = {}
        for class_name in self.classes:
            self.fixed_amounts[class_name] = {}
            for category in self.fee_categories:
                self.fixed_amounts[class_name][category] = 0

        # Initialize fee widgets list
        self.fee_widgets = []

        # Setup database
        self.setup_database()

        # Setup UI
        self.setup_ui()

        # Load data
        self.load_fixed_amounts()
        self.load_students()

    def setup_database(self):
        """Create database and tables"""
        self.conn = sqlite3.connect(str(DB_PATH))
        self.c = self.conn.cursor()

        self.c.executescript('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                class TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS fixed_fees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL DEFAULT 0,
                term TEXT NOT NULL,
                UNIQUE(class, category, term)
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                amount REAL DEFAULT 0
            );
        ''')

        self.conn.commit()

    def setup_ui(self):
        """Create the user interface with tabs - PROFESSIONAL GREY THEME"""
        self.setWindowTitle("School Fee Manager 2026 - Professional Edition")
        self.setGeometry(100, 100, 1400, 800)

        # Enable window controls
        self.setWindowFlags(Qt.Window)
        self.setWindowState(Qt.WindowActive)

        # Set minimum window size
        self.setMinimumSize(1000, 600)

        # Set application icon based on platform
        if IS_WINDOWS:
            # On Windows, you can set an .ico file
            try:
                self.setWindowIcon(QIcon("icon.ico"))
            except:
                pass
        else:
            # On Linux, use theme icon
            self.setWindowIcon(QIcon.fromTheme("accessories-calculator"))

        # Create menu bar
        self.create_menu_bar()

        # Create toolbar
        self.create_toolbar()

        # Create status bar
        self.statusBar().showMessage("Ready")

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QLabel("🏫 SCHOOL FEE MANAGER 2026")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                padding: 25px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2c3e50, stop:1 #34495e);
                color: white;
                border-bottom: 3px solid #3498db;
            }
        """)
        main_layout.addWidget(header)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: #ecf0f1;
            }
            QTabBar::tab {
                padding: 12px 30px;
                margin-right: 2px;
                font-weight: 500;
                font-size: 14px;
                background-color: #bdc3c7;
                color: #2c3e50;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QTabBar::tab:selected {
                background: #3498db;
                color: white;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background-color: #95a5a6;
                color: white;
            }
        """)

        # Tab 1: Set Fixed Fees
        self.setup_tab = QWidget()
        self.setup_fixed_fees_tab()
        self.tabs.addTab(self.setup_tab, "💰 Set Fixed Fees")

        # Tab 2: Enter Payments
        self.grid_tab = QWidget()
        self.setup_payment_grid()
        self.tabs.addTab(self.grid_tab, "📊 Enter Payments")

        main_layout.addWidget(self.tabs)

    def toggle_maximize(self):
        """Toggle between maximized and normal window"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def create_toolbar(self):
        """Create toolbar with Undo/Delete buttons and window controls"""
        toolbar = self.addToolBar("Quick Actions")
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #ecf0f1;
                border-bottom: 1px solid #bdc3c7;
                spacing: 5px;
                padding: 5px;
            }
            QToolButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 8px;
                color: #2c3e50;
                font-weight: 500;
            }
            QToolButton:hover {
                background-color: #3498db;
                color: white;
            }
            QToolButton:pressed {
                background-color: #2980b9;
            }
        """)

        # Undo button
        undo_action = QAction("↩ Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo)
        toolbar.addAction(undo_action)

        # Redo button
        redo_action = QAction("↪ Redo", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self.redo)
        toolbar.addAction(redo_action)

        toolbar.addSeparator()

        # Delete button
        delete_action = QAction("🗑 Delete", self)
        delete_action.setShortcut("Del")
        delete_action.triggered.connect(self.delete_student)
        toolbar.addAction(delete_action)

        toolbar.addSeparator()

        # Save button
        save_action = QAction("💾 Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_to_file)
        toolbar.addAction(save_action)

        toolbar.addSeparator()

        # Clear All buttons
        clear_fees_action = QAction("🧹 Clear Fees", self)
        clear_fees_action.triggered.connect(self.clear_all_fees)
        toolbar.addAction(clear_fees_action)

        clear_students_action = QAction("🧹 Clear Students", self)
        clear_students_action.triggered.connect(self.clear_all_students)
        toolbar.addAction(clear_students_action)

        toolbar.addSeparator()

        # Window control buttons
        minimize_btn = QAction("➖", self)
        minimize_btn.setToolTip("Minimize Window")
        minimize_btn.triggered.connect(self.showMinimized)
        toolbar.addAction(minimize_btn)

        maximize_btn = QAction("🔲", self)
        maximize_btn.setToolTip("Maximize/Restore Window")
        maximize_btn.triggered.connect(self.toggle_maximize)
        toolbar.addAction(maximize_btn)

        # Exit button
        exit_btn = QAction("✖", self)
        exit_btn.setToolTip("Exit Application")
        exit_btn.triggered.connect(self.close)
        toolbar.addAction(exit_btn)

    def create_menu_bar(self):
        """Create menu bar with File menu for Print, CSV, and Save"""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #34495e;
                color: white;
                border-bottom: 1px solid #2c3e50;
            }
            QMenuBar::item {
                padding: 8px 15px;
                background-color: transparent;
                color: white;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: #3498db;
                color: white;
            }
            QMenu {
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 25px;
                border-radius: 3px;
                color: #2c3e50;
            }
            QMenu::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)

        # File menu
        file_menu = menubar.addMenu("📁 File")

        # Save action
        save_action = QAction("💾 Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_to_file)
        file_menu.addAction(save_action)

        # Save As action
        save_as_action = QAction("💾 Save As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_as_to_file)
        file_menu.addAction(save_as_action)

        # Open action
        open_action = QAction("📂 Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        # Export to CSV action
        export_action = QAction("📥 Export to CSV", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_to_csv)
        file_menu.addAction(export_action)

        # Print action
        print_action = QAction("🖨️ Print", self)
        print_action.setShortcut("Ctrl+P")
        print_action.triggered.connect(self.print_grid)
        file_menu.addAction(print_action)

        file_menu.addSeparator()

        # Exit action
        exit_action = QAction("🚪 Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu for Undo/Redo
        edit_menu = menubar.addMenu("✏️ Edit")

        undo_action = QAction("↩ Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("↪ Redo", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        delete_action = QAction("🗑 Delete Student", self)
        delete_action.setShortcut("Del")
        delete_action.triggered.connect(self.delete_student)
        edit_menu.addAction(delete_action)

        edit_menu.addSeparator()

        # Clear All actions
        clear_fees_action = QAction("🧹 Clear All Fixed Fees", self)
        clear_fees_action.triggered.connect(self.clear_all_fees)
        edit_menu.addAction(clear_fees_action)

        clear_students_action = QAction("🧹 Clear All Students", self)
        clear_students_action.triggered.connect(self.clear_all_students)
        edit_menu.addAction(clear_students_action)

        # Add Window menu
        window_menu = menubar.addMenu("🪟 Window")

        # Minimize action
        minimize_action = QAction("➖ Minimize", self)
        minimize_action.setShortcut("Ctrl+M")
        minimize_action.triggered.connect(self.showMinimized)
        window_menu.addAction(minimize_action)

        # Maximize action
        maximize_action = QAction("🔲 Maximize", self)
        maximize_action.setShortcut("Ctrl+Shift+M")
        maximize_action.triggered.connect(self.toggle_maximize)
        window_menu.addAction(maximize_action)

        window_menu.addSeparator()

        # Normal size action
        normal_action = QAction("🔄 Restore", self)
        normal_action.triggered.connect(self.showNormal)
        window_menu.addAction(normal_action)

        # Help menu
        help_menu = menubar.addMenu("❓ Help")

        # About action
        about_action = QAction("📌 About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def clear_all_fees(self):
        """Clear all fixed fee amounts for the current class"""
        reply = QMessageBox.question(
            self,
            "Clear All Fees",
            "Are you sure you want to clear all fixed fee amounts for this class?\n\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            class_name = self.fixed_class_combo.currentText()

            # Clear in memory
            for category in self.fee_categories:
                self.fixed_amounts[class_name][category] = 0

            # Clear in database
            self.c.execute('''
                DELETE FROM fixed_fees 
                WHERE class=? AND term=?
            ''', (class_name, self.current_term))
            self.conn.commit()

            # Update UI
            self.load_fixed_for_class()

            self.statusBar().showMessage(f"All fees cleared for {class_name}", 3000)

    def clear_all_students(self):
        """Delete all students and their payments"""
        reply = QMessageBox.question(
            self,
            "Clear All Students",
            "Are you sure you want to delete ALL students?\n\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Double confirmation for safety
            confirm = QMessageBox.question(
                self,
                "Final Confirmation",
                "⚠️ This will permanently delete ALL students and their payment records.\n\nAre you absolutely sure?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if confirm == QMessageBox.Yes:
                # Delete all payments first
                self.c.execute("DELETE FROM payments")
                # Delete all students
                self.c.execute("DELETE FROM students")
                self.conn.commit()

                # Clear undo/redo stacks
                self.undo_stack.clear()
                self.redo_stack.clear()

                # Reload
                self.load_students()

                self.statusBar().showMessage("All students deleted", 3000)

    def add_to_undo_stack(self, action_type, data):
        """Add an action to undo stack"""
        self.undo_stack.append((action_type, data))
        self.redo_stack.clear()
        self.statusBar().showMessage(f"Action recorded. Undo available ({len(self.undo_stack)})", 2000)

    def undo(self):
        """Undo last action"""
        if not self.undo_stack:
            QMessageBox.information(self, "Undo", "Nothing to undo")
            return

        action_type, data = self.undo_stack.pop()
        self.redo_stack.append((action_type, data))

        if action_type == "payment_change":
            student_id, category, old_value = data
            self.restore_payment(student_id, category, old_value)
            self.statusBar().showMessage(f"Undo: Payment change", 3000)

        elif action_type == "name_change":
            student_id, old_name = data
            self.restore_student_name(student_id, old_name)
            self.statusBar().showMessage(f"Undo: Name change", 3000)

        elif action_type == "class_change":
            student_id, old_class = data
            self.restore_student_class(student_id, old_class)
            self.statusBar().showMessage(f"Undo: Class change", 3000)

        elif action_type == "add_student":
            student_id = data
            self.delete_student_by_id(student_id)
            self.statusBar().showMessage(f"Undo: Add student", 3000)

        elif action_type == "delete_student":
            student_data, payments_data = data
            self.restore_deleted_student(student_data, payments_data)
            self.statusBar().showMessage(f"Undo: Delete student", 3000)

        self.load_students()

    def redo(self):
        """Redo previously undone action"""
        if not self.redo_stack:
            QMessageBox.information(self, "Redo", "Nothing to redo")
            return

        action_type, data = self.redo_stack.pop()
        self.undo_stack.append((action_type, data))

        if action_type == "payment_change":
            student_id, category, new_value = data
            self.restore_payment(student_id, category, new_value)
            self.statusBar().showMessage(f"Redo: Payment change", 3000)

        elif action_type == "name_change":
            student_id, new_name = data
            self.restore_student_name(student_id, new_name)
            self.statusBar().showMessage(f"Redo: Name change", 3000)

        elif action_type == "class_change":
            student_id, new_class = data
            self.restore_student_class(student_id, new_class)
            self.statusBar().showMessage(f"Redo: Class change", 3000)

        elif action_type == "add_student":
            student_data, payments_data = data
            self.restore_deleted_student(student_data, payments_data)
            self.statusBar().showMessage(f"Redo: Add student", 3000)

        elif action_type == "delete_student":
            student_id = data
            self.delete_student_by_id(student_id)
            self.statusBar().showMessage(f"Redo: Delete student", 3000)

        self.load_students()

    def restore_payment(self, student_id, category, amount):
        """Restore a payment value"""
        self.c.execute('''
            INSERT OR REPLACE INTO payments (student_id, category, amount)
            VALUES (?, ?, ?)
        ''', (student_id, category, amount))
        self.conn.commit()

    def restore_student_name(self, student_id, name):
        """Restore student name"""
        self.c.execute("UPDATE students SET name=? WHERE id=?",
                       (name, student_id))
        self.conn.commit()

    def restore_student_class(self, student_id, class_name):
        """Restore student class"""
        self.c.execute("UPDATE students SET class=? WHERE id=?",
                       (class_name, student_id))
        self.conn.commit()

    def restore_deleted_student(self, student_data, payments_data):
        """Restore a deleted student and their payments"""
        self.c.execute('''
            INSERT INTO students (id, name, class)
            VALUES (?, ?, ?)
        ''', (student_data['id'], student_data['name'], student_data['class']))

        for payment in payments_data:
            self.c.execute('''
                INSERT INTO payments (student_id, category, amount)
                VALUES (?, ?, ?)
            ''', (payment['student_id'], payment['category'], payment['amount']))

        self.conn.commit()

    def delete_student(self):
        """Delete the selected student"""
        current_row = self.table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Delete", "Please select a student to delete")
            return

        name_item = self.table.item(current_row, 0)
        if not name_item:
            return

        student_id = name_item.data(Qt.UserRole)
        student_name = name_item.text()

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete student '{student_name}'?\n\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.save_deleted_student_to_undo(student_id)
            self.delete_student_by_id(student_id)

    def save_deleted_student_to_undo(self, student_id):
        """Save deleted student data to undo stack"""
        self.c.execute("SELECT id, name, class FROM students WHERE id=?", (student_id,))
        student = self.c.fetchone()
        if not student:
            return

        student_data = {
            'id': student[0],
            'name': student[1],
            'class': student[2]
        }

        self.c.execute("SELECT student_id, category, amount FROM payments WHERE student_id=?", (student_id,))
        payments = self.c.fetchall()
        payments_data = []
        for p in payments:
            payments_data.append({
                'student_id': p[0],
                'category': p[1],
                'amount': p[2]
            })

        self.add_to_undo_stack("delete_student", (student_data, payments_data))

    def delete_student_by_id(self, student_id):
        """Delete a student by ID"""
        self.c.execute("DELETE FROM payments WHERE student_id=?", (student_id,))
        self.c.execute("DELETE FROM students WHERE id=?", (student_id,))
        self.conn.commit()

        self.load_students()
        self.statusBar().showMessage(f"Student deleted", 3000)

    def save_to_file(self):
        """Save database to a file (Save)"""
        if hasattr(self, 'current_file') and self.current_file:
            self.backup_database(self.current_file)
            self.statusBar().showMessage(f"Saved to {self.current_file}", 3000)
        else:
            self.save_as_to_file()

    def save_as_to_file(self):
        """Save database to a new file (Save As)"""
        # Platform-independent file dialog
        suggested_name = f"school_fees_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        suggested_path = str(Path.home() / suggested_name)

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Database As",
            suggested_path,
            "Database Files (*.db);;All Files (*)"
        )

        if filename:
            self.current_file = filename
            self.backup_database(filename)
            self.statusBar().showMessage(f"Saved to {filename}", 3000)
            self.setWindowTitle(f"School Fee Manager 2026 - {Path(filename).name}")

    def open_file(self):
        """Open a saved database file"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Database File",
            str(Path.home()),
            "Database Files (*.db);;All Files (*)"
        )

        if filename:
            try:
                self.conn.close()
                shutil.copy2(filename, str(DB_PATH))
                self.conn = sqlite3.connect(str(DB_PATH))
                self.c = self.conn.cursor()

                self.undo_stack.clear()
                self.redo_stack.clear()

                self.load_fixed_amounts()
                self.load_students()

                self.current_file = filename
                self.setWindowTitle(f"School Fee Manager 2026 - {Path(filename).name}")
                self.statusBar().showMessage(f"Opened {filename}", 3000)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {str(e)}")

    def backup_database(self, filename):
        """Backup the current database to a file"""
        try:
            shutil.copy2(str(DB_PATH), filename)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")
            return False

    def export_to_csv(self):
        """Export current grid data to CSV file"""
        suggested_name = f"school_fees_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        suggested_path = str(Path.home() / suggested_name)

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save CSV File",
            suggested_path,
            "CSV Files (*.csv);;All Files (*)"
        )

        if not filename:
            return

        try:
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                headers = ["Student Name", "Class"] + self.fee_categories + ["Expected", "Paid", "Outstanding"]
                writer.writerow(headers)

                if self.tabs.currentIndex() == 1:
                    for row in range(self.table.rowCount()):
                        row_data = []
                        name_item = self.table.item(row, 0)
                        row_data.append(name_item.text() if name_item else "")

                        class_combo = self.table.cellWidget(row, 1)
                        row_data.append(class_combo.currentText() if class_combo else "")

                        for col in range(2, 2 + len(self.fee_categories)):
                            item = self.table.item(row, col)
                            row_data.append(item.text().replace(',', '') if item else "0")

                        expected_item = self.table.item(row, 2 + len(self.fee_categories))
                        paid_item = self.table.item(row, 3 + len(self.fee_categories))
                        outstanding_item = self.table.item(row, 4 + len(self.fee_categories))

                        row_data.append(expected_item.text().replace(',', '') if expected_item else "0")
                        row_data.append(paid_item.text().replace(',', '') if paid_item else "0")
                        row_data.append(outstanding_item.text().replace(',', '') if outstanding_item else "0")

                        writer.writerow(row_data)

                QMessageBox.information(self, "Success", f"Data exported to:\n{filename}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export: {str(e)}")

    def print_grid(self):
        """Print the current grid"""
        printer = QPrinter(QPrinter.HighResolution)

        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QPrintDialog.Accepted:
            return

        try:
            doc = QTextDocument()
            html = self.generate_print_html()
            doc.setHtml(html)
            doc.print_(printer)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to print: {str(e)}")

    def generate_print_html(self):
        """Generate HTML for printing"""
        html = f"""
        <html>
        <head>
            <style>
                body {{ 
                    font-family: 'Segoe UI', Arial, sans-serif; 
                    margin: 30px; 
                    color: #2c3e50;
                }}
                h1 {{ 
                    color: #2c3e50; 
                    text-align: center; 
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 15px;
                    margin-bottom: 20px;
                }}
                h2 {{ 
                    color: #34495e; 
                    margin-top: 20px; 
                    font-size: 18px;
                }}
                table {{ 
                    border-collapse: collapse; 
                    width: 100%; 
                    margin-top: 20px; 
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }}
                th {{ 
                    background: #34495e;
                    color: white; 
                    padding: 12px; 
                    text-align: left; 
                    font-weight: 600;
                    font-size: 13px;
                }}
                td {{ 
                    border: 1px solid #bdc3c7; 
                    padding: 10px; 
                    font-size: 12px;
                }}
                tr:nth-child(even) {{ background-color: #f8f9fa; }}
                .total {{ font-weight: bold; color: #2980b9; }}
                .paid {{ color: #27ae60; font-weight: bold; }}
                .outstanding {{ color: #c0392b; font-weight: bold; }}
                .footer {{ 
                    margin-top: 30px; 
                    font-size: 11px; 
                    color: #7f8c8d; 
                    text-align: center; 
                    border-top: 1px solid #bdc3c7;
                    padding-top: 15px;
                }}
            </style>
        </head>
        <body>
            <h1>🏫 SCHOOL FEE MANAGER 2026</h1>
            <h2>Payment Report - {self.current_term}</h2>
            <p style="color: #7f8c8d;">Generated on: {datetime.now().strftime('%B %d, %Y at %H:%M')}</p>
        """

        html += '<table>'
        html += '<tr><th>Student Name</th><th>Class</th>'

        for cat in self.fee_categories:
            html += f'<th>{cat}</th>'

        html += '<th>Expected</th><th>Paid</th><th>Outstanding</th></tr>'

        if self.tabs.currentIndex() == 1:
            for row in range(self.table.rowCount()):
                html += '<tr>'

                name_item = self.table.item(row, 0)
                html += f'<td>{name_item.text() if name_item else ""}</td>'

                class_combo = self.table.cellWidget(row, 1)
                html += f'<td>{class_combo.currentText() if class_combo else ""}</td>'

                for col in range(2, 2 + len(self.fee_categories)):
                    item = self.table.item(row, col)
                    html += f'<td>{item.text() if item else "0"}</td>'

                expected_item = self.table.item(row, 2 + len(self.fee_categories))
                paid_item = self.table.item(row, 3 + len(self.fee_categories))
                outstanding_item = self.table.item(row, 4 + len(self.fee_categories))

                expected_class = "total"
                paid_class = "paid"
                outstanding_class = "outstanding" if float(
                    outstanding_item.text().replace(',', '') or 0) > 0 else "paid"

                html += f'<td class="{expected_class}">{expected_item.text() if expected_item else "0"}</td>'
                html += f'<td class="{paid_class}">{paid_item.text() if paid_item else "0"}</td>'
                html += f'<td class="{outstanding_class}">{outstanding_item.text() if outstanding_item else "0"}</td>'

                html += '</tr>'

        html += '</table>'
        html += f'<div class="footer">School Fee Manager 2026 Professional Edition - Printed on {datetime.now().strftime("%Y-%m-%d")}</div>'
        html += '</body></html>'

        return html

    def show_about(self):
        """Show about dialog"""
        msg = QMessageBox(self)
        msg.setWindowTitle("About School Fee Manager 2026")
        msg.setIconPixmap(QPixmap())
        msg.setText("""
            <div style='text-align: center;'>
                <h2 style='color: #2c3e50; margin-bottom: 5px;'>🏫 School Fee Manager 2026</h2>
                <p style='color: #3498db; font-weight: bold; margin-top: 0;'>Professional Edition v4.0</p>
                <hr style='border: 1px solid #bdc3c7; width: 80%;'>
                <table style='margin: 15px auto; text-align: left; color: #34495e;'>
                    <tr><td><b>✓</b> Set fixed fees per class</td></tr>
                    <tr><td><b>✓</b> Type directly into any cell</td></tr>
                    <tr><td><b>✓</b> Automatic calculation</td></tr>
                    <tr><td><b>✓</b> Undo/Redo (Ctrl+Z, Ctrl+Y)</td></tr>
                    <tr><td><b>✓</b> Delete students with confirmation</td></tr>
                    <tr><td><b>✓</b> Clear All Fees</td></tr>
                    <tr><td><b>✓</b> Clear All Students</td></tr>
                    <tr><td><b>✓</b> Save and Open files (Ctrl+S, Ctrl+O)</td></tr>
                    <tr><td><b>✓</b> Export to CSV (Ctrl+E)</td></tr>
                    <tr><td><b>✓</b> Print reports (Ctrl+P)</td></tr>
                    <tr><td><b>✓</b> Windows & Linux compatible</td></tr>
                </table>
                <hr style='border: 1px solid #bdc3c7; width: 80%;'>
                <p style='color: #7f8c8d; font-size: 12px;'>
                    <b>9 Fee Categories:</b> Registration, Tuition, Books, Uniform,<br>
                    Medicals, Toiletries, End of Year, After School Care, Abacus/Coding
                </p>
                <p style='color: #95a5a6; font-size: 11px;'>© 2026 Premium Edition. All rights reserved.</p>
            </div>
        """)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()

    def setup_fixed_fees_tab(self):
        """Tab for setting fixed amounts per class - Perfect spacing and alignment"""
        layout = QVBoxLayout(self.setup_tab)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)

        # Title
        title = QLabel("Set Fixed Amounts Per Class")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #1e293b;
            padding: 0 0 15px 0;
            border-bottom: 2px solid #3498db;
            margin-bottom: 5px;
        """)
        layout.addWidget(title)

        # Class selector with Clear button
        selector_container = QWidget()
        selector_layout = QHBoxLayout(selector_container)
        selector_layout.setContentsMargins(0, 0, 0, 0)
        selector_layout.setSpacing(15)

        # Class selector frame
        class_frame = QWidget()
        class_frame.setStyleSheet("""
            QWidget {
                background-color: #f8fafc;
                border-radius: 6px;
                padding: 5px;
            }
        """)
        class_layout = QHBoxLayout(class_frame)
        class_layout.setContentsMargins(10, 8, 10, 8)
        class_layout.setSpacing(15)

        class_label = QLabel("Class:")
        class_label.setStyleSheet("""
            font-size: 14px;
            font-weight: 600;
            color: #334155;
            min-width: 45px;
        """)
        class_layout.addWidget(class_label)

        self.fixed_class_combo = QComboBox()
        self.fixed_class_combo.addItems(self.classes)
        self.fixed_class_combo.setMinimumWidth(250)
        self.fixed_class_combo.setStyleSheet("""
            QComboBox {
                padding: 8px 12px;
                border: 1px solid #cbd5e1;
                border-radius: 5px;
                background: white;
                font-size: 14px;
                min-height: 20px;
            }
            QComboBox:hover {
                border-color: #3498db;
            }
            QComboBox:focus {
                border-color: #3498db;
                outline: none;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #64748b;
                margin-right: 8px;
            }
        """)
        self.fixed_class_combo.currentTextChanged.connect(self.load_fixed_for_class)
        class_layout.addWidget(self.fixed_class_combo)
        class_layout.addStretch()

        selector_layout.addWidget(class_frame)

        # Clear Fees button
        clear_fees_btn = QPushButton("🧹 Clear All Fees")
        clear_fees_btn.setCursor(Qt.PointingHandCursor)
        clear_fees_btn.setFixedHeight(38)
        clear_fees_btn.setFixedWidth(130)
        clear_fees_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 13px;
                font-weight: 500;
                padding: 0 10px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
            QPushButton:pressed {
                background-color: #b91c1c;
            }
        """)
        clear_fees_btn.clicked.connect(self.clear_all_fees)
        selector_layout.addWidget(clear_fees_btn)

        selector_layout.addStretch()
        layout.addWidget(selector_container)

        # Scroll area for fee categories
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #f1f5f9;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #94a3b8;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #64748b;
            }
        """)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(5, 5, 15, 5)
        scroll_layout.setSpacing(8)

        # Create fee rows with perfect spacing
        self.fee_widgets = []
        for i, category in enumerate(self.fee_categories):
            row_widget = QWidget()
            row_widget.setStyleSheet("""
                QWidget {
                    background-color: white;
                    border: 1px solid #e2e8f0;
                    border-radius: 5px;
                }
            """)
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(15, 12, 15, 12)
            row_layout.setSpacing(20)

            # Category label with fixed width for perfect alignment
            label = QLabel(category)
            label.setStyleSheet("""
                font-size: 14px;
                color: #1e293b;
                font-weight: 500;
                min-width: 140px;
            """)
            row_layout.addWidget(label)

            # Amount input with perfect size and alignment
            amount = QLineEdit("0")
            amount.setFixedWidth(180)
            amount.setFixedHeight(38)
            amount.setAlignment(Qt.AlignRight)
            amount.setStyleSheet("""
                QLineEdit {
                    border: 1px solid #cbd5e1;
                    border-radius: 5px;
                    padding: 0 12px;
                    font-size: 14px;
                    font-weight: 500;
                    background-color: white;
                    selection-background-color: #3498db;
                }
                QLineEdit:hover {
                    border-color: #94a3b8;
                }
                QLineEdit:focus {
                    border: 2px solid #3498db;
                    padding: 0 11px;
                }
            """)
            row_layout.addWidget(amount)

            # Add spacer to push everything left
            row_layout.addStretch()

            self.fee_widgets.append((category, amount))
            scroll_layout.addWidget(row_widget)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)

        # Save button with perfect centering
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 10, 0, 0)

        save_btn = QPushButton("Save Fixed Amounts")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setFixedWidth(200)
        save_btn.setFixedHeight(45)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 15px;
                font-weight: 600;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
        """)
        save_btn.clicked.connect(self.save_fixed_amounts)

        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addStretch()

        layout.addWidget(button_container)

        # Load first class
        if self.classes:
            self.load_fixed_for_class()

    def setup_payment_grid(self):
        """Tab for entering payments - Clean professional design"""
        layout = QVBoxLayout(self.grid_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title with Clear button
        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("📊 Enter Payments")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #2c3e50;
            padding: 0 0 10px 0;
        """)
        title_layout.addWidget(title)

        title_layout.addStretch()

        # Clear All Students button
        clear_students_btn = QPushButton("🧹 Clear All Students")
        clear_students_btn.setCursor(Qt.PointingHandCursor)
        clear_students_btn.setFixedHeight(36)
        clear_students_btn.setFixedWidth(150)
        clear_students_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 13px;
                font-weight: 500;
                padding: 0 10px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
            QPushButton:pressed {
                background-color: #b91c1c;
            }
        """)
        clear_students_btn.clicked.connect(self.clear_all_students)
        title_layout.addWidget(clear_students_btn)

        layout.addWidget(title_container)

        # Add bottom border after title
        border = QFrame()
        border.setFrameShape(QFrame.HLine)
        border.setStyleSheet("border: 1px solid #3498db; margin-bottom: 10px;")
        layout.addWidget(border)

        # Button bar - Clean buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # Button style
        button_style = """
            QPushButton {
                background-color: white;
                color: #334155;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #f8fafc;
                border-color: #94a3b8;
            }
            QPushButton:pressed {
                background-color: #f1f5f9;
            }
        """

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setStyleSheet(button_style)
        refresh_btn.clicked.connect(self.load_students)
        button_layout.addWidget(refresh_btn)

        add_btn = QPushButton("➕ Add Student")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet(button_style)
        add_btn.clicked.connect(self.add_student_dialog)
        button_layout.addWidget(add_btn)

        delete_btn = QPushButton("🗑 Delete")
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setStyleSheet(button_style)
        delete_btn.clicked.connect(self.delete_student)
        button_layout.addWidget(delete_btn)

        csv_btn = QPushButton("📥 CSV")
        csv_btn.setCursor(Qt.PointingHandCursor)
        csv_btn.setStyleSheet(button_style)
        csv_btn.clicked.connect(self.export_to_csv)
        button_layout.addWidget(csv_btn)

        print_btn = QPushButton("🖨️ Print")
        print_btn.setCursor(Qt.PointingHandCursor)
        print_btn.setStyleSheet(button_style)
        print_btn.clicked.connect(self.print_grid)
        button_layout.addWidget(print_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        # Create the grid
        self.create_payment_grid()
        layout.addWidget(self.table)

    def create_payment_grid(self):
        """Create the payment entry grid - Perfect typing experience"""
        total_cols = 2 + len(self.fee_categories) + 3
        self.table = QTableWidget()
        self.table.setColumnCount(total_cols)

        headers = ["Student Name", "Class"] + self.fee_categories + ["Expected", "Paid", "Outstanding"]
        self.table.setHorizontalHeaderLabels(headers)

        # Better table styling for typing
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e2e8f0;
                border-radius: 5px;
                font-size: 13px;
                gridline-color: #e2e8f0;
            }
            QTableWidget::item {
                padding: 8px 10px;
                color: #1e293b;
            }
            QTableWidget::item:selected {
                background-color: #e0f2fe;
                color: #0c4a6e;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                color: #334155;
                padding: 10px 8px;
                font-weight: 600;
                font-size: 13px;
                border: none;
                border-bottom: 2px solid #cbd5e1;
            }
            QTableWidget QLineEdit {
                border: 2px solid #3498db;
                border-radius: 3px;
                padding: 4px 6px;
                background-color: white;
                selection-background-color: #3498db;
            }
        """)

        # Set perfect column widths
        self.table.setColumnWidth(0, 200)  # Student Name
        self.table.setColumnWidth(1, 120)  # Class

        # Fee categories with proper widths
        fee_widths = [110, 100, 100, 100, 100, 100, 120, 140, 130]
        for i, width in enumerate(fee_widths):
            self.table.setColumnWidth(2 + i, width)

        self.table.setColumnWidth(2 + len(self.fee_categories), 100)  # Expected
        self.table.setColumnWidth(3 + len(self.fee_categories), 90)  # Paid
        self.table.setColumnWidth(4 + len(self.fee_categories), 100)  # Outstanding

        # Set row height for better typing
        self.table.verticalHeader().setDefaultSectionSize(45)

        self.table.setEditTriggers(
            QTableWidget.DoubleClicked |
            QTableWidget.EditKeyPressed |
            QTableWidget.AnyKeyPressed |
            QTableWidget.SelectedClicked
        )

        self.table.setSortingEnabled(True)
        self.table.cellChanged.connect(self.on_cell_changed)

    def load_fixed_amounts(self):
        """Load fixed amounts from database"""
        for class_name in self.classes:
            for category in self.fee_categories:
                self.c.execute('''
                    SELECT amount FROM fixed_fees 
                    WHERE class=? AND category=? AND term=?
                ''', (class_name, category, self.current_term))
                result = self.c.fetchone()
                if result:
                    self.fixed_amounts[class_name][category] = result[0]

    def load_fixed_for_class(self):
        """Load fixed amounts for selected class"""
        if not hasattr(self, 'fixed_class_combo') or not self.fixed_class_combo:
            return

        class_name = self.fixed_class_combo.currentText()

        for category, amount_input in self.fee_widgets:
            amount = self.fixed_amounts[class_name][category]
            amount_input.setText(f"{int(amount):,}")

    def save_fixed_amounts(self):
        """Save fixed amounts for current class"""
        class_name = self.fixed_class_combo.currentText()

        for category, amount_input in self.fee_widgets:
            try:
                amount_text = amount_input.text().replace(',', '').strip()
                amount = float(amount_text) if amount_text else 0
            except:
                amount = 0

            self.fixed_amounts[class_name][category] = amount

            self.c.execute('''
                INSERT OR REPLACE INTO fixed_fees (class, category, amount, term)
                VALUES (?, ?, ?, ?)
            ''', (class_name, category, amount, self.current_term))

        self.conn.commit()
        QMessageBox.information(self, "Success", f"Amounts saved for {class_name}")

    def load_students(self):
        """Load students into payment grid"""
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        self.table.setSortingEnabled(False)

        self.c.execute("SELECT id, name, class FROM students ORDER BY name")
        students = self.c.fetchall()

        for row, student in enumerate(students):
            self.table.insertRow(row)
            student_id, name, student_class = student

            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.UserRole, student_id)
            name_item.setFlags(name_item.flags() | Qt.ItemIsEditable)
            name_item.setForeground(QColor(44, 62, 80))
            self.table.setItem(row, 0, name_item)

            class_combo = QComboBox()
            class_combo.addItems(self.classes)
            class_combo.setCurrentText(student_class)
            class_combo.setStyleSheet("""
                QComboBox {
                    border: 1px solid #bdc3c7;
                    border-radius: 3px;
                    padding: 4px;
                    background-color: white;
                    color: #2c3e50;
                }
                QComboBox:hover {
                    border-color: #3498db;
                }
                QComboBox::drop-down {
                    border: none;
                }
                QComboBox::down-arrow {
                    image: none;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 4px solid #7f8c8d;
                    margin-right: 5px;
                }
            """)
            class_combo.currentTextChanged.connect(
                lambda text, r=row: self.on_class_changed(r, text)
            )
            self.table.setCellWidget(row, 1, class_combo)

            fixed = self.fixed_amounts.get(student_class, {})

            total_paid = 0
            for col, category in enumerate(self.fee_categories):
                self.c.execute('''
                    SELECT amount FROM payments 
                    WHERE student_id=? AND category=?
                ''', (student_id, category))
                result = self.c.fetchone()
                amount = result[0] if result else 0
                total_paid += amount

                amount_item = QTableWidgetItem(f"{int(amount):,}")
                amount_item.setData(Qt.UserRole + 1, category)
                amount_item.setFlags(amount_item.flags() | Qt.ItemIsEditable)
                amount_item.setForeground(QColor(44, 62, 80))
                amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row, 2 + col, amount_item)

            expected_total = sum(fixed.values())
            expected_item = QTableWidgetItem(f"{int(expected_total):,}")
            expected_item.setFlags(expected_item.flags() & ~Qt.ItemIsEditable)
            expected_item.setForeground(QColor(41, 128, 185))
            expected_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            expected_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 2 + len(self.fee_categories), expected_item)

            paid_item = QTableWidgetItem(f"{int(total_paid):,}")
            paid_item.setFlags(paid_item.flags() & ~Qt.ItemIsEditable)
            paid_item.setForeground(QColor(39, 174, 96))
            paid_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            paid_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 3 + len(self.fee_categories), paid_item)

            outstanding = expected_total - total_paid
            outstanding_item = QTableWidgetItem(f"{int(outstanding):,}")
            outstanding_item.setFlags(outstanding_item.flags() & ~Qt.ItemIsEditable)
            if outstanding > 0:
                outstanding_item.setForeground(QColor(192, 57, 43))
            else:
                outstanding_item.setForeground(QColor(39, 174, 96))
            outstanding_item.setFont(QFont("Segoe UI", 10, QFont.Bold))
            outstanding_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(row, 4 + len(self.fee_categories), outstanding_item)

        self.table.setSortingEnabled(True)
        self.table.blockSignals(False)

    def on_cell_changed(self, row, col):
        """Handle cell changes"""
        if self.table.signalsBlocked():
            return

        if col == 0:
            item = self.table.item(row, col)
            if item and item.text():
                student_id = item.data(Qt.UserRole)
                old_name = self.get_student_name(student_id)
                if student_id and old_name != item.text():
                    self.add_to_undo_stack("name_change", (student_id, old_name))
                    self.c.execute("UPDATE students SET name=? WHERE id=?",
                                   (item.text(), student_id))
                    self.conn.commit()

        elif 2 <= col < 2 + len(self.fee_categories):
            self.update_payment(row, col)

    def get_student_name(self, student_id):
        """Get student name by ID"""
        self.c.execute("SELECT name FROM students WHERE id=?", (student_id,))
        result = self.c.fetchone()
        return result[0] if result else ""

    def update_payment(self, row, col):
        """Update payment in database and recalculate"""
        name_item = self.table.item(row, 0)
        if not name_item or not name_item.text():
            return

        student_id = name_item.data(Qt.UserRole)
        if not student_id:
            return

        amount_item = self.table.item(row, col)
        if not amount_item:
            return

        category_index = col - 2
        category = self.fee_categories[category_index]

        self.c.execute('''
            SELECT amount FROM payments 
            WHERE student_id=? AND category=?
        ''', (student_id, category))
        result = self.c.fetchone()
        old_amount = result[0] if result else 0

        try:
            new_amount = float(amount_item.text().replace(',', '') or 0)
        except:
            new_amount = 0

        if old_amount != new_amount:
            self.add_to_undo_stack("payment_change", (student_id, category, old_amount))
            self.c.execute('''
                INSERT OR REPLACE INTO payments (student_id, category, amount)
                VALUES (?, ?, ?)
            ''', (student_id, category, new_amount))
            self.conn.commit()

        self.recalculate_row(row)

    def recalculate_row(self, row):
        """AUTOMATICALLY recalculate paid total and outstanding"""
        self.table.blockSignals(True)

        class_combo = self.table.cellWidget(row, 1)
        if not class_combo:
            return
        student_class = class_combo.currentText()

        fixed = self.fixed_amounts.get(student_class, {})
        expected_total = sum(fixed.values())

        total_paid = 0
        for col in range(2, 2 + len(self.fee_categories)):
            item = self.table.item(row, col)
            if item:
                try:
                    total_paid += float(item.text().replace(',', '') or 0)
                except:
                    pass

        expected_item = self.table.item(row, 2 + len(self.fee_categories))
        if expected_item:
            expected_item.setText(f"{int(expected_total):,}")

        paid_item = self.table.item(row, 3 + len(self.fee_categories))
        if paid_item:
            paid_item.setText(f"{int(total_paid):,}")

        outstanding = expected_total - total_paid
        outstanding_item = self.table.item(row, 4 + len(self.fee_categories))
        if outstanding_item:
            outstanding_item.setText(f"{int(outstanding):,}")
            if outstanding > 0:
                outstanding_item.setForeground(QColor(192, 57, 43))
            else:
                outstanding_item.setForeground(QColor(39, 174, 96))

        self.table.blockSignals(False)

    def on_class_changed(self, row, text):
        """Handle class change"""
        name_item = self.table.item(row, 0)
        if name_item and name_item.text():
            student_id = name_item.data(Qt.UserRole)
            if student_id:
                self.c.execute("SELECT class FROM students WHERE id=?", (student_id,))
                old_class = self.c.fetchone()[0]

                if old_class != text:
                    self.add_to_undo_stack("class_change", (student_id, old_class))
                    self.c.execute("UPDATE students SET class=? WHERE id=?",
                                   (text, student_id))
                    self.conn.commit()

                    fixed = self.fixed_amounts.get(text, {})
                    expected_total = sum(fixed.values())
                    expected_item = self.table.item(row, 2 + len(self.fee_categories))
                    if expected_item:
                        expected_item.setText(f"{int(expected_total):,}")

                    self.recalculate_row(row)

    def add_student_dialog(self):
        """Dialog to add new student"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Student")
        dialog.setFixedSize(450, 280)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                border: 1px solid #dde2e6;
            }
            QLabel {
                color: #2c3e50;
                font-size: 13px;
                font-weight: 600;
                padding: 2px 0;
            }
            QLineEdit, QComboBox {
                padding: 10px 12px;
                border: 1px solid #cbd5e0;
                border-radius: 6px;
                font-size: 13px;
                background-color: white;
                color: #1e293b;
                selection-background-color: #3498db;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #3498db;
                padding: 9px 11px;
            }
            QLineEdit:hover, QComboBox:hover {
                border-color: #94a3b8;
            }
            QLineEdit::placeholder {
                color: #94a3b8;
                font-style: italic;
            }
            QComboBox {
                background-color: white;
                color: #1e293b;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #64748b;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #cbd5e0;
                selection-background-color: #3498db;
                selection-color: white;
                color: #1e293b;
                outline: none;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        title = QLabel("➕ Add New Student")
        title.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
            padding-bottom: 10px;
            border-bottom: 2px solid #3498db;
            margin-bottom: 5px;
        """)
        layout.addWidget(title)

        layout.addWidget(QLabel("Student Name:"))
        name_input = QLineEdit()
        name_input.setPlaceholderText("Enter student's full name")
        name_input.setMinimumHeight(38)
        layout.addWidget(name_input)

        layout.addWidget(QLabel("Class:"))
        class_combo = QComboBox()
        class_combo.addItems(self.classes)
        class_combo.setCurrentText(self.classes[0])
        class_combo.setMinimumHeight(38)
        layout.addWidget(class_combo)

        layout.addStretch()

        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setMinimumWidth(120)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                color: #475569;
                border: 1px solid #cbd5e0;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
                border-color: #94a3b8;
            }
            QPushButton:pressed {
                background-color: #cbd5e0;
            }
        """)
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Add Student")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setMinimumHeight(40)
        save_btn.setMinimumWidth(120)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 600;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:pressed {
                background-color: #229954;
            }
        """)
        save_btn.clicked.connect(lambda: self.save_new_student(dialog, name_input, class_combo))
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

        dialog.exec()

    def save_new_student(self, dialog, name_input, class_combo):
        """Save new student"""
        name = name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Student name is required")
            return

        self.c.execute("INSERT INTO students (name, class) VALUES (?, ?)",
                       (name, class_combo.currentText()))
        self.conn.commit()

        student_id = self.c.lastrowid

        dialog.accept()

        self.add_to_undo_stack("add_student", student_id)

        self.load_students()


def main():
    app = QApplication(sys.argv)

    app.setStyle("Fusion")

    # Platform-specific font adjustments
    if IS_WINDOWS:
        default_font = QFont("Segoe UI", 9)
    else:
        default_font = QFont("Ubuntu", 9)

    app.setFont(default_font)

    # Professional grey color palette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(236, 240, 241))
    palette.setColor(QPalette.WindowText, QColor(44, 62, 80))
    palette.setColor(QPalette.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
    palette.setColor(QPalette.Text, QColor(44, 62, 80))
    palette.setColor(QPalette.Button, QColor(52, 73, 94))
    palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.Highlight, QColor(52, 152, 219))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)

    window = SchoolFeeManager()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()