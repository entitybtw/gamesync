import sys
import os
import subprocess
import shutil
import json
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTabWidget, QFileDialog, QProgressBar,
    QMessageBox, QHBoxLayout, QDialog, QListWidget, QDialogButtonBox,
    QInputDialog
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
import qdarkstyle

def get_available_themes(themes_dir="themes"):
    if not os.path.exists(themes_dir):
        return []
    files = os.listdir(themes_dir)
    themes = [os.path.splitext(f)[0] for f in files if f.endswith(".qss")]
    themes.sort()
    return themes

CONFIG_FILE = "config.json"
MOUNT_POINT = "/mnt/gamesync"

class PasswordDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enter sudo password")
        self.setModal(True)
        self.password = None

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Enter password for sudo:"))
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.pass_input)

        btn = QPushButton("OK")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

        self.setLayout(layout)

    def accept(self):
        self.password = self.pass_input.text()
        super().accept()

class SelectGameDialog(QDialog):
    def __init__(self, games_list, parent=None):
        themes = get_available_themes()
        super().__init__(parent)
        self.setWindowTitle("Select a game to download")
        self.setModal(True)
        self.selected_game = None

        layout = QVBoxLayout()
        self.list_widget = QListWidget()
        self.list_widget.addItems(games_list)
        layout.addWidget(self.list_widget)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def accept(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Error", "Select a game from the list")
            return
        self.selected_game = selected_items[0].text()
        super().accept()

class SettingsTab(QWidget):
    def __init__(self):
        super().__init__()
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.setSpacing(2)
        main_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("<h2>NAS Settings</h2>")
        main_layout.addWidget(title)

        def make_row(label_text, widget):
            row = QHBoxLayout()
            label = QLabel(label_text)
            label.setFixedWidth(100)
            row.addWidget(label)
            row.addWidget(widget)
            return row

        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("NAS IP address")
        main_layout.addLayout(make_row("NAS IP", self.ip_input))

        self.share_input = QLineEdit()
        self.share_input.setPlaceholderText("Share path")
        main_layout.addLayout(make_row("NAS Path", self.share_input))

        self.protocol_combo = QComboBox()
        self.protocol_combo.addItems(["nfs", "smb"])
        main_layout.addLayout(make_row("Protocol", self.protocol_combo))

        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("User")
        main_layout.addLayout(make_row("User", self.user_input))

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        main_layout.addLayout(make_row("Password", self.pass_input))

        self.mount_btn = QPushButton("Mount NAS")
        main_layout.addWidget(self.mount_btn)

        self.umount_btn = QPushButton("Unmount NAS")
        main_layout.addWidget(self.umount_btn)

        self.status_label = QLabel("Status: not mounted")
        main_layout.addWidget(self.status_label)

        title = QLabel("<h2>Appearance</h2>")
        main_layout.addWidget(title)

        self.theme_combo = QComboBox()
        themes = get_available_themes()
        self.theme_combo.addItems(themes)
        main_layout.addLayout(make_row("Theme", self.theme_combo))

        self.apply_theme_btn = QPushButton("Apply Theme")
        main_layout.addWidget(self.apply_theme_btn)
        self.apply_theme_btn.clicked.connect(self.apply_theme)

        self.save_btn = QPushButton("Save Settings")
        main_layout.addWidget(self.save_btn)
        self.mount_btn.clicked.connect(self.mount_share)
        self.umount_btn.clicked.connect(self.umount_share)
        self.save_btn.clicked.connect(self.save_settings)
        self.load_settings()

        self.setLayout(main_layout)
        
    def apply_theme(self):
        theme_name = self.theme_combo.currentText()
        theme_path = os.path.join("themes", f"{theme_name}.qss")
        if os.path.exists(theme_path):
            with open(theme_path, "r") as f:
                qss = f.read()
            QApplication.instance().setStyleSheet(qss)
        else:
            QMessageBox.warning(self, "Error", f"Theme file {theme_path} not found")

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
                self.ip_input.setText(cfg.get("ip", ""))
                self.share_input.setText(cfg.get("share", ""))
                self.protocol_combo.setCurrentText(cfg.get("protocol", "nfs"))
                self.user_input.setText(cfg.get("user", ""))
                self.pass_input.setText(cfg.get("password", ""))
                theme = cfg.get("theme", "")
                if theme and theme in [self.theme_combo.itemText(i) for i in range(self.theme_combo.count())]:
                    self.theme_combo.setCurrentText(theme)
                    self.apply_theme()

    def save_settings(self):
        cfg = {
            "ip": self.ip_input.text(),
            "share": self.share_input.text(),
            "protocol": self.protocol_combo.currentText(),
            "user": self.user_input.text(),
            "password": self.pass_input.text(),
            "theme": self.theme_combo.currentText()
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=4)
        QMessageBox.information(self, "Settings", "Saved")

    def ask_sudo_password(self):
        dlg = PasswordDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.password:
            return dlg.password
        else:
            QMessageBox.warning(self, "Cancel", "Password not entered")
            return None

    def run_sudo_cmd(self, cmd, sudo_pass):
        proc = subprocess.Popen(["sudo", "-S"] + cmd,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)
        out, err = proc.communicate(sudo_pass + "\n")
        return proc.returncode, out, err

    def mount_share(self):
        ip = self.ip_input.text().strip()
        share = self.share_input.text().strip()
        protocol = self.protocol_combo.currentText()
        user = self.user_input.text().strip()
        password = self.pass_input.text().strip()

        if not ip or not share:
            QMessageBox.warning(self, "Error", "IP and share path are required")
            return

        sudo_pass = self.ask_sudo_password()
        if not sudo_pass:
            return

        if not os.path.exists(MOUNT_POINT):
            ret, out, err = self.run_sudo_cmd(["mkdir", "-p", MOUNT_POINT], sudo_pass)
            if ret != 0:
                QMessageBox.critical(self, "Error", f"Cannot create mount point:\n{err}")
                return

        if protocol == "nfs":
            target = f"{ip}:{share}"
            cmd = ["mount", "-t", "nfs", target, MOUNT_POINT]
        elif protocol == "smb":
            options = f"rw"
            if user:
                options += f",username={user}"
            if password:
                options += f",password={password}"
            target = f"//{ip}/{share}"
            cmd = ["mount", "-t", "cifs", target, MOUNT_POINT, "-o", options]
        else:
            QMessageBox.warning(self, "Error", "Protocol not supported")
            return

        ret, out, err = self.run_sudo_cmd(cmd, sudo_pass)
        if ret == 0:
            self.status_label.setText(f"Status: mounted at {MOUNT_POINT}")
            QMessageBox.information(self, "Done", "NAS mounted")
        else:
            self.status_label.setText(f"Mount error:\n{err}")
            QMessageBox.critical(self, "Error", f"Mount failed:\n{err}")

    def umount_share(self):
        if not os.path.ismount(MOUNT_POINT):
            QMessageBox.information(self, "Info", "Mount point is not mounted")
            return

        sudo_pass = self.ask_sudo_password()
        if not sudo_pass:
            return

        ret, out, err = self.run_sudo_cmd(["umount", MOUNT_POINT], sudo_pass)
        if ret == 0:
            self.status_label.setText("Status: unmounted")
            QMessageBox.information(self, "Done", "Mount point successfully unmounted")
        else:
            self.status_label.setText(f"Unmount error:\n{err}")
            QMessageBox.critical(self, "Error", f"Unmount failed:\n{err}")

class MainTab(QWidget):
    def __init__(self, settings_tab):
        super().__init__()
        self.settings_tab = settings_tab
        self.layout = QVBoxLayout()
        self.layout.setSpacing(4)

        title = QLabel("GameSync")
        title.setFont(QFont("Arial", 20))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(title)

        path_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Select a folder for upload/download...")
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_folder)
        path_layout.addWidget(self.path_input)
        path_layout.addWidget(browse_btn)
        self.layout.addLayout(path_layout)

        btn_layout = QHBoxLayout()
        upload_btn = QPushButton("⬆ Upload to NAS")
        upload_btn.clicked.connect(self.upload_game)
        download_btn = QPushButton("⬇ Download from NAS")
        download_btn.clicked.connect(self.download_game)
        manage_btn = QPushButton("🛠 Manage NAS")
        manage_btn.clicked.connect(self.open_manage_dialog)
        btn_layout.addWidget(manage_btn)
        btn_layout.addWidget(upload_btn)
        btn_layout.addWidget(download_btn)
        self.layout.addLayout(btn_layout)

        self.progress = QProgressBar()
        self.layout.addWidget(self.progress)

        self.setLayout(self.layout)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select folder")
        if folder:
            self.path_input.setText(folder)

    def upload_game(self):
        src = self.path_input.text().strip()
        if not src or not os.path.exists(src):
            QMessageBox.warning(self, "Error", "Select a valid game folder")
            return
        if not os.path.ismount(MOUNT_POINT):
            QMessageBox.warning(self, "Error", f"NAS not mounted at {MOUNT_POINT}")
            return

        sudo_pass = self.settings_tab.ask_sudo_password()
        if not sudo_pass:
            return

        dest = os.path.join(MOUNT_POINT, os.path.basename(src))
        self.copy_dir(src, dest)

    def download_game(self):
        if not os.path.ismount(MOUNT_POINT):
            self.settings_tab.mount_share()
            if not os.path.ismount(MOUNT_POINT):
                return

        try:
            games = [d for d in os.listdir(MOUNT_POINT) if os.path.isdir(os.path.join(MOUNT_POINT, d))]
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot get list of games:\n{e}")
            return

        if not games:
            QMessageBox.information(self, "Info", "No games available on NAS")
            return

        dlg = SelectGameDialog(games, self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.selected_game:
            selected_game = dlg.selected_game
            dest = QFileDialog.getExistingDirectory(self, "Select folder for download")
            if not dest:
                return
            src = os.path.join(MOUNT_POINT, selected_game)
            self.copy_dir(src, os.path.join(dest, selected_game))

    def open_manage_dialog(self):
        if not os.path.ismount(MOUNT_POINT):
            self.settings_tab.mount_share()
            if not os.path.ismount(MOUNT_POINT):
                return
        dlg = ManageNASDialog(self)
        dlg.exec()

    def copy_dir(self, src, dest):
        if os.path.exists(dest):
            reply = QMessageBox.question(
                self, "Confirmation",
                f"Folder {dest} already exists. Replace?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            try:
                shutil.rmtree(dest)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Cannot delete folder: {e}")
                return
        try:
            total_files = sum(len(files) for _, _, files in os.walk(src))
            copied_files = 0
            for root, dirs, files in os.walk(src):
                rel_path = os.path.relpath(root, src)
                target_root = os.path.join(dest, rel_path)
                os.makedirs(target_root, exist_ok=True)
                for file in files:
                    src_file = os.path.join(root, file)
                    dst_file = os.path.join(target_root, file)
                    shutil.copy2(src_file, dst_file)
                    copied_files += 1
                    progress = int(copied_files / total_files * 100)
                    self.progress.setValue(progress)
            self.progress.setValue(100)
            QMessageBox.information(self, "Done", "Operation completed")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Copy error: {e}")

class GameSyncApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎮 GameSync")
        self.setMinimumSize(600, 400)

        self.tabs = QTabWidget()
        self.settings_tab = SettingsTab()
        self.main_tab = MainTab(self.settings_tab)

        self.tabs.addTab(self.main_tab, "Main")
        self.tabs.addTab(self.settings_tab, "Settings")

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)

class ManageNASDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage files on NAS")
        self.setMinimumSize(400, 300)

        layout = QVBoxLayout()
        self.file_list = QListWidget()
        layout.addWidget(self.file_list)

        btn_layout = QHBoxLayout()
        self.rename_btn = QPushButton("Rename")
        self.delete_btn = QPushButton("Delete")
        btn_layout.addWidget(self.rename_btn)
        btn_layout.addWidget(self.delete_btn)
        layout.addLayout(btn_layout)
        self.setLayout(layout)


    def delete_item(self):
        item = self.file_list.currentItem()
        if not item:
            return
        name = item.text()
        full_path = os.path.join(MOUNT_POINT, name)
        reply = QMessageBox.question(self, "Удаление", f"Удалить {name}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if os.path.isdir(full_path):
                    shutil.rmtree(full_path)
                else:
                    os.remove(full_path)
                self.load_files()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка удаления:\n{e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt6())
    window = GameSyncApp()
    window.show()
    sys.exit(app.exec())