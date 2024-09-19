import asyncio
import base64
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QPushButton, QTextEdit,
                             QWidget, QLabel, QLineEdit, QFileDialog)
from PyQt6.QtCore import QThread, pyqtSignal


class ClientThread(QThread):
    message_signal = pyqtSignal(str)
    image_signal = pyqtSignal(bytes)

    def __init__(self, host, port, name):
        super().__init__()
        self.host = host
        self.port = port
        self.name = name
        self.writer = None

    async def start_client(self):
        try:
            reader, writer = await asyncio.open_connection(self.host, self.port)
            self.writer = writer
            writer.write(self.name.encode())
            await writer.drain()

            while True:
                data = await reader.read(4096)
                if not data:
                    break

                message = data.decode()
                if message.startswith("IMAGE_MSG:"):
                    image_data = base64.b64decode(message[len("IMAGE_MSG:"):])
                    self.image_signal.emit(image_data)
                else:
                    self.message_signal.emit(message)

        except Exception as e:
            self.message_signal.emit(f"Error: {str(e)}")
        finally:
            if self.writer:
                self.writer.close()

    def run(self):
        asyncio.run(self.start_client())

    async def send_message(self, message):
        if self.writer:
            try:
                self.writer.write(message.encode())
                await self.writer.drain()
            except Exception as e:
                self.message_signal.emit(f"Error sending message: {str(e)}")

    async def send_image(self, image_path):
        try:
            with open(image_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            message = f"IMAGE_MSG:{image_data}"
            if self.writer:
                self.writer.write(message.encode('utf-8'))
                await self.writer.drain()
        except Exception as e:
            self.message_signal.emit(f"Error sending image: {str(e)}")


class RCSClient(QMainWindow):
    def __init__(self, host, port):
        super().__init__()
        self.setWindowTitle("RCS Client")
        self.setGeometry(100, 100, 600, 400)
        self.client_thread = None
        self.host = host
        self.port = port

        self.layout = QVBoxLayout()

        self.title_label = QLabel(f"Chat Client connected to {self.host}:{self.port}")
        self.layout.addWidget(self.title_label)

        self.name_input = QLineEdit("Enter your name")
        self.layout.addWidget(self.name_input)

        self.start_button = QPushButton("Start Chat")
        self.start_button.clicked.connect(self.start_client)
        self.layout.addWidget(self.start_button)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.layout.addWidget(self.chat_display)

        self.message_input = QLineEdit("Type a message")
        self.layout.addWidget(self.message_input)

        self.send_button = QPushButton("Send Message")
        self.send_button.clicked.connect(self.send_message)
        self.layout.addWidget(self.send_button)

        self.send_image_button = QPushButton("Send Image")
        self.send_image_button.clicked.connect(self.browse_image)
        self.layout.addWidget(self.send_image_button)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

    def start_client(self):
        name = self.name_input.text().strip()
        if name:
            self.client_thread = ClientThread(self.host, self.port, name)
            self.client_thread.message_signal.connect(self.receive_message)
            self.client_thread.image_signal.connect(self.receive_image)
            self.client_thread.start()

            self.name_input.setEnabled(False)
            self.start_button.setEnabled(False)

    def receive_message(self, message):
        self.chat_display.append(message)

    def receive_image(self, image_data):
        self.chat_display.append("[Image received]")

    def send_message(self):
        message = self.message_input.text()
        asyncio.run(self.client_thread.send_message(message))
        self.message_input.clear()

    def browse_image(self):
        image_path, _ = QFileDialog.getOpenFileName(self, "Select Image", os.getenv('HOME'), "Image Files (*.png *.jpg *.bmp)")
        if image_path:
            asyncio.run(self.client_thread.send_image(image_path))


if __name__ == "__main__":
    app = QApplication([])
    client1 = RCSClient('127.0.0.1', 2855)  # Change IP and port for production
    client1.show()
    app.exec()
