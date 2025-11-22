import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import time
import re
import pyautogui
import os

def normalize_key(key):
    key = key.lower()
    mapping = {
        'alt_l': 'alt',
        'alt_r': 'alt',
        'control_l': 'ctrl',
        'control_r': 'ctrl',
        'ctrl_l': 'ctrl',
        'ctrl_r': 'ctrl',
        'shift_l': 'shift',
        'shift_r': 'shift'
    }
    return mapping.get(key, key)

class MacroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Automação por Timeline")
        self.root.geometry("900x400")
        
        # Variáveis de controle da execução
        self.executing = False
        self.stop_requested = False
        self.interrupt_reason = None
        self.message_shown = False  # Evita mensagens duplicadas
        
        # Dicionários para múltiplas listas carregadas:
        # chave: caminho completo do arquivo TXT; valor: lista de itens
        self.loaded_lists = {}
        # Para cada lista, guarda o índice do próximo item a ser utilizado
        self.loaded_index = {}
        
        # Frame dos botões
        button_frame = tk.Frame(root)
        button_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(button_frame, text="Capturar Clique", command=self.capture_mouse_click).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        tk.Button(button_frame, text="Adicionar Texto", command=self.add_text_event).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        tk.Button(button_frame, text="Adicionar Tecla", command=self.add_key_event).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        tk.Button(button_frame, text="Adicionar Espera", command=self.add_wait_event).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        tk.Button(button_frame, text="Apagar Campo", command=self.add_clear_event).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        tk.Button(button_frame, text="Carregar Lista TXT", command=self.load_timeline).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        tk.Button(button_frame, text="Importar Timeline", bg="blue", fg="white", command=self.import_timeline).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        tk.Button(button_frame, text="Exportar Timeline", bg="purple", fg="white", command=self.export_timeline).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        tk.Button(button_frame, text="Executar", bg="green", fg="white", command=self.execute_timeline).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        tk.Button(button_frame, text="Parar", bg="red", fg="white", command=self.stop_execution).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
        
        # Frame com scrollbar vertical para a timeline
        timeline_container = tk.Frame(root)
        timeline_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.canvas = tk.Canvas(timeline_container, bg="white")
        self.scrollbar = tk.Scrollbar(timeline_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="white", width=900)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=900)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.bind_all("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-1>", self.deselect_event)
        
        # Lista de eventos (cada evento é representado por um Label)
        self.events = []
        self.selected_event = None

    # --- Criação de eventos na timeline ---
    def add_event(self, event_text):
        event_label = tk.Label(self.scrollable_frame, text=event_text, bg="lightgray", padx=10, pady=5, relief=tk.RIDGE)
        event_label.pack(fill=tk.X, pady=2, expand=True)
        event_label.bind("<Button-1>", self.select_event)
        event_label.bind("<B1-Motion>", self.drag_event)
        event_label.bind("<Double-Button-1>", self.on_double_click_event)
        event_label.bind("<Enter>", lambda e: event_label.config(bg="gray"))
        event_label.bind("<Leave>", lambda e: event_label.config(bg="lightgray" if event_label != self.selected_event else "darkgray"))
        self.events.append(event_label)
    
    def on_double_click_event(self, event):
        label = event.widget
        text = label.cget("text")
        if (text.startswith("Clique Simples") or text.startswith("Duplo Clique") or 
            text.startswith("Botão Direito") or text.startswith("Scroll")):
            self.edit_click_event(label)
        elif text.startswith("Digitar:"):
            self.edit_text_event(label)
        elif text.startswith("Pressionar Tecla:"):
            self.edit_key_event(label)
        elif text.startswith("Esperar"):
            self.edit_wait_event(label)
        elif text.startswith("Lista:"):
            self.edit_list_event(label)
    
    # --- Edição de Evento de Clique (com radio buttons) ---
    def edit_click_event(self, event_label):
        current = event_label.cget("text")
        try:
            tipo_atual, coords = current.split(" em ")
        except ValueError:
            tipo_atual = "Clique Simples"
            coords = "(0, 0)"
        window = tk.Toplevel(self.root)
        window.title("Editar Clique")
        window.geometry("400x200")
        window.attributes("-topmost", True)
        
        pos_label = tk.Label(window, text="Mova o mouse e aperte ENTER", padx=20, pady=10)
        pos_label.pack(expand=True, fill=tk.BOTH)
        
        radio_frame = tk.Frame(window)
        radio_frame.pack(pady=5)
        click_type_var = tk.StringVar(value=tipo_atual.strip())
        tk.Radiobutton(radio_frame, text="Clique Simples", variable=click_type_var, value="Clique Simples").pack(anchor="w")
        tk.Radiobutton(radio_frame, text="Duplo Clique", variable=click_type_var, value="Duplo Clique").pack(anchor="w")
        tk.Radiobutton(radio_frame, text="Botão Direito", variable=click_type_var, value="Botão Direito").pack(anchor="w")
        tk.Radiobutton(radio_frame, text="Scroll", variable=click_type_var, value="Scroll").pack(anchor="w")
        
        def update_position():
            x = self.root.winfo_pointerx()
            y = self.root.winfo_pointery()
            pos_label.config(text=f"Mova o mouse e aperte ENTER\nPosição atual: ({x}, {y})")
            window.after(50, update_position)
        update_position()
        
        def on_enter(event):
            x = self.root.winfo_pointerx()
            y = self.root.winfo_pointery()
            novo_tipo = click_type_var.get()
            window.destroy()
            event_label.config(text=f"{novo_tipo} em ({x}, {y})")
        window.bind("<Return>", on_enter)
        window.focus_set()
    
    # --- Edição de Evento de Texto com Text widget e botão OK fixo ---
    def edit_text_event(self, event_label):
        if hasattr(event_label, "full_text"):
            full_text = event_label.full_text
        else:
            prefix = "Digitar:"
            full_text = event_label.cget("text")[len(prefix):].strip() if event_label.cget("text").startswith(prefix) else ""
        window = tk.Toplevel(self.root)
        window.title("Editar Texto")
        window.geometry("600x400")
        window.attributes("-topmost", True)
        # Usando grid para garantir que o botão fique sempre visível
        window.grid_rowconfigure(0, weight=1)
        window.grid_rowconfigure(1, weight=0)
        window.grid_columnconfigure(0, weight=1)
        
        text_frame = tk.Frame(window)
        text_frame.grid(row=0, column=0, sticky="nsew")
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set)
        text_widget.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        scrollbar.config(command=text_widget.yview)
        text_widget.insert("1.0", full_text)
        
        btn_frame = tk.Frame(window)
        btn_frame.grid(row=1, column=0, sticky="ew")
        ok_button = tk.Button(btn_frame, text="OK", command=lambda: self._save_text_edit(event_label, text_widget, window))
        ok_button.pack(pady=5)
    
    def _save_text_edit(self, event_label, text_widget, window):
        full_text = text_widget.get("1.0", tk.END).rstrip("\n")
        single_line = " ".join(full_text.splitlines())
        summary = single_line if len(single_line) <= 40 else single_line[:40] + "..."
        event_label.config(text=f"Digitar: {summary}")
        event_label.full_text = full_text
        window.destroy()
    
    # --- Edição de Evento de Tecla (com botão Limpar) ---
    def edit_key_event(self, event_label):
        current_text = event_label.cget("text")
        prefix = "Pressionar Tecla:"
        existing = current_text[len(prefix):].strip() if current_text.startswith(prefix) else ""
        window = tk.Toplevel(self.root)
        window.title("Editar Tecla")
        window.geometry("400x200")
        window.attributes("-topmost", True)
        instr_label = tk.Label(window, text="Pressione a(s) tecla(s) desejada(s) e aperte ENTER para confirmar", padx=20, pady=10)
        instr_label.pack(expand=True, fill=tk.BOTH)
        combo_label = tk.Label(window, text="Combinação: " + existing, padx=20, pady=5)
        combo_label.pack()
        key_combination = [] if not existing else existing.split("+")
        def on_key(event):
            if event.keysym == "Return":
                return
            if event.keysym not in key_combination:
                key_combination.append(event.keysym)
            combo_label.config(text="Combinação: " + "+".join(key_combination))
        window.bind("<Key>", on_key)
        clear_button = tk.Button(window, text="Limpar", command=lambda: (key_combination.clear(), combo_label.config(text="Combinação: ")))
        clear_button.pack(pady=5)
        def save_keys(e=None):
            if key_combination:
                event_label.config(text=f"Pressionar Tecla: {'+'.join(key_combination)}")
            else:
                event_label.config(text=f"Pressionar Tecla: {existing}")
            window.destroy()
        window.bind("<Return>", save_keys)
        ok_button = tk.Button(window, text="OK", command=save_keys)
        ok_button.pack(pady=5)
        window.focus_set()
    
    # --- Edição de Evento de Espera (apenas números) ---
    def edit_wait_event(self, event_label):
        current_text = event_label.cget("text")
        m = re.search(r"Esperar (\d+) segundos", current_text)
        existing = m.group(1) if m else ""
        window = tk.Toplevel(self.root)
        window.title("Editar Espera")
        window.geometry("400x150")
        window.attributes("-topmost", True)
        label = tk.Label(window, text="Digite o tempo (somente números) e aperte ENTER ou clique em OK", padx=20, pady=10)
        label.pack(expand=True, fill=tk.BOTH)
        entry = tk.Entry(window, width=20)
        entry.insert(0, existing)
        entry.pack(pady=5)
        entry.focus_set()
        vcmd = (window.register(lambda P: P.isdigit() or P == ""), '%P')
        entry.config(validate='key', validatecommand=vcmd)
        def save_edit(e=None):
            new_val = entry.get()
            if new_val.strip():
                event_label.config(text=f"Esperar {new_val} segundos")
            window.destroy()
        entry.bind("<Return>", save_edit)
        ok_button = tk.Button(window, text="OK", command=save_edit)
        ok_button.pack(pady=5)
    
    # --- Edição de Evento de Lista ---
    def edit_list_event(self, event_label):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            try:
                with open(file_path, "r") as f:
                    lines = f.read().splitlines()
                items = [line.strip() for line in lines if line.strip()]
                if items:
                    full_path = os.path.abspath(file_path)
                    self.loaded_lists[full_path] = items
                    self.loaded_index[full_path] = 0
                    event_label.config(text=f"Lista: {full_path}")
                else:
                    messagebox.showwarning("Aviso", "O arquivo está vazio ou não contém dados válidos.")
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível carregar o arquivo: {e}")
    
    # --- Seleção, arranjo e refresh da timeline ---
    def select_event(self, event):
        if self.selected_event:
            self.selected_event.config(bg="lightgray")
        self.selected_event = event.widget
        self.selected_event.config(bg="darkgray")
    
    def deselect_event(self, event):
        if self.selected_event and event.widget == self.canvas:
            self.selected_event.config(bg="lightgray")
            self.selected_event = None
    
    def drag_event(self, event):
        if self.selected_event:
            index = self.events.index(self.selected_event)
            y = event.y_root - self.scrollable_frame.winfo_rooty()
            for i, widget in enumerate(self.events):
                if widget.winfo_y() < y < widget.winfo_y() + widget.winfo_height():
                    self.events[index], self.events[i] = self.events[i], self.events[index]
                    self.refresh_timeline()
                    break
    
    def refresh_timeline(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.pack_forget()
        for widget in self.events:
            widget.pack(fill=tk.X, pady=2, expand=True)
    
    def _on_mouse_wheel(self, event):
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")
    
    def delete_selected_event(self, event):
        if self.selected_event in self.events:
            self.events.remove(self.selected_event)
            self.selected_event.destroy()
            self.selected_event = None
            self.refresh_timeline()
    
    # --- Funções para criar eventos ---
    def capture_mouse_click(self):
        capture_window = tk.Toplevel(self.root)
        capture_window.title("Capturar Clique")
        capture_window.geometry("400x200")
        capture_window.attributes("-topmost", True)
        
        label = tk.Label(capture_window, text="Mova o mouse até a posição desejada e aperte ENTER", padx=20, pady=10)
        label.pack(expand=True, fill=tk.BOTH)
        
        radio_frame = tk.Frame(capture_window)
        radio_frame.pack(pady=5)
        click_type_var = tk.StringVar(value="Clique Simples")
        tk.Radiobutton(radio_frame, text="Clique Simples", variable=click_type_var, value="Clique Simples").pack(anchor="w")
        tk.Radiobutton(radio_frame, text="Duplo Clique", variable=click_type_var, value="Duplo Clique").pack(anchor="w")
        tk.Radiobutton(radio_frame, text="Botão Direito", variable=click_type_var, value="Botão Direito").pack(anchor="w")
        tk.Radiobutton(radio_frame, text="Scroll", variable=click_type_var, value="Scroll").pack(anchor="w")
        
        def update_position():
            x = self.root.winfo_pointerx()
            y = self.root.winfo_pointery()
            label.config(text=f"Mova o mouse até a posição desejada e aperte ENTER\nPosição atual: ({x}, {y})")
            capture_window.after(50, update_position)
        update_position()
        
        def on_enter(event):
            x = self.root.winfo_pointerx()
            y = self.root.winfo_pointery()
            capture_window.destroy()
            option = click_type_var.get()
            self.add_event(f"{option} em ({x}, {y})")
        capture_window.bind("<Return>", on_enter)
        capture_window.focus_set()
    
    def add_text_event(self):
        text_window = tk.Toplevel(self.root)
        text_window.title("Adicionar Texto")
        text_window.geometry("600x400")
        text_window.attributes("-topmost", True)
        
        # Utiliza grid para garantir que o botão OK fique fixo na parte inferior
        text_window.grid_rowconfigure(0, weight=1)
        text_window.grid_rowconfigure(1, weight=0)
        text_window.grid_columnconfigure(0, weight=1)
        
        text_frame = tk.Frame(text_window)
        text_frame.grid(row=0, column=0, sticky="nsew")
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set)
        text_widget.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        scrollbar.config(command=text_widget.yview)
        
        btn_frame = tk.Frame(text_window)
        btn_frame.grid(row=1, column=0, sticky="ew")
        ok_button = tk.Button(btn_frame, text="OK", command=lambda: self._save_text_edit(text_widget, text_window))
        ok_button.pack(pady=5)
    
    def _save_text_edit(self, text_widget, window):
        full_text = text_widget.get("1.0", tk.END).rstrip("\n")
        single_line = " ".join(full_text.splitlines())
        summary = single_line if len(single_line) <= 40 else single_line[:40] + "..."
        if full_text.strip():
            event_label = tk.Label(self.scrollable_frame, text=f"Digitar: {summary}", bg="lightgray", padx=10, pady=5, relief=tk.RIDGE)
            event_label.full_text = full_text
            event_label.pack(fill=tk.X, pady=2, expand=True)
            event_label.bind("<Button-1>", self.select_event)
            event_label.bind("<B1-Motion>", self.drag_event)
            event_label.bind("<Double-Button-1>", self.on_double_click_event)
            event_label.bind("<Enter>", lambda e: event_label.config(bg="gray"))
            event_label.bind("<Leave>", lambda e: event_label.config(bg="lightgray" if event_label != self.selected_event else "darkgray"))
            self.events.append(event_label)
        window.destroy()
    
    def add_key_event(self):
        key_window = tk.Toplevel(self.root)
        key_window.title("Adicionar Tecla")
        key_window.geometry("400x200")
        key_window.attributes("-topmost", True)
        key_window.focus_set()
        instr_label = tk.Label(key_window, text="Pressione a(s) tecla(s) desejada(s) e aperte ENTER para confirmar", padx=20, pady=10)
        instr_label.pack(expand=True, fill=tk.BOTH)
        combo_label = tk.Label(key_window, text="Combinação: ", padx=20, pady=5)
        combo_label.pack()
        key_combination = []
        def on_key(event):
            if event.keysym == "Return":
                return
            if event.keysym not in key_combination:
                key_combination.append(event.keysym)
            combo_label.config(text="Combinação: " + "+".join(key_combination))
        key_window.bind("<Key>", on_key)
        clear_button = tk.Button(key_window, text="Limpar", command=lambda: (key_combination.clear(), combo_label.config(text="Combinação: ")))
        clear_button.pack(pady=5)
        def save_keys(e=None):
            if key_combination:
                self.add_event(f"Pressionar Tecla: {'+'.join(key_combination)}")
            key_window.destroy()
        key_window.bind("<Return>", save_keys)
        ok_button = tk.Button(key_window, text="OK", command=save_keys)
        ok_button.pack(pady=5)
    
    def add_wait_event(self):
        wait_window = tk.Toplevel(self.root)
        wait_window.title("Adicionar Espera")
        wait_window.geometry("400x150")
        wait_window.attributes("-topmost", True)
        label = tk.Label(wait_window, text="Digite o tempo em segundos e aperte ENTER ou clique em OK", padx=20, pady=10)
        label.pack(expand=True, fill=tk.BOTH)
        time_entry = tk.Entry(wait_window, width=20)
        time_entry.pack(pady=5)
        time_entry.focus_set()
        vcmd = (wait_window.register(lambda P: P.isdigit() or P == ""), '%P')
        time_entry.config(validate='key', validatecommand=vcmd)
        def process_time(event=None):
            tempo = time_entry.get()
            if tempo.strip():
                self.add_event(f"Esperar {tempo} segundos")
            wait_window.destroy()
        time_entry.bind("<Return>", process_time)
        ok_button = tk.Button(wait_window, text="OK", command=process_time)
        ok_button.pack(pady=5)
    
    def add_clear_event(self):
        self.add_event("Apagar Campo")
    
    def load_timeline(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            try:
                with open(file_path, "r") as file:
                    lines = file.read().splitlines()
                items = [line.strip() for line in lines if line.strip()]
                if items:
                    full_path = os.path.abspath(file_path)
                    self.loaded_lists[full_path] = items
                    self.loaded_index[full_path] = 0
                    self.add_event(f"Lista: {full_path}")
                    messagebox.showinfo("Lista carregada", f"Arquivo {os.path.basename(full_path)} carregado com {len(items)} itens.")
                else:
                    messagebox.showwarning("Aviso", "O arquivo está vazio ou não contém dados válidos.")
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível carregar o arquivo: {e}")
    
    def import_timeline(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            try:
                with open(file_path, "r") as file:
                    lines = file.readlines()
                for widget in self.scrollable_frame.winfo_children():
                    widget.destroy()
                self.events = []
                i = 0
                while i < len(lines):
                    line = lines[i].rstrip("\n")
                    if line.startswith("Digitar: <<START>>"):
                        full_text_lines = []
                        i += 1
                        while i < len(lines) and lines[i].strip() != "<<END>>":
                            full_text_lines.append(lines[i].rstrip("\n"))
                            i += 1
                        full_text = "\n".join(full_text_lines)
                        single_line = " ".join(full_text.splitlines())
                        summary = single_line if len(single_line) <= 40 else single_line[:40] + "..."
                        self.add_event("Digitar: " + summary)
                        self.events[-1].full_text = full_text
                    else:
                        if line.strip():
                            self.add_event(line.strip())
                    i += 1
                messagebox.showinfo("Importar", f"Timeline importada do arquivo {os.path.basename(file_path)}.")
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível importar a timeline: {e}")
    
    def export_timeline(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if file_path:
            try:
                with open(file_path, "w") as file:
                    for event_label in self.events:
                        text = event_label.cget("text")
                        if text.startswith("Digitar:") and hasattr(event_label, "full_text"):
                            file.write("Digitar: <<START>>\n" + event_label.full_text + "\n<<END>>\n")
                        else:
                            file.write(text + "\n")
                messagebox.showinfo("Exportar", f"Timeline exportada para o arquivo {os.path.basename(file_path)}.")
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível exportar a timeline: {e}")
    
    def execute_timeline(self):
        if self.executing:
            messagebox.showwarning("Atenção", "Macro já está em execução!")
            return
        self.message_shown = False
        required_files = set()
        for event in self.events:
            text = event.cget("text")
            if text.startswith("Lista:"):
                file_path = text.split("Lista:")[1].strip()
                required_files.add(file_path)
        for file_path in required_files:
            if file_path not in self.loaded_lists:
                if os.path.exists(file_path):
                    try:
                        with open(file_path, "r") as f:
                            lines = f.read().splitlines()
                        items = [line.strip() for line in lines if line.strip()]
                        if items:
                            self.loaded_lists[file_path] = items
                            self.loaded_index[file_path] = 0
                        else:
                            messagebox.showerror("Erro de Execução", f"A lista '{file_path}' está vazia.")
                            return
                    except Exception as e:
                        messagebox.showerror("Erro de Execução", f"Erro ao carregar a lista '{file_path}': {e}")
                        return
                else:
                    messagebox.showerror("Erro de Execução", f"A lista '{file_path}' não foi encontrada. Carregue-a antes de executar.")
                    return
        for file_path in required_files:
            self.loaded_index[file_path] = 0
        
        self.stop_requested = False
        self.interrupt_reason = None
        self.executing = True
        
        self.show_countdown_and_execute(required_files)
    
    def show_countdown_and_execute(self, required_files):
        countdown_window = tk.Toplevel(self.root)
        countdown_window.title("Contagem Regressiva")
        countdown_window.geometry("200x100")
        countdown_label = tk.Label(countdown_window, text="3", font=("Arial", 48))
        countdown_label.pack(expand=True, fill=tk.BOTH)
        def update_count(count):
            if count > 0:
                countdown_label.config(text=str(count))
                countdown_window.after(1000, update_count, count - 1)
            else:
                countdown_window.destroy()
                exec_thread = threading.Thread(target=self._run_macro, args=(required_files,))
                exec_thread.start()
                shake_thread = threading.Thread(target=self._monitor_mouse_shake)
                shake_thread.daemon = True
                shake_thread.start()
        update_count(3)
    
    def _run_macro(self, required_files):
        tem_lista = any(event.cget("text").startswith("Lista:") for event in self.events)
        if tem_lista:
            while (not self.stop_requested) and any(self.loaded_index[fname] < len(self.loaded_lists[fname]) for fname in required_files):
                for event_label in self.events:
                    if self.stop_requested:
                        break
                    text = event_label.cget("text")
                    if (text.startswith("Clique Simples") or text.startswith("Duplo Clique") or 
                        text.startswith("Botão Direito") or text.startswith("Scroll")) and " em (" in text:
                        match = re.search(r"\((\d+),\s*(\d+)\)", text)
                        if match:
                            x = int(match.group(1))
                            y = int(match.group(2))
                            if text.startswith("Botão Direito"):
                                pyautogui.click(x, y, button="right")
                            elif text.startswith("Duplo Clique"):
                                pyautogui.doubleClick(x, y)
                            elif text.startswith("Scroll"):
                                pyautogui.click(x, y, button="middle")
                            else:
                                pyautogui.click(x, y)
                            time.sleep(0.2)
                    elif text.startswith("Digitar:"):
                        if hasattr(event_label, "full_text"):
                            full_text = event_label.full_text
                        else:
                            full_text = text[len("Digitar:"):].strip()
                        pyautogui.write(full_text)
                        time.sleep(0.2)
                    elif text.startswith("Pressionar Tecla:"):
                        key_str = text[len("Pressionar Tecla:"):].strip()
                        if "+" in key_str:
                            keys = [normalize_key(k) for k in key_str.split("+")]
                            pyautogui.hotkey(*keys)
                        else:
                            pyautogui.press(normalize_key(key_str))
                        time.sleep(0.2)
                    elif text.startswith("Esperar"):
                        match = re.search(r"Esperar (\d+) segundos", text)
                        if match:
                            seconds = int(match.group(1))
                            for _ in range(seconds * 10):
                                if self.stop_requested:
                                    break
                                time.sleep(0.1)
                    elif text.startswith("Apagar Campo"):
                        pyautogui.hotkey('ctrl', 'a')
                        pyautogui.press('backspace')
                        time.sleep(0.2)
                    elif text.startswith("Lista:"):
                        file_path = text.split("Lista:")[1].strip()
                        if file_path in self.loaded_lists and self.loaded_index[file_path] < len(self.loaded_lists[file_path]):
                            item = self.loaded_lists[file_path][self.loaded_index[file_path]]
                            pyautogui.write(item)
                            self.loaded_index[file_path] += 1
                            time.sleep(0.2)
        else:
            for event_label in self.events:
                if self.stop_requested:
                    break
                text = event_label.cget("text")
                if (text.startswith("Clique Simples") or text.startswith("Duplo Clique") or 
                    text.startswith("Botão Direito") or text.startswith("Scroll")) and " em (" in text:
                    match = re.search(r"\((\d+),\s*(\d+)\)", text)
                    if match:
                        x = int(match.group(1))
                        y = int(match.group(2))
                        if text.startswith("Botão Direito"):
                            pyautogui.click(x, y, button="right")
                        elif text.startswith("Duplo Clique"):
                            pyautogui.doubleClick(x, y)
                        elif text.startswith("Scroll"):
                            pyautogui.click(x, y, button="middle")
                        else:
                            pyautogui.click(x, y)
                        time.sleep(0.2)
                elif text.startswith("Digitar:"):
                    if hasattr(event_label, "full_text"):
                        full_text = event_label.full_text
                    else:
                        full_text = text[len("Digitar:"):].strip()
                    pyautogui.write(full_text)
                    time.sleep(0.2)
                elif text.startswith("Pressionar Tecla:"):
                    key_str = text[len("Pressionar Tecla:"):].strip()
                    if "+" in key_str:
                        keys = [normalize_key(k) for k in key_str.split("+")]
                        pyautogui.hotkey(*keys)
                    else:
                        pyautogui.press(normalize_key(key_str))
                    time.sleep(0.2)
                elif text.startswith("Esperar"):
                    match = re.search(r"Esperar (\d+) segundos", text)
                    if match:
                        seconds = int(match.group(1))
                        for _ in range(seconds * 10):
                            if self.stop_requested:
                                break
                            time.sleep(0.1)
                elif text.startswith("Apagar Campo"):
                    pyautogui.hotkey('ctrl', 'a')
                    pyautogui.press('backspace')
                    time.sleep(0.2)
        self.executing = False
        if not self.message_shown:
            if self.stop_requested:
                self._show_message("Interrompido", self.interrupt_reason)
            else:
                self._show_message("Finalizado", "A macro foi executada com sucesso.")
    
    def _monitor_mouse_shake(self):
        last_x = pyautogui.position().x
        shake_count = 0
        while self.executing and not self.stop_requested:
            time.sleep(0.1)
            current_x = pyautogui.position().x
            diff = current_x - last_x
            if abs(diff) > 100:
                shake_count += 1
            else:
                shake_count = max(0, shake_count - 1)
            last_x = current_x
            if shake_count >= 3:
                self.interrupt_reason = "Macro interrompida por sacudir o mouse."
                self.stop_requested = True
                self._show_message("Interrompido", self.interrupt_reason)
                break
    
    def stop_execution(self):
        if not self.stop_requested:
            self.interrupt_reason = "Macro interrompida pelo usuário."
        self.stop_requested = True
        self._show_message("Interrompido", self.interrupt_reason)
    
    def _show_message(self, title, message):
        if not self.message_shown:
            self.message_shown = True
            self.root.after(0, lambda: messagebox.showinfo(title, message))

if __name__ == "__main__":
    root = tk.Tk()
    app = MacroApp(root)
    root.bind("<Delete>", app.delete_selected_event)
    root.mainloop()
