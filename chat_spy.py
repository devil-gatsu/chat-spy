import tkinter as tk
from tkinter import simpledialog, messagebox
import socket
import threading
import json
import os
import pystray
from PIL import Image, ImageDraw

# Configurações de Rede
PORT = 50000
BROADCAST_IP = '<broadcast>'
CONFIG_FILE = 'chat_spy_user.json'

class ChatSpy:
    def __init__(self):
        self.username = self.load_username()
        self.current_room = "Geral"
        
        # Configuração da Janela Principal (Translúcida)
        self.root = tk.Tk()
        self.root.title("SpyChat")
        self.root.geometry("300x400")
        self.root.attributes('-alpha', 0.8) # Translucidez de 80%
        self.root.attributes('-topmost', True) # Sempre no topo
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        # Cores discretas
        self.bg_color = "#1e1e1e"
        self.fg_color = "#cccccc"
        self.root.configure(bg=self.bg_color)

        # Barra Superior (+ e -)
        top_frame = tk.Frame(self.root, bg=self.bg_color)
        top_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(top_frame, text="+", command=self.open_room, bg="#333", fg="white", bd=0, width=3).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="-", command=self.close_room, bg="#333", fg="white", bd=0, width=3).pack(side=tk.LEFT)
        self.lbl_room = tk.Label(top_frame, text=f"Sala: {self.current_room}", bg=self.bg_color, fg=self.fg_color)
        self.lbl_room.pack(side=tk.RIGHT, padx=5)

        # Área de Mensagens
        self.chat_box = tk.Text(self.root, bg=self.bg_color, fg=self.fg_color, bd=0, state=tk.DISABLED)
        self.chat_box.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

        # Entrada de Texto
        self.entry_msg = tk.Entry(self.root, bg="#333", fg="white", bd=0)
        self.entry_msg.pack(padx=5, pady=5, fill=tk.X)
        self.entry_msg.bind("<Return>", self.send_message)

        # Configuração de Socket UDP
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", PORT))

        # Thread de Escuta
        threading.Thread(target=self.listen_messages, daemon=True).start()

        # Configuração da Bandeja (Tray)
        self.tray_icon = None
        self.setup_tray()
        
        # Inicia pedindo o nome se for o primeiro uso
        if not self.username:
            self.root.after(500, self.ask_username)

    def create_dot_icon(self, color):
        """Cria uma imagem de um pequeno ponto para a bandeja"""
        image = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        # Um ponto simples um pouco maior que 1 pixel (círculo 8x8 no centro)
        draw.ellipse((4, 4, 12, 12), fill=color)
        return image

    def setup_tray(self):
        icon_image = self.create_dot_icon("black")
        menu = pystray.Menu(
            pystray.MenuItem("Abrir", self.show_window, default=True),
            pystray.MenuItem("Sair", self.quit_app)
        )
        self.tray_icon = pystray.Icon("chat_spy", icon_image, "...", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def update_tray_icon(self, color):
        if self.tray_icon:
            self.tray_icon.icon = self.create_dot_icon(color)

    def hide_window(self):
        self.root.withdraw()
        self.update_tray_icon("black")

    def show_window(self, icon=None, item=None):
        self.root.deiconify()
        self.update_tray_icon("black") # Reseta a notificação visual ao abrir

    def quit_app(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()

    def load_username(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f).get('username', '')
        return ''

    def ask_username(self):
        # Exemplo de placeholder padrão caso a pessoa prefira apenas confirmar
        name = simpledialog.askstring("Usuário", "Defina seu nome de usuário:", initialvalue="Matheus")
        if name:
            self.username = name
            with open(CONFIG_FILE, 'w') as f:
                json.dump({'username': self.username}, f)

    def open_room(self):
        if not self.username:
            self.ask_username()
        room = simpledialog.askstring("Nova Sala", "Nome da sala (ex: suporte):")
        if room:
            self.current_room = room
            self.lbl_room.config(text=f"Sala: {self.current_room}")
            self.chat_box.config(state=tk.NORMAL)
            self.chat_box.delete('1.0', tk.END)
            self.chat_box.insert(tk.END, f"--- Entrou na sala {room} ---\n")
            self.chat_box.config(state=tk.DISABLED)

    def close_room(self):
        self.chat_box.config(state=tk.NORMAL)
        self.chat_box.delete('1.0', tk.END)
        self.chat_box.insert(tk.END, f"--- Sala {self.current_room} fechada ---\n")
        self.chat_box.config(state=tk.DISABLED)
        self.current_room = ""
        self.lbl_room.config(text="Sala: Nenhuma")

    def send_message(self, event=None):
        msg = self.entry_msg.get().strip()
        if msg and self.username and self.current_room:
            packet = json.dumps({"user": self.username, "room": self.current_room, "msg": msg})
            self.sock.sendto(packet.encode('utf-8'), (BROADCAST_IP, PORT))
            self.entry_msg.delete(0, tk.END)

    def listen_messages(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(1024)
                packet = json.loads(data.decode('utf-8'))
                
                # Exibe a mensagem apenas se estiver na mesma sala
                if packet.get('room') == self.current_room:
                    user = packet.get('user')
                    msg = packet.get('msg')
                    
                    self.chat_box.config(state=tk.NORMAL)
                    self.chat_box.insert(tk.END, f"{user}: {msg}\n")
                    self.chat_box.see(tk.END)
                    self.chat_box.config(state=tk.DISABLED)

                    # Se a janela estiver oculta, muda o ícone para azul
                    if self.root.state() == 'withdrawn':
                        self.update_tray_icon("blue")
            except:
                pass

if __name__ == "__main__":
    app = ChatSpy()
    app.root.mainloop()
