import tkinter as tk
from tkinter import simpledialog, messagebox
import json
import os
import time
import threading
import pystray
from PIL import Image, ImageDraw

# Ficheiro local para guardar o seu utilizador e o caminho da pasta
CONFIG_FILE = 'config_local.dat'

class ChatSpy:
    def __init__(self):
        self.username = ""
        self.shared_folder = ""
        self.current_room = ""
        self.last_mtime = 0
        self.loaded_messages_count = 0
        
        # Carrega as configurações guardadas localmente
        self.load_config()
        
        # Janela Principal (Translúcida)
        self.root = tk.Tk()
        self.root.title("log de erros")
        self.root.geometry("250x300") # Tamanho inicial menor
        self.root.attributes('-alpha', 0.8)
        self.root.attributes('-topmost', True)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        
        self.bg_color = "#1e1e1e"
        self.fg_color = "#cccccc"
        self.root.configure(bg=self.bg_color)

        # 1. Barra Superior (Fixa no topo)
        top_frame = tk.Frame(self.root, bg=self.bg_color)
        top_frame.pack(side=tk.TOP, fill=tk.X, pady=5)
        
        tk.Button(top_frame, text="+", command=self.open_room, bg="#333", fg="white", bd=0, width=3).pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="-", command=self.close_room, bg="#333", fg="white", bd=0, width=3).pack(side=tk.LEFT)
        
        # Menu Dropdown para listar as salas existentes
        self.room_mb = tk.Menubutton(top_frame, text="Salas ▼", bg="#333", fg="white", relief=tk.FLAT)
        self.room_mb.pack(side=tk.RIGHT, padx=5)
        self.room_menu = tk.Menu(self.room_mb, tearoff=0, bg="#333", fg="white", postcommand=self.refresh_rooms)
        self.room_mb.config(menu=self.room_menu)

        # 2. Entrada de Texto (Fixa no fundo para nunca sumir)
        self.entry_msg = tk.Entry(self.root, bg="#333", fg="white", bd=0)
        self.entry_msg.pack(side=tk.BOTTOM, padx=5, pady=10, fill=tk.X)
        self.entry_msg.bind("<Return>", self.send_message)

        # 3. Área de Mensagens (Preenche o meio)
        self.chat_box = tk.Text(self.root, bg=self.bg_color, fg=self.fg_color, bd=0, state=tk.DISABLED, height=10)
        self.chat_box.pack(side=tk.TOP, padx=5, pady=5, fill=tk.BOTH, expand=True)

        # Ícone na Área de Notificação
        self.tray_icon = None
        self.setup_tray()
        
        self.root.after(1000, self.check_messages)
        self.root.after(500, self.check_initial_setup)

    def create_dot_icon(self, color):
        image = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((4, 4, 12, 12), fill=color)
        return image

    def setup_tray(self):
        icon_image = self.create_dot_icon("black")
        menu = pystray.Menu(
            pystray.MenuItem("Abrir", self.show_window, default=True),
            pystray.MenuItem("Sair", self.quit_app)
        )
        self.tray_icon = pystray.Icon("log_de_erros", icon_image, "...", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def update_tray_icon(self, color):
        if self.tray_icon:
            self.tray_icon.icon = self.create_dot_icon(color)

    def hide_window(self):
        self.root.withdraw()
        self.update_tray_icon("black")

    def show_window(self, icon=None, item=None):
        self.root.deiconify()
        self.update_tray_icon("black")

    def quit_app(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.username = config.get('username', '')
                    self.shared_folder = config.get('shared_folder', '')
            except:
                pass

    def save_config(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'username': self.username,
                'shared_folder': self.shared_folder
            }, f, ensure_ascii=False)

    def check_initial_setup(self):
        if not self.username:
            name = simpledialog.askstring("Configuração", "Escolha o seu nome no chat:", initialvalue="Matheus")
            if name:
                self.username = name
                self.save_config()
            else:
                self.username = "Anonimo"
        
        if not self.shared_folder:
            folder = simpledialog.askstring(
                "Configuração de Diretório", 
                "Onde deseja salvar o arquivo de comunicação na rede?\n(Exemplo: Z:\\ ou \\\\servidor\\pasta)"
            )
            if folder:
                self.shared_folder = folder
                self.save_config()
            else:
                messagebox.showwarning("Aviso", "O programa precisa do diretório para funcionar.")

    def get_room_filepath(self):
        return os.path.join(self.shared_folder, f"arquivo_cache_{self.current_room}.tpm")

    def refresh_rooms(self):
        """Lê a pasta compartilhada e atualiza o menu com as salas existentes"""
        if not self.shared_folder or not os.path.exists(self.shared_folder):
            return
        
        self.room_menu.delete(0, tk.END)
        rooms_found = False
        
        try:
            for f in os.listdir(self.shared_folder):
                if f.startswith("arquivo_cache_") and f.endswith(".tpm"):
                    r = f.replace("arquivo_cache_", "").replace(".tpm", "")
                    # Adiciona a sala ao menu clicável
                    self.room_menu.add_command(label=r, command=lambda room=r: self.join_room(room))
                    rooms_found = True
        except:
            pass
            
        if not rooms_found:
            self.room_menu.add_command(label="Nenhuma sala", state=tk.DISABLED)

    def join_room(self, room):
        """Função para carregar uma sala selecionada"""
        self.current_room = room.strip().lower()
        self.room_mb.config(text=f"{self.current_room} ▼")
        self.last_mtime = 0
        self.loaded_messages_count = 0
        
        self.chat_box.config(state=tk.NORMAL)
        self.chat_box.delete('1.0', tk.END)
        self.chat_box.insert(tk.END, f"--- Entrou na sala: {self.current_room} ---\n")
        self.chat_box.config(state=tk.DISABLED)

    def open_room(self):
        if not self.shared_folder:
            self.check_initial_setup()
            return
            
        room = simpledialog.askstring("Abrir", "Nome da nova sala:")
        if room:
            room_name = room.strip().lower()
            room_file = os.path.join(self.shared_folder, f"arquivo_cache_{room_name}.tpm")
            
            # Cria o arquivo se for uma sala inédita
            if not os.path.exists(room_file):
                try:
                    with open(room_file, 'w', encoding='utf-8') as f:
                        json.dump([], f)
                except Exception as e:
                    messagebox.showerror("Erro", f"Não foi possível criar o arquivo:\n{e}")
                    return
            
            self.join_room(room_name)

    def close_room(self):
        self.chat_box.config(state=tk.NORMAL)
        self.chat_box.delete('1.0', tk.END)
        self.chat_box.insert(tk.END, f"--- Fechou {self.current_room} ---\n")
        self.chat_box.config(state=tk.DISABLED)
        self.current_room = ""
        self.room_mb.config(text="Salas ▼")

    def send_message(self, event=None):
        msg = self.entry_msg.get().strip()
        if msg and self.username and self.current_room and self.shared_folder:
            room_file = self.get_room_filepath()
            self.entry_msg.delete(0, tk.END)
            
            for _ in range(5):
                try:
                    messages = []
                    if os.path.exists(room_file):
                        with open(room_file, 'r', encoding='utf-8') as f:
                            messages = json.load(f)
                    
                    messages.append({"user": self.username, "msg": msg, "time": time.time()})
                    
                    with open(room_file, 'w', encoding='utf-8') as f:
                        json.dump(messages, f, ensure_ascii=False)
                    break
                except:
                    time.sleep(0.1)

    def check_messages(self):
        if self.current_room and self.shared_folder:
            room_file = self.get_room_filepath()
            if os.path.exists(room_file):
                try:
                    mtime = os.path.getmtime(room_file)
                    if mtime > self.last_mtime:
                        self.last_mtime = mtime
                        self.load_messages(room_file)
                except:
                    pass
        self.root.after(1000, self.check_messages)

    def load_messages(self, room_file):
        try:
            with open(room_file, 'r', encoding='utf-8') as f:
                messages = json.load(f)
            
            if len(messages) > self.loaded_messages_count:
                new_messages = messages[self.loaded_messages_count:]
                
                self.chat_box.config(state=tk.NORMAL)
                for msg_data in new_messages:
                    user = msg_data.get('user')
                    msg = msg_data.get('msg')
                    self.chat_box.insert(tk.END, f"{user}: {msg}\n")
                
                self.chat_box.see(tk.END)
                self.chat_box.config(state=tk.DISABLED)
                self.loaded_messages_count = len(messages)

                if self.root.state() == 'withdrawn':
                    self.update_tray_icon("blue")
        except:
            pass

if __name__ == "__main__":
    app = ChatSpy()
    app.root.mainloop()
