import asyncio
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QPushButton, QTextEdit,
                             QWidget, QLabel)
from PyQt6.QtCore import Qt, QThread, pyqtSignal


class ServerThread(QThread):
    log_signal = pyqtSignal(str)

    clients = {}

    def run(self):
        asyncio.run(self.start_tcp_server())

    async def start_tcp_server(self):
        async def handle_client(reader, writer):
            addr = writer.get_extra_info('peername')
            client_id = len(self.clients) + 1
            self.log_signal.emit(f"New client connected with ID {client_id} from {addr}.")

            try:
                name_data = await reader.read(100)
                name = name_data.decode().strip()

                self.clients[client_id] = {'name': name, 'writer': writer}
                self.log_signal.emit(f"Client {name} (ID: {client_id}) connected.")

                join_message = f"{name} (ID: {client_id}) has joined the chat."
                await self.broadcast(join_message)

                while True:
                    data = await reader.read(4096)
                    if not data:
                        break
                    message = data.decode()

                    if message.startswith("IMAGE_MSG:"):
                        await self.broadcast(message)
                    else:
                        full_message = f"{name} (ID: {client_id}): {message}"
                        self.log_signal.emit(f"Broadcasting: {full_message}")
                        await self.broadcast(full_message)

            except Exception as e:
                self.log_signal.emit(f"Error: {str(e)}")
            finally:
                if client_id in self.clients:
                    self.clients.pop(client_id, None)
                    writer.close()
                    self.log_signal.emit(f"Client {name} (ID: {client_id}) has left the chat.")

                    leave_message = f"{name} (ID: {client_id}) has left the chat."
                    await self.broadcast(leave_message)

        server = await asyncio.start_server(handle_client, '0.0.0.0', 2855)  # Change IP and port for production
        self.log_signal.emit("Server started on port 2855.")

        async with server:
            await server.serve_forever()

    async def broadcast(self, message):
        for client in self.clients.values():
            writer = client['writer']
            try:
                writer.write(message.encode())
                await writer.drain()
            except Exception as e:
                self.log_signal.emit(f"Error broadcasting to client: {str(e)}")

    def stop(self):
        pass


class RCSApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RCS Server")
        self.setGeometry(100, 100, 800, 600)
        self.server_thread = None

        self.layout = QVBoxLayout()

        self.title_label = QLabel("RCS Server with Multi-client Chat")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.title_label)

        self.start_button = QPushButton("Start Server")
        self.start_button.clicked.connect(self.start_server)
        self.layout.addWidget(self.start_button)

        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.layout.addWidget(self.log_display)

        container = QWidget()
        container.setLayout(self.layout)
        self.setCentralWidget(container)

    def start_server(self):
        if not self.server_thread:
            self.server_thread = ServerThread()
            self.server_thread.log_signal.connect(self.log_message)
            self.server_thread.start()

    def log_message(self, message):
        self.log_display.append(message)


if __name__ == "__main__":
    app = QApplication([])
    server_app = RCSApp()
    server_app.show()
    app.exec()
