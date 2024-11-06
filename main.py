import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QTextEdit, QLabel, QLineEdit, QFileDialog, QProgressBar, QSpinBox, QMenu, QToolButton, QFrame, QAction
)
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, Qt
from PyQt5.QtGui import QColor, QTextCharFormat, QTextCursor, QFont
import requests
from concurrent.futures import ThreadPoolExecutor
import webbrowser
import qdarkstyle
from better_proxy import Proxy


class ProxyCheckerThread(QThread):
    update_progress = pyqtSignal(int, int, int)  # checked, valid, invalid
    log_message = pyqtSignal(str, bool)  # message, is_valid

    def __init__(self, proxies, url, valid_output_file, invalid_output_file, num_threads):
        super().__init__()
        self.proxies = proxies
        self.url = url
        self.valid_output_file = valid_output_file
        self.invalid_output_file = invalid_output_file
        self.num_threads = num_threads
        self.valid_count = 0
        self.invalid_count = 0

    def run(self):
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            for proxy in self.proxies:
                executor.submit(self.check_proxy, proxy.strip())

    def check_proxy(self, proxy):
        try:
            response = requests.get(self.url, proxies=Proxy.from_str(proxy).as_proxies_dict, timeout=5)
            proxy = Proxy.from_str(proxy).as_url
            if response.status_code == 200:
                with open(self.valid_output_file, 'a') as f:
                    f.write(f"{proxy}\n")
                self.valid_count += 1
                self.log_message.emit(f"VALID, ip:{response.text}, {proxy}", True)
            else:
                self.invalid_count += 1
                with open(self.invalid_output_file, 'a') as f:
                    f.write(f"{proxy}\n")
                self.log_message.emit(f"INVALID: {proxy}", False)
        except Exception:
            self.invalid_count += 1
            with open(self.invalid_output_file, 'a') as f:
                f.write(f"{proxy}\n")
            self.log_message.emit(f"INVALID: {proxy}", False)
        finally:
            self.update_progress.emit(1, self.valid_count, self.invalid_count)


class ProxyCheckerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Proxy Checker')
        self.setGeometry(100, 100, 900, 700)

        # Main widget and layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # Menu button
        self.menu_button = QToolButton(self)
        self.menu_button.setText("Menu")
        self.menu_button.setFont(QFont("Arial", 12))
        self.menu_button.setPopupMode(QToolButton.InstantPopup)
        self.create_menu()
        layout.addWidget(self.menu_button)

        # Instruction
        instruction_frame = QFrame(self)
        instruction_layout = QVBoxLayout(instruction_frame)
        instruction_frame.setFrameShape(QFrame.StyledPanel)
        instruction_label = QLabel('Load proxies in the format:', instruction_frame)
        instruction_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        format_label = QLabel('host:port:login:password\n'
                              'host:port@login:password\n'
                              'host:port|login:password\n'
                              'login:password@host:port\n'
                              'login:password:host:port\n'
                              'host:port', instruction_frame)
        format_label.setFont(QFont("Arial", 12))
        instruction_layout.addWidget(instruction_label)
        instruction_layout.addWidget(format_label)
        layout.addWidget(instruction_frame)

        # URL to test
        url_label = QLabel('URL to Test:', self)
        url_label.setFont(QFont("Arial", 12))
        url_input = QLineEdit(self)
        url_input.setFont(QFont("Arial", 12))
        url_input.setText('https://api.botprod.ru/ip')
        layout.addWidget(url_label)
        layout.addWidget(url_input)

        # Input proxy list file
        input_file_label = QLabel('Input Proxy List File:', self)
        input_file_label.setFont(QFont("Arial", 12))
        input_file_input = QLineEdit(self)
        input_file_input.setFont(QFont("Arial", 12))
        input_file_button = QPushButton('Select', self)
        input_file_button.setFont(QFont("Arial", 12))
        input_file_button.clicked.connect(self.select_input_file)
        input_file_layout = QHBoxLayout()
        input_file_layout.addWidget(input_file_input)
        input_file_layout.addWidget(input_file_button)
        layout.addWidget(input_file_label)
        layout.addLayout(input_file_layout)

        # Output file for valid proxies
        output_file_label = QLabel('Output File for Valid Proxies:', self)
        output_file_label.setFont(QFont("Arial", 12))
        output_file_input = QLineEdit(self)
        output_file_input.setFont(QFont("Arial", 12))
        output_file_button = QPushButton('Select', self)
        output_file_button.setFont(QFont("Arial", 12))
        output_file_button.clicked.connect(self.select_output_file)
        output_file_layout = QHBoxLayout()
        output_file_layout.addWidget(output_file_input)
        output_file_layout.addWidget(output_file_button)
        layout.addWidget(output_file_label)
        layout.addLayout(output_file_layout)

        # Output file for invalid proxies
        invalid_output_file_label = QLabel('Output File for Invalid Proxies:', self)
        invalid_output_file_label.setFont(QFont("Arial", 12))
        invalid_output_file_input = QLineEdit(self)
        invalid_output_file_input.setFont(QFont("Arial", 12))
        invalid_output_file_button = QPushButton('Select', self)
        invalid_output_file_button.setFont(QFont("Arial", 12))
        invalid_output_file_button.clicked.connect(self.select_invalid_output_file)
        invalid_output_file_layout = QHBoxLayout()
        invalid_output_file_layout.addWidget(invalid_output_file_input)
        invalid_output_file_layout.addWidget(invalid_output_file_button)
        layout.addWidget(invalid_output_file_label)
        layout.addLayout(invalid_output_file_layout)

        # Number of threads
        threads_label = QLabel('Number of Threads:', self)
        threads_label.setFont(QFont("Arial", 12))
        self.threads_input = QSpinBox(self)
        self.threads_input.setFont(QFont("Arial", 12))
        self.threads_input.setValue(10)
        layout.addWidget(threads_label)
        layout.addWidget(self.threads_input)

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setFont(QFont("Arial", 12))
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel('Waiting to start...', self)
        self.status_label.setFont(QFont("Arial", 12))
        layout.addWidget(self.status_label)

        # Log output
        self.log_output = QTextEdit(self)
        self.log_output.setFont(QFont("Arial", 12))
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        # Start button
        self.start_button = QPushButton('Start Checking', self)
        self.start_button.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(self.start_button)
        self.start_button.clicked.connect(self.start_checking)

        # Set dark style
        self.setStyleSheet(qdarkstyle.load_stylesheet())

    def create_menu(self):
        # Меню
        menu = QMenu(self)
        app_name_action = QAction("Proxy Checker", self)
        app_name_action.setDisabled(True)
        menu.addAction(app_name_action)
        menu.addSeparator()
        channel_action = QAction("Visit Channel", self)
        channel_action.triggered.connect(self.open_channel)
        menu.addAction(channel_action)
        self.menu_button.setMenu(menu)

    def open_channel(self):
        webbrowser.open("https://t.me/botpr0d")

    def select_input_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Proxy List File")
        if file_name:
            self.input_file_input.setText(file_name)

    def select_output_file(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Select Output File for Good Proxies", "",
                                                   "Text Files (*.txt);;All Files (*)")
        if file_name:
            self.output_file_input.setText(file_name)

    def select_invalid_output_file(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Select Output File for Invalid Proxies", "",
                                                   "Text Files (*.txt);;All Files (*)")
        if file_name:
            self.invalid_output_file_input.setText(file_name)

    def start_checking(self):
        input_file = self.input_file_input.text()
        valid_output_file = self.output_file_input.text()
        invalid_output_file = self.invalid_output_file_input.text()
        url = self.url_input.text()
        num_threads = self.threads_input.value()

        if not input_file or not valid_output_file or not invalid_output_file or not url:
            self.status_label.setText("Please fill in all fields!")
            return

        with open(input_file, 'r') as f:
            proxies = f.readlines()

        self.total_proxies = len(proxies)
        self.checked_proxies = 0
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting...")
        self.thread = ProxyCheckerThread(proxies, url, valid_output_file, invalid_output_file, num_threads)
        self.thread.update_progress.connect(self.update_progress)
        self.thread.log_message.connect(self.log_message)
        self.thread.start()

    @pyqtSlot(int, int, int)
    def update_progress(self, checked, valid, invalid):
        self.checked_proxies += checked
        progress = int((self.checked_proxies / self.total_proxies) * 100)
        self.progress_bar.setValue(progress)
        self.status_label.setText(f"Valid: {valid} | Invalid: {invalid}")

    @pyqtSlot(str, bool)
    def log_message(self, message, is_valid):
        format = QTextCharFormat()
        format.setForeground(QColor("green" if is_valid else "red"))
        self.log_output.moveCursor(QTextCursor.End)
        self.log_output.setCurrentCharFormat(format)
        self.log_output.insertPlainText(message + "\n")
        self.log_output.moveCursor(QTextCursor.End)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = ProxyCheckerApp()
    ex.show()
    sys.exit(app.exec_())
