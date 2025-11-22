import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import threading
import time
import re
import pyautogui
import os
import ctypes

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

# Classe auxiliar para tooltip
class CreateToolTip(object):
    """
    Cria um tooltip para um widget.
    Exemplo:
      btn = tk.Button(root, text="Teste")
      btn.pack()
      CreateToolTip(btn, "Este é o tooltip")
    """
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.showtip)
        widget.bind("<Leave>", self.hidetip)

    def showtip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class MacroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Automação por Timeline")
        self.root.geometry("940x400")
        
        # Variáveis de controle da execução
        self.executing = False
        self.stop_requested = False
        self.interrupt_reason = None
        self.message_shown = False  # Evita mensagens duplicadas
        self.suppress_messages = False  # Para suprimir mensagens intermediárias em loop
        
        # Dicionários para múltiplas listas carregadas:
        self.loaded_lists = {}
        self.loaded_index = {}
        
        # Lista para seleção múltipla
        self.selected_events = []
        
        # Frame dos botões (ocupando toda a largura)
        button_frame = tk.Frame(root)
        button_frame.pack(fill=tk.X, pady=5)
        # Frame interno para manter os botões com tamanho fixo e centralizados
        inner_frame = tk.Frame(button_frame)
        inner_frame.pack(anchor="center")
        
        # Botões quadrados com emojis (largura um pouco maior, width=5)
        self.btn_capturar = tk.Button(inner_frame, text="🖱️", command=self.capture_mouse_click,
                                        font=("Segoe UI Emoji", 14), width=5, height=2)
        self.btn_capturar.pack(side=tk.LEFT, padx=2)
        CreateToolTip(self.btn_capturar, "Captura um clique do mouse")
        
        self.btn_texto = tk.Button(inner_frame, text="📝", command=self.add_text_event,
                                     font=("Segoe UI Emoji", 14), width=5, height=2)
        self.btn_texto.pack(side=tk.LEFT, padx=2)
        CreateToolTip(self.btn_texto, "Adiciona um bloco de texto à timeline")
        
        self.btn_tecla = tk.Button(inner_frame, text="⌨️", command=self.add_key_event,
                                     font=("Segoe UI Emoji", 14), width=5, height=2)
        self.btn_tecla.pack(side=tk.LEFT, padx=2)
        CreateToolTip(self.btn_tecla, "Adiciona uma sequência de teclas")
        
        self.btn_espera = tk.Button(inner_frame, text="⏱️", command=self.add_wait_event,
                                      font=("Segoe UI Emoji", 14), width=5, height=2)
        self.btn_espera.pack(side=tk.LEFT, padx=2)
        CreateToolTip(self.btn_espera, "Adiciona um tempo de espera")
        
        self.btn_apagar = tk.Button(inner_frame, text="🗑️", command=self.add_clear_event,
                                     font=("Segoe UI Emoji", 14), width=5, height=2)
        self.btn_apagar.pack(side=tk.LEFT, padx=2)
        CreateToolTip(self.btn_apagar, "Adiciona o evento de apagar campo")
        
        self.btn_carregar = tk.Button(inner_frame, text="📋", command=self.load_timeline,
                                        font=("Segoe UI Emoji", 14), width=5, height=2)
        self.btn_carregar.pack(side=tk.LEFT, padx=2)
        CreateToolTip(self.btn_carregar, "Carrega uma lista de um arquivo TXT")
        
        self.btn_importar = tk.Button(inner_frame, text="📥", bg="blue", fg="white", command=self.import_timeline,
                                       font=("Segoe UI Emoji", 14), width=5, height=2)
        self.btn_importar.pack(side=tk.LEFT, padx=2)
        CreateToolTip(self.btn_importar, "Importa uma timeline de arquivo")
        
        self.btn_exportar = tk.Button(inner_frame, text="📤", bg="purple", fg="white", command=self.export_timeline,
                                       font=("Segoe UI Emoji", 14), width=5, height=2)
        self.btn_exportar.pack(side=tk.LEFT, padx=2)
        CreateToolTip(self.btn_exportar, "Exporta a timeline para arquivo")
        
        # Botão "Executar" e menu suspenso para "Executar em loop"
        exec_frame = tk.Frame(inner_frame)
        exec_frame.pack(side=tk.LEFT, padx=2)
        self.btn_executar = tk.Button(exec_frame, text="▶️", bg="green", fg="white", command=self.execute_timeline,
                                       font=("Segoe UI Emoji", 14), width=5, height=2)
        self.btn_executar.pack(side=tk.LEFT, padx=2)
        CreateToolTip(self.btn_executar, "Executa a macro")
        loop_mb = tk.Menubutton(exec_frame, text="▼", relief=tk.RAISED, width=3, height=2, bg="green", fg="white",
                                 font=("Segoe UI Emoji", 14))
        loop_menu = tk.Menu(loop_mb, tearoff=0)
        loop_menu.add_command(label="Executar em loop", command=self.execute_timeline_loop)
        loop_mb.config(menu=loop_menu)
        loop_mb.pack(side=tk.LEFT, padx=2)
        CreateToolTip(loop_mb, "Executa a macro em loop")
        
        self.btn_parar = tk.Button(inner_frame, text="⏹️", bg="red", fg="white", command=self.stop_execution,
                                    font=("Segoe UI Emoji", 14), width=5, height=2)
        self.btn_parar.pack(side=tk.LEFT, padx=2)
        CreateToolTip(self.btn_parar, "Interrompe a macro")
        
        # Botão "Sobre" (?)
        self.btn_about = tk.Button(inner_frame, text="❓", command=self.show_about,
                                    font=("Segoe UI Emoji", 14), width=5, height=2)
        self.btn_about.pack(side=tk.LEFT, padx=2)
        CreateToolTip(self.btn_about, "Sobre este sistema")
        
        # Frame com scrollbar para a timeline
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
        
        # Lista de eventos (cada evento é um Label)
        self.events = []
    
    def center_window(self, win, width, height):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        win.geometry(f"{width}x{height}+{x}+{y}")
    
    def show_about(self):
        about_win = tk.Toplevel(self.root)
        about_win.title("Sobre")
        self.center_window(about_win, 500, 300)
        about_win.attributes("-topmost", True)
        info = (
            "MacroApp - Automação por Timeline\n"
            "Versão 1.0\n\n"
            "Funcionalidades:\n"
            "• Capturar cliques, adicionar textos, teclas, esperas, apagar campo\n"
            "• Suporte a listas (importação/exportação)\n"
            "• Execução com contagem regressiva e monitor de sacudir o mouse\n"
            "• Modo de execução em loop\n\n"
            "Atalhos úteis:\n"
            "• Ctrl + Clique: Seleciona múltiplos eventos\n"
            "• Delete: Deleta os eventos selecionados\n"
            "• Arraste: Move eventos (ou grupo de eventos)"
        )
        label = tk.Label(about_win, text=info, font=("Arial", 10), justify="left")
        label.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)
    
    def _on_mouse_wheel(self, event):
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")
    
    def add_event(self, event_text):
        event_label = tk.Label(self.scrollable_frame, text=event_text, bg="lightgray",
                               padx=10, pady=5, relief=tk.RIDGE)
        event_label.pack(fill=tk.X, pady=2, expand=True)
        event_label.bind("<Button-1>", self.select_event)
        event_label.bind("<B1-Motion>", self.drag_event)
        event_label.bind("<Double-Button-1>", self.on_double_click_event)
        event_label.bind("<Enter>", lambda e: event_label.config(bg="gray"))
        event_label.bind("<Leave>", lambda e: event_label.config(bg="lightgray" if event_label not in self.selected_events else "darkgray"))
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
    
    def select_event(self, event):
        ctrl_pressed = (event.state & 0x0004) != 0
        if ctrl_pressed:
            if event.widget in self.selected_events:
                self.selected_events.remove(event.widget)
                event.widget.config(bg="lightgray")
            else:
                self.selected_events.append(event.widget)
                event.widget.config(bg="darkgray")
        else:
            for w in self.selected_events:
                w.config(bg="lightgray")
            self.selected_events = [event.widget]
            event.widget.config(bg="darkgray")
    
    def deselect_event(self, event):
        if self.selected_events and event.widget == self.canvas:
            for w in self.selected_events:
                w.config(bg="lightgray")
            self.selected_events = []
    
    def drag_event(self, event):
        if self.selected_events:
            y = event.y_root - self.scrollable_frame.winfo_rooty()
            target_index = None
            for i, widget in enumerate(self.events):
                if widget.winfo_y() < y < widget.winfo_y() + widget.winfo_height():
                    target_index = i
                    break
            if target_index is not None:
                selected = [w for w in self.events if w in self.selected_events]
                self.events = [w for w in self.events if w not in self.selected_events]
                self.events[target_index:target_index] = selected
                self.refresh_timeline()
    
    def refresh_timeline(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.pack_forget()
        for widget in self.events:
            widget.pack(fill=tk.X, pady=2, expand=True)
    
    def delete_selected_events(self, event=None):
        for widget in self.selected_events:
            if widget in self.events:
                self.events.remove(widget)
                widget.destroy()
        self.selected_events = []
        self.refresh_timeline()
    
    def edit_click_event(self, event_label):
        current = event_label.cget("text")
        try:
            tipo_atual, coords = current.split(" em ")
        except ValueError:
            tipo_atual = "Clique Simples"
            coords = "(0, 0)"
        window = tk.Toplevel(self.root)
        window.title("Editar Clique")
        self.center_window(window, 400, 200)
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
    
    def edit_text_event(self, event_label):
        if hasattr(event_label, "full_text"):
            full_text = event_label.full_text
        else:
            prefix = "Digitar:"
            full_text = event_label.cget("text")[len(prefix):].strip() if event_label.cget("text").startswith(prefix) else ""
        window = tk.Toplevel(self.root)
        window.title("Editar Texto")
        self.center_window(window, 600, 400)
        window.attributes("-topmost", True)
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
        ok_button = tk.Button(btn_frame, text="OK", command=lambda: self._save_text_edit(text_widget, window))
        ok_button.pack(pady=5)
    
    def _save_text_edit(self, text_widget, window):
        full_text = text_widget.get("1.0", tk.END).rstrip("\n")
        single_line = " ".join(full_text.splitlines())
        summary = single_line if len(single_line) <= 40 else single_line[:40] + "..."
        event_label = tk.Label(self.scrollable_frame, text=f"Digitar: {summary}", bg="lightgray",
                                padx=10, pady=5, relief=tk.RIDGE)
        event_label.full_text = full_text
        event_label.pack(fill=tk.X, pady=2, expand=True)
        event_label.bind("<Button-1>", self.select_event)
        event_label.bind("<B1-Motion>", self.drag_event)
        event_label.bind("<Double-Button-1>", self.on_double_click_event)
        event_label.bind("<Enter>", lambda e: event_label.config(bg="gray"))
        event_label.bind("<Leave>", lambda e: event_label.config(bg="lightgray" if event_label not in self.selected_events else "darkgray"))
        self.events.append(event_label)
        window.destroy()
    
    def edit_key_event(self, event_label):
        current_text = event_label.cget("text")
        prefix = "Pressionar Tecla:"
        existing = current_text[len(prefix):].strip() if current_text.startswith(prefix) else ""
        window = tk.Toplevel(self.root)
        window.title("Editar Tecla")
        self.center_window(window, 400, 200)
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
    
    def edit_wait_event(self, event_label):
        current_text = event_label.cget("text")
        m = re.search(r"Esperar (\d+) segundos", current_text)
        existing = m.group(1) if m else ""
        window = tk.Toplevel(self.root)
        window.title("Editar Espera")
        self.center_window(window, 400, 150)
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
    
    def delete_selected_events(self, event=None):
        for widget in self.selected_events:
            if widget in self.events:
                self.events.remove(widget)
                widget.destroy()
        self.selected_events = []
        self.refresh_timeline()
    
    def move_selected_up(self):
        sel = sorted(self.selected_events, key=lambda w: self.events.index(w))
        for w in sel:
            idx = self.events.index(w)
            if idx > 0 and self.events[idx - 1] not in self.selected_events:
                self.events[idx], self.events[idx - 1] = self.events[idx - 1], self.events[idx]
        self.refresh_timeline()
    
    def move_selected_down(self):
        sel = sorted(self.selected_events, key=lambda w: self.events.index(w), reverse=True)
        for w in sel:
            idx = self.events.index(w)
            if idx < len(self.events) - 1 and self.events[idx + 1] not in self.selected_events:
                self.events[idx], self.events[idx + 1] = self.events[idx + 1], self.events[idx]
        self.refresh_timeline()
    
    def _save_text_edit(self, text_widget, window):
        full_text = text_widget.get("1.0", tk.END).rstrip("\n")
        single_line = " ".join(full_text.splitlines())
        summary = single_line if len(single_line) <= 40 else single_line[:40] + "..."
        event_label = tk.Label(self.scrollable_frame, text=f"Digitar: {summary}", bg="lightgray",
                                padx=10, pady=5, relief=tk.RIDGE)
        event_label.full_text = full_text
        event_label.pack(fill=tk.X, pady=2, expand=True)
        event_label.bind("<Button-1>", self.select_event)
        event_label.bind("<B1-Motion>", self.drag_event)
        event_label.bind("<Double-Button-1>", self.on_double_click_event)
        event_label.bind("<Enter>", lambda e: event_label.config(bg="gray"))
        event_label.bind("<Leave>", lambda e: event_label.config(bg="lightgray" if event_label not in self.selected_events else "darkgray"))
        self.events.append(event_label)
        window.destroy()
    
    def capture_mouse_click(self):
        capture_window = tk.Toplevel(self.root)
        capture_window.title("Capturar Clique")
        self.center_window(capture_window, 400, 200)
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
        self.center_window(text_window, 600, 400)
        text_window.attributes("-topmost", True)
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
    
    def add_key_event(self):
        key_window = tk.Toplevel(self.root)
        key_window.title("Adicionar Tecla")
        self.center_window(key_window, 400, 200)
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
        self.center_window(wait_window, 400, 150)
        wait_window.attributes("-topmost", True)
        lbl = tk.Label(wait_window, text="Digite o tempo em segundos e aperte ENTER ou clique em OK", padx=20, pady=10)
        lbl.pack(expand=True, fill=tk.BOTH)
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
        for event_label in self.events:
            text = event_label.cget("text")
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
    
    def execute_timeline_loop(self):
        loop_count = simpledialog.askinteger("Loop", "Digite a quantidade de loops:")
        if loop_count is None:
            return
        def loop_runner():
            self.stop_requested = False
            self.message_shown = False
            self.executing = True
            self.suppress_messages = True
            for i in range(loop_count):
                for file_path in self.loaded_lists:
                    self.loaded_index[file_path] = 0
                self.countdown_and_execute_sync(list(self.loaded_lists.keys()), current_loop=i+1, total_loops=loop_count)
                if self.stop_requested:
                    break
            self.suppress_messages = False
            if not self.stop_requested:
                self._show_message("Finalizado", "A macro foi executada em loop com sucesso.")
            self.executing = False
        threading.Thread(target=loop_runner).start()
    
    def show_countdown_and_execute(self, required_files, current_loop=None, total_loops=None):
        self.stop_requested = False
        self.executing = True
        countdown_window = tk.Toplevel(self.root)
        countdown_window.overrideredirect(True)
        countdown_window.attributes("-topmost", True)
        countdown_window.configure(bg="white")
        win_width, win_height = 250, 120
        # Centraliza a janela de countdown
        self.center_window(countdown_window, win_width, win_height)
        countdown_window.update_idletasks()
        
        frame = tk.Frame(countdown_window, bg="white")
        frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        if current_loop is not None and total_loops is not None:
            top_text = f"Começando Macro {current_loop} de {total_loops} em:"
        else:
            top_text = "Começando Macro em:"
        top_label = tk.Label(frame, text=top_text, font=("Arial", 12), bg="white")
        top_label.pack()
        number_label = tk.Label(frame, text="3", font=("Arial", 36), bg="white")
        number_label.pack()
        bottom_label = tk.Label(frame, text="Sacuda o mouse para abortar", font=("Arial", 12), bg="white")
        bottom_label.pack()
        
        shake_thread = threading.Thread(target=self._monitor_mouse_shake)
        shake_thread.daemon = True
        shake_thread.start()
        
        def update_count(count):
            if self.stop_requested:
                countdown_window.destroy()
                self.executing = False
                return
            number_label.config(text=str(count))
            if count > 0:
                countdown_window.after(1000, update_count, count - 1)
            else:
                countdown_window.destroy()
                exec_thread = threading.Thread(target=self._run_macro, args=(required_files,))
                exec_thread.start()
        update_count(3)
    
    def countdown_and_execute_sync(self, required_files, current_loop=None, total_loops=None):
        self.stop_requested = False
        self.executing = True
        countdown_window = tk.Toplevel(self.root)
        countdown_window.overrideredirect(True)
        countdown_window.attributes("-topmost", True)
        countdown_window.configure(bg="white")
        win_width, win_height = 250, 120
        self.center_window(countdown_window, win_width, win_height)
        countdown_window.update_idletasks()
        
        frame = tk.Frame(countdown_window, bg="white")
        frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        if current_loop is not None and total_loops is not None:
            top_text = f"Começando Macro {current_loop} de {total_loops} em:"
        else:
            top_text = "Começando Macro em:"
        top_label = tk.Label(frame, text=top_text, font=("Arial", 12), bg="white")
        top_label.pack()
        number_label = tk.Label(frame, text="3", font=("Arial", 36), bg="white")
        number_label.pack()
        bottom_label = tk.Label(frame, text="Sacuda o mouse para abortar", font=("Arial", 12), bg="white")
        bottom_label.pack()
        
        shake_thread = threading.Thread(target=self._monitor_mouse_shake)
        shake_thread.daemon = True
        shake_thread.start()
        
        for count in range(3, 0, -1):
            if self.stop_requested:
                countdown_window.destroy()
                self.executing = False
                return
            number_label.config(text=str(count))
            countdown_window.update()
            time.sleep(1)
        countdown_window.destroy()
        self._run_macro(required_files)
    
    def _run_macro(self, required_files):
        tem_lista = any(event_label.cget("text").startswith("Lista:") for event_label in self.events)
        if tem_lista:
            while (not self.stop_requested) and any(self.loaded_index[fname] < len(self.loaded_lists[fname]) for fname in required_files):
                for event_label in list(self.events):
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
            for event_label in list(self.events):
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
        if not self.suppress_messages and not self.message_shown:
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
            if abs(diff) > 50:
                shake_count += 1
            else:
                shake_count = max(0, shake_count - 1)
            last_x = current_x
            if shake_count >= 2:
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
    
    # Método auxiliar para centralizar uma janela Toplevel
    def center_window(self, win, width, height):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        win.geometry(f"{width}x{height}+{x}+{y}")
    
if __name__ == "__main__":
    root = tk.Tk()
    app = MacroApp(root)
    root.bind("<Delete>", lambda event: app.delete_selected_events(event))
    root.mainloop()
