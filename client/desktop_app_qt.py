"""PyQt6 Desktop Client for File Share Network.

Features:
- Login (HTTP)
- List files (HTTP)
- Upload/Download via TCP (optional SSL)
- Search via gRPC
- Listen to multicast radio stream
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from typing import Any, Callable, Dict, List, Tuple

import httpx
import grpc
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QFileDialog,
)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from client.tcp_client import TCPFileClient
from client.multicast_client import MulticastRadioClient
from app.grpc_files import file_search_pb2, file_search_pb2_grpc


class Worker(QThread):
    result = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, fn: Callable, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            res = self.fn(*self.args, **self.kwargs)
            self.result.emit(res)
        except Exception as exc:
            self.error.emit(str(exc))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Share Network - Desktop Client (PyQt6)")
        self.resize(1100, 720)

        self.token: str | None = None
        self.user_info: Dict[str, Any] | None = None
        self.files_cache: List[Dict[str, Any]] = []
        self._workers: List[Worker] = []
        self._radio_client: MulticastRadioClient | None = None
        self._radio_worker: Worker | None = None

        self._build_ui()

    # ------------------------------ UI ------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)

        # Header
        header = QGroupBox("Connection & Login")
        header_layout = QGridLayout(header)

        self.host_input = QLineEdit("localhost")
        self.http_port_input = QLineEdit("8000")
        self.tcp_port_input = QLineEdit("9000")
        self.tcp_ssl_port_input = QLineEdit("9001")
        self.grpc_port_input = QLineEdit("50051")
        self.ssl_checkbox = QCheckBox("Use SSL (TCP)")

        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.login)

        header_layout.addWidget(QLabel("Host"), 0, 0)
        header_layout.addWidget(self.host_input, 0, 1)
        header_layout.addWidget(QLabel("HTTP"), 0, 2)
        header_layout.addWidget(self.http_port_input, 0, 3)
        header_layout.addWidget(QLabel("TCP"), 0, 4)
        header_layout.addWidget(self.tcp_port_input, 0, 5)
        header_layout.addWidget(QLabel("TCP SSL"), 0, 6)
        header_layout.addWidget(self.tcp_ssl_port_input, 0, 7)
        header_layout.addWidget(QLabel("gRPC"), 0, 8)
        header_layout.addWidget(self.grpc_port_input, 0, 9)
        header_layout.addWidget(self.ssl_checkbox, 0, 10)

        header_layout.addWidget(QLabel("Username"), 1, 0)
        header_layout.addWidget(self.username_input, 1, 1, 1, 3)
        header_layout.addWidget(QLabel("Password"), 1, 4)
        header_layout.addWidget(self.password_input, 1, 5, 1, 3)
        header_layout.addWidget(self.login_btn, 1, 9, 1, 2)

        root_layout.addWidget(header)

        # Tabs
        tabs = QTabWidget()
        root_layout.addWidget(tabs)

        self.files_tab = QWidget()
        self.search_tab = QWidget()
        self.radio_tab = QWidget()
        tabs.addTab(self.files_tab, "Files")
        tabs.addTab(self.search_tab, "Search")
        tabs.addTab(self.radio_tab, "Radio")

        self._build_files_tab()
        self._build_search_tab()
        self._build_radio_tab()

        # Status bar
        self.status_label = QLabel("Not logged in")
        root_layout.addWidget(self.status_label)

    def _build_files_tab(self):
        layout = QVBoxLayout(self.files_tab)

        toolbar = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_files)
        upload_btn = QPushButton("Upload (TCP)")
        upload_btn.clicked.connect(self.upload_file)
        download_btn = QPushButton("Download (TCP)")
        download_btn.clicked.connect(self.download_file)
        toolbar.addWidget(refresh_btn)
        toolbar.addWidget(upload_btn)
        toolbar.addWidget(download_btn)
        toolbar.addStretch()

        layout.addLayout(toolbar)

        self.files_table = QTableWidget(0, 5)
        self.files_table.setHorizontalHeaderLabels(["ID", "Original Name", "Size (KB)", "Owner", "Public"])
        self.files_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.files_table)

    def _build_search_tab(self):
        layout = QVBoxLayout(self.search_tab)

        row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter keyword")
        search_btn = QPushButton("Search (gRPC)")
        search_btn.clicked.connect(self.search_files)
        row.addWidget(self.search_input)
        row.addWidget(search_btn)
        layout.addLayout(row)

        self.search_output = QTextEdit()
        self.search_output.setReadOnly(True)
        layout.addWidget(self.search_output)

    def _build_radio_tab(self):
        layout = QVBoxLayout(self.radio_tab)

        form = QFormLayout()
        self.radio_group_input = QLineEdit("224.1.1.1")
        self.radio_port_input = QLineEdit("5007")
        self.radio_duration_input = QSpinBox()
        self.radio_duration_input.setRange(5, 3600)
        self.radio_duration_input.setValue(30)
        self.radio_play_checkbox = QCheckBox("Play live audio")
        self.radio_play_checkbox.setChecked(True)
        self.radio_save_checkbox = QCheckBox("Save to file")

        form.addRow("Group", self.radio_group_input)
        form.addRow("Port", self.radio_port_input)
        form.addRow("Duration (s)", self.radio_duration_input)
        form.addRow(self.radio_play_checkbox, self.radio_save_checkbox)

        layout.addLayout(form)

        listen_btn = QPushButton("Start Listening")
        listen_btn.clicked.connect(self.start_radio)
        layout.addWidget(listen_btn)

        self.radio_stop_btn = QPushButton("Stop Listening")
        self.radio_stop_btn.setEnabled(False)
        self.radio_stop_btn.clicked.connect(self.stop_radio)
        layout.addWidget(self.radio_stop_btn)

        self.radio_log = QTextEdit()
        self.radio_log.setReadOnly(True)
        layout.addWidget(self.radio_log)

    # ------------------------------ Helpers ------------------------------
    def _api_base(self) -> str:
        host = self.host_input.text().strip()
        port = self.http_port_input.text().strip()
        return f"http://{host}:{port}"

    def _tcp_config(self) -> Tuple[str, int, bool]:
        host = self.host_input.text().strip()
        use_ssl = self.ssl_checkbox.isChecked()
        port = int(self.tcp_ssl_port_input.text()) if use_ssl else int(self.tcp_port_input.text())
        return host, port, use_ssl

    def _grpc_target(self) -> str:
        host = self.host_input.text().strip()
        port = self.grpc_port_input.text().strip()
        return f"{host}:{port}"

    def _set_status(self, text: str):
        self.status_label.setText(text)

    def _show_error(self, title: str, message: str):
        QMessageBox.critical(self, title, message)

    def _start_worker(self, worker: Worker, on_result: Callable | None = None, on_error: Callable | None = None):
        """Start worker and keep reference to prevent premature GC."""
        self._workers.append(worker)

        if on_result:
            worker.result.connect(on_result)
        if on_error:
            worker.error.connect(on_error)

        def _cleanup():
            if worker in self._workers:
                self._workers.remove(worker)
            worker.deleteLater()

        worker.finished.connect(_cleanup)
        worker.start()

    def _require_login(self) -> bool:
        if not self.token:
            QMessageBox.warning(self, "Login", "Please login first")
            return False
        return True

    # ------------------------------ Actions ------------------------------
    def login(self):
        if self.token:
            self.logout()
            return

        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        if not username or not password:
            QMessageBox.warning(self, "Login", "Enter username and password")
            return

        def do_login():
            url = f"{self._api_base()}/api/v1/auth/login"
            resp = httpx.post(url, json={"username": username, "password": password}, timeout=10)
            data = resp.json()
            if resp.status_code != 200:
                raise RuntimeError(data.get("detail", "Login failed"))
            if not data.get("success"):
                raise RuntimeError(data.get("message", "Login failed"))
            return data["data"]

        worker = Worker(do_login)
        self._start_worker(
            worker,
            on_result=self._on_login_success,
            on_error=lambda e: self._show_error("Login", e)
        )

    def _on_login_success(self, payload: Dict[str, Any]):
        self.token = payload.get("access_token")
        self.user_info = payload.get("user")
        username = self.user_info.get("username") if self.user_info else "user"
        self._set_status(f"Logged in as {username}")
        self.login_btn.setText("Logout")

    def logout(self):
        self.token = None
        self.user_info = None
        self.files_cache = []
        self.files_table.setRowCount(0)
        self._set_status("Not logged in")
        self.login_btn.setText("Login")

    def refresh_files(self):
        if not self._require_login():
            return

        def do_fetch():
            url = f"{self._api_base()}/api/v1/files/"
            headers = {"Authorization": f"Bearer {self.token}"}
            resp = httpx.get(url, headers=headers, timeout=10)
            data = resp.json()
            if resp.status_code != 200:
                raise RuntimeError(data.get("detail", "Failed to fetch files"))
            if not data.get("success"):
                raise RuntimeError(data.get("message", "Failed to fetch files"))
            return data.get("data", [])

        worker = Worker(do_fetch)
        self._start_worker(
            worker,
            on_result=self._render_files,
            on_error=lambda e: self._show_error("Files", e)
        )

    def _render_files(self, files: List[Dict[str, Any]]):
        self.files_cache = files
        self.files_table.setRowCount(0)
        for f in files:
            row = self.files_table.rowCount()
            self.files_table.insertRow(row)
            size_kb = float(f.get("file_size", 0)) / 1024
            self.files_table.setItem(row, 0, QTableWidgetItem(str(f.get("id"))))
            self.files_table.setItem(row, 1, QTableWidgetItem(f.get("original_filename", "")))
            self.files_table.setItem(row, 2, QTableWidgetItem(f"{size_kb:.1f}"))
            self.files_table.setItem(row, 3, QTableWidgetItem(str(f.get("owner_id"))))
            self.files_table.setItem(row, 4, QTableWidgetItem("Yes" if f.get("is_public") else "No"))

    def upload_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select file to upload")
        if not path:
            return

        def do_upload():
            host, port, use_ssl = self._tcp_config()
            client = TCPFileClient(host=host, port=port, use_ssl=use_ssl)
            if not client.connect():
                raise RuntimeError("Cannot connect to TCP server")
            ok = client.upload_file(path)
            client.close()
            if not ok:
                raise RuntimeError("Upload failed")
            # Register metadata via HTTP so file appears in list
            filename = os.path.basename(path)
            file_size = os.path.getsize(path)
            file_ext = os.path.splitext(filename)[1].lower()
            url = f"{self._api_base()}/api/v1/files/register"
            headers = {"Authorization": f"Bearer {self.token}"}
            payload = {
                "filename": filename,
                "original_filename": filename,
                "file_size": file_size,
                "description": "",
                "is_public": False,
            }
            resp = httpx.post(url, headers=headers, json=payload, timeout=10)
            if resp.status_code != 200:
                try:
                    detail = resp.json().get("detail", resp.text)
                except Exception:
                    detail = resp.text
                raise RuntimeError(f"Register failed: {detail}")
            return filename

        worker = Worker(do_upload)
        self._start_worker(
            worker,
            on_result=lambda name: (
                self._set_status(f"Uploaded: {name}"),
                QMessageBox.information(self, "Upload", f"Upload thành công: {name}"),
                self.refresh_files(),
            ),
            on_error=lambda e: self._show_error("Upload", e)
        )

    def download_file(self):
        row = self.files_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Download", "Select a file first")
            return

        file_item = self.files_cache[row]
        filename_on_server = file_item.get("filename")
        original_name = file_item.get("original_filename", "downloaded_file")

        save_path, _ = QFileDialog.getSaveFileName(self, "Save file", original_name)
        if not save_path:
            return

        def do_download():
            host, port, use_ssl = self._tcp_config()
            client = TCPFileClient(host=host, port=port, use_ssl=use_ssl)
            if not client.connect():
                raise RuntimeError("Cannot connect to TCP server")
            ok = client.download_file(filename_on_server, save_path)
            client.close()
            if not ok:
                raise RuntimeError("Download failed")
            return save_path

        worker = Worker(do_download)
        self._start_worker(
            worker,
            on_result=lambda p: (
                self._set_status(f"Downloaded: {p}"),
                QMessageBox.information(self, "Download", f"Download thành công: {p}"),
            ),
            on_error=lambda e: self._show_error("Download", e)
        )

    def search_files(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "Search", "Enter a keyword")
            return

        def do_search():
            channel = grpc.insecure_channel(self._grpc_target())
            stub = file_search_pb2_grpc.FileSearchServiceStub(channel)
            req = file_search_pb2.SearchRequest(keyword=keyword, limit=20)
            resp = stub.SearchFiles(req)
            return resp

        worker = Worker(do_search)
        self._start_worker(
            worker,
            on_result=self._render_search,
            on_error=lambda e: self._show_error("Search", e)
        )

    def _render_search(self, resp):
        self.search_output.clear()
        self.search_output.append(f"Found {resp.total_count} result(s)\n")
        for f in resp.files:
            self.search_output.append(
                f"- {f.original_filename} | ID: {f.id} | Size: {f.file_size/1024:.1f} KB | Owner: {f.owner_username}"
            )

    def start_radio(self):
        if self._radio_worker is not None:
            QMessageBox.information(self, "Radio", "Radio is already running")
            return

        group = self.radio_group_input.text().strip()
        port = int(self.radio_port_input.text().strip())
        duration = int(self.radio_duration_input.value())

        save_path = None
        if self.radio_save_checkbox.isChecked():
            save_path, _ = QFileDialog.getSaveFileName(self, "Save stream to file", "received_stream.wav")
            if save_path == "":
                save_path = None

        client = MulticastRadioClient(group=group, port=port)
        self._radio_client = client

        def do_listen():
            with client:
                client.receive_stream(
                    save_to_file=save_path,
                    duration_seconds=duration,
                    play_audio=self.radio_play_checkbox.isChecked(),
                )
            return save_path or "(no file)"

        self.radio_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] Listening {group}:{port} for {duration}s...\n")
        worker = Worker(do_listen)
        self._radio_worker = worker
        self.radio_stop_btn.setEnabled(True)
        self._start_worker(
            worker,
            on_result=lambda p: (self.radio_log.append(f"Done. Saved: {p}\n"), self._radio_cleanup()),
            on_error=lambda e: (self._show_error("Radio", e), self._radio_cleanup()),
        )

    def stop_radio(self):
        if self._radio_client is None:
            return
        self.radio_log.append(f"[{datetime.now().strftime('%H:%M:%S')}] Stopping radio...\n")
        try:
            self._radio_client.running = False
            self._radio_client.leave_group()
        except Exception:
            pass
        self._radio_cleanup()

    def _radio_cleanup(self):
        self._radio_client = None
        self._radio_worker = None
        self.radio_stop_btn.setEnabled(False)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
