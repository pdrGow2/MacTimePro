import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import threading
import time
import re
import os
import sys
import pyautogui
import ctypes # Para detecção global de teclas (Enter)

# Configuração para lidar com caminhos no executável ou script
def resource_path(relative_path):
    """Retorna o caminho absoluto para o arquivo, funcionando tanto em ambiente de desenvolvimento quanto no executável."""
    try:
        # Se estiver empacotado pelo PyInstaller
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def normalize_key(key):
    key = key.lower()
    mapping = {
        'alt_l': 'alt', 'alt_r': 'alt',
        'control_l': 'ctrl', 'control_r': 'ctrl',
        'ctrl_l': 'ctrl', 'ctrl_r': 'ctrl',
        'shift_l': 'shift', 'shift_r': 'shift'
    }
    return mapping.get(key, key)

# Classe auxiliar para tooltips
class CreateToolTip:
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.showtip)
        widget.bind("<Leave>", self.hidetip)

    def showtip(self, event=None):
        if self.tipwindow or not self.text: return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.configure(bg="#282828")
        tw.wm_geometry("+%d+%d" % (x, y))
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hidetip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw: tw.destroy()

# Função auxiliar para efeito hover
def add_hover_effect(widget, normal_bg, hover_bg):
    widget.bind("<Enter>", lambda e: widget.config(bg=hover_bg), add="+")
    widget.bind("<Leave>", lambda e: widget.config(bg=normal_bg), add="+")

class MacroApp:
    def __init__(self, root):
        self.root = root
        
        # --- CONFIGURAÇÕES GERAIS DO APP ---
        self.APP_NAME = "MacTime Pro"
        self.APP_VERSION = "v2.1"
        self.APP_AUTHOR = "pdrGow2"
        self.APP_DESC = (
            "Automação avançada com suporte a:\n"
            "• Captura de cliques, teclado e textos\n"
            "• Listas dinâmicas (.txt) com ignorar vazios\n"
            "• Loops e proteção contra falhas (Shake)\n"
            "• Edição completa via Timeline"
        )
        
        try: self.root.iconbitmap(resource_path("icone.ico"))
        except: pass 
        
        self.root.title(self.APP_NAME)
        self.root.configure(bg="#282828")
        self.root.geometry("940x450")
        
        # Variáveis de controle
        self.executing = False
        self.stop_requested = False
        self.interrupt_reason = None
        self.message_shown = False
        self.suppress_messages = False
        
        # Dados
        self.loaded_lists = {}
        self.loaded_index = {}
        self.list_settings = {} 
        self.events = []
        
        self.create_ui()

    def create_ui(self):
        # Botões superiores
        button_frame = tk.Frame(self.root, bg="#282828")
        button_frame.pack(fill=tk.X, pady=5)
        left_frame = tk.Frame(button_frame, bg="#282828")
        left_frame.pack(side=tk.LEFT, padx=10)
        right_frame = tk.Frame(button_frame, bg="#282828")
        right_frame.pack(side=tk.RIGHT, padx=10)
        
        def create_emoji_button(parent, emoji, cmd, tip, bg="#535353", fg="white", width=4, height=1, font=("Segoe UI Emoji", 20)):
            btn = tk.Button(parent, text=emoji, command=cmd, font=font,
                            width=width, height=height, relief=tk.FLAT, bd=0, bg=bg, fg=fg)
            CreateToolTip(btn, tip)
            add_hover_effect(btn, normal_bg=bg, hover_bg="#6e6e6e")
            return btn
        
        self.btn_capturar = create_emoji_button(left_frame, "🖱️", self.capture_mouse_click, "Captura um clique do mouse")
        self.btn_capturar.pack(side=tk.LEFT, padx=2)
        self.btn_texto = create_emoji_button(left_frame, "📝", self.add_text_event, "Adiciona um bloco de texto à timeline")
        self.btn_texto.pack(side=tk.LEFT, padx=2)
        self.btn_tecla = create_emoji_button(left_frame, "⌨️", self.add_key_event, "Adiciona uma sequência de teclas")
        self.btn_tecla.pack(side=tk.LEFT, padx=2)
        self.btn_espera = create_emoji_button(left_frame, "⏱️", self.add_wait_event, "Adiciona um tempo de espera")
        self.btn_espera.pack(side=tk.LEFT, padx=2)
        self.btn_apagar = create_emoji_button(left_frame, "🗑️", self.add_clear_event, "Apaga o evento")
        self.btn_apagar.pack(side=tk.LEFT, padx=2)
        self.btn_carregar = create_emoji_button(left_frame, "📋", self.load_timeline, "Carrega uma lista de um arquivo TXT")
        self.btn_carregar.pack(side=tk.LEFT, padx=2)
        
        # Mover itens
        move_frame = tk.Frame(left_frame, bg="#282828")
        move_frame.pack(side=tk.LEFT, padx=2)
        self.btn_move_up = create_emoji_button(move_frame, "⬆️", self.move_selected_up, "Mover para cima", font=("Segoe UI Emoji", 10))
        self.btn_move_up.pack(side=tk.TOP)
        self.btn_move_down = create_emoji_button(move_frame, "⬇️", self.move_selected_down, "Mover para baixo", font=("Segoe UI Emoji", 10))
        self.btn_move_down.pack(side=tk.TOP)
        
        self.btn_importar = create_emoji_button(right_frame, "📥", self.import_timeline, "Importa uma timeline de arquivo", bg="blue")
        self.btn_importar.pack(side=tk.LEFT, padx=2)
        self.btn_exportar = create_emoji_button(right_frame, "📤", self.export_timeline, "Exporta a timeline para arquivo", bg="purple")
        self.btn_exportar.pack(side=tk.LEFT, padx=2)
        self.btn_executar = create_emoji_button(right_frame, "▶️", self.execute_with_loops, "Executa a macro (ou loop)", bg="green")
        self.btn_executar.pack(side=tk.LEFT, padx=2)
        self.btn_parar = create_emoji_button(right_frame, "⏹️", self.stop_execution, "Interrompe a macro", bg="red")
        self.btn_parar.pack(side=tk.LEFT, padx=2)
        self.btn_about = create_emoji_button(right_frame, "❓", self.show_about, "Sobre este sistema")
        self.btn_about.pack(side=tk.LEFT, padx=2)

        # Timeline
        timeline_container = tk.Frame(self.root, bg="#808080")
        timeline_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.canvas = tk.Canvas(timeline_container, bg="#808080", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(timeline_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#808080")
        self.window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-1>", self.deselect_event)

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.window_id, width=event.width)

    def center_window(self, win, width, height):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.configure(bg="#282828")
        try: win.iconbitmap(resource_path("icone.ico"))
        except: pass
        
        # Torna a janela Modal (Bloqueia a principal)
        if win != self.root:
            win.transient(self.root)
            win.grab_set()
            win.focus_force()

    def show_about(self):
        about_win = tk.Toplevel(self.root)
        about_win.resizable(False, False)
        about_win.title(f"Sobre - {self.APP_NAME}")
        about_win.configure(bg="#282828")
        self.center_window(about_win, 400, 250)
        about_win.attributes("-topmost", True)
        
        try: tk.Label(about_win, text="🖱️", font=("Segoe UI Emoji", 40), bg="#282828", fg="white").pack(pady=(10, 0))
        except: pass

        tk.Label(about_win, text=self.APP_NAME, font=("Segoe UI", 14, "bold"), bg="#282828", fg="white").pack()
        tk.Label(about_win, text=f"Versão: {self.APP_VERSION}", font=("Segoe UI", 10), bg="#282828", fg="#A0A0A0").pack()
        tk.Label(about_win, text=f"Created by: {self.APP_AUTHOR}", font=("Segoe UI", 9), bg="#282828", fg="#808080").pack(pady=5)
        
        desc_frame = tk.Frame(about_win, bg="#333333", padx=10, pady=10)
        desc_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        tk.Label(desc_frame, text=self.APP_DESC, font=("Segoe UI", 9), justify="left", bg="#333333", fg="#E0E0E0").pack()

    def _on_mouse_wheel(self, event):
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def deselect_event(self, event): pass

    def select_event(self, event):
        lbl = event.widget
        ctrl_pressed = (event.state & 0x0004)
        if not ctrl_pressed:
            for item in self.events:
                if item["label"] != lbl:
                    item["checkvar"].set(False)
                    item["label"].config(bg="lightgray")
        for item in self.events:
            if item["label"] == lbl:
                if item["checkvar"].get():
                    item["checkvar"].set(False)
                    lbl.config(bg="lightgray")
                else:
                    item["checkvar"].set(True)
                    lbl.config(bg="darkgray")
                break

    def set_event_bg(self, frame, color):
        frame.config(bg=color)
        for child in frame.winfo_children():
            child.config(bg=color)

    def add_event(self, event_text):
        event_frame = tk.Frame(self.scrollable_frame, bg="lightgray")
        event_frame.pack(fill=tk.X, pady=2, expand=True)
        var = tk.BooleanVar(value=False)
        cb = tk.Checkbutton(event_frame, variable=var, bg="lightgray", bd=0, relief=tk.FLAT,
                             activebackground="lightgray", selectcolor="lightgray")
        cb.pack(side=tk.LEFT, padx=(2,5))
        lbl = tk.Label(event_frame, text=event_text, bg="lightgray", padx=10, pady=5,
                        bd=0, relief=tk.FLAT, anchor="w", fg="black")
        lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        lbl.bind("<Button-1>", self.select_event)
        event_frame.bind("<Enter>", lambda e: self.set_event_bg(event_frame, "#A0A0A0"))
        event_frame.bind("<Leave>", lambda e: self.set_event_bg(event_frame, "lightgray"))
        lbl.bind("<Double-Button-1>", self.on_double_click_event)
        event_frame.bind("<B1-Motion>", self.drag_event)
        item = {"frame": event_frame, "checkvar": var, "label": lbl, "text": event_text}
        self.events.append(item)

    def refresh_timeline(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.pack_forget()
        for item in self.events:
            item["frame"].pack(fill=tk.X, pady=2, expand=True)

    def delete_selected_events(self, event=None):
        to_delete = [item for item in self.events if item["checkvar"].get()]
        for item in to_delete:
            item["frame"].destroy()
            self.events.remove(item)
        self.refresh_timeline()

    def move_selected_up(self):
        sel = sorted([item for item in self.events if item["checkvar"].get()], key=lambda i: self.events.index(i))
        for item in sel:
            idx = self.events.index(item)
            if idx > 0 and not self.events[idx - 1]["checkvar"].get():
                self.events[idx], self.events[idx - 1] = self.events[idx - 1], self.events[idx]
        self.refresh_timeline()

    def move_selected_down(self):
        sel = sorted([item for item in self.events if item["checkvar"].get()], key=lambda i: self.events.index(i), reverse=True)
        for item in sel:
            idx = self.events.index(item)
            if idx < len(self.events) - 1 and not self.events[idx + 1]["checkvar"].get():
                self.events[idx], self.events[idx + 1] = self.events[idx + 1], self.events[idx]
        self.refresh_timeline()

    def drag_event(self, event):
        selected_items = [item for item in self.events if item["checkvar"].get()]
        if not selected_items: return
        y = event.y_root - self.scrollable_frame.winfo_rooty()
        remaining = [item for item in self.events if item not in selected_items]
        insert_index = 0
        for item in remaining:
            center = item["frame"].winfo_y() + item["frame"].winfo_height() / 2
            if center < y: insert_index += 1
        new_order = remaining[:insert_index] + selected_items + remaining[insert_index:]
        self.events = new_order
        self.refresh_timeline()

    def on_double_click_event(self, event):
        lbl = event.widget
        for item in self.events:
            if item["label"] == lbl:
                text = lbl.cget("text")
                if text.startswith("Clique") or text.startswith("Duplo") or text.startswith("Botão"):
                    self.edit_click_event(lbl)
                elif text.startswith("Digitar:"):
                    self.edit_text_event(lbl)
                elif text.startswith("Pressionar") or text.startswith("Manter") or text.startswith("Tecla"):
                    self.edit_key_event(lbl)
                elif text.startswith("Esperar"):
                    self.edit_wait_event(lbl)
                elif text.startswith("Lista:"):
                    self.edit_list_event(lbl)
                break

    # -------------------------------------------------------------------------
    #  HELPERS (JANELAS PADRONIZADAS)
    # -------------------------------------------------------------------------
    def _open_key_dialog(self, title, initial_mode="Simples", initial_keys=None, initial_duration="", on_confirm=None):
        window = tk.Toplevel(self.root)
        window.title(title)
        self.center_window(window, 450, 300)
        window.attributes("-topmost", True)
        
        key_combination = list(initial_keys) if initial_keys else []

        instr_label = tk.Label(window, text="Selecione o tipo e clique no campo abaixo para gravar as teclas.",
                               padx=20, pady=10, bg="#282828", fg="white", wraplength=400)
        instr_label.pack(fill=tk.X)
        
        radio_frame = tk.Frame(window, bg="#282828")
        radio_frame.pack(pady=10)
        
        key_option = tk.StringVar(value=initial_mode)
        def create_radio(parent, text, val):
            rb = tk.Radiobutton(parent, text=text, variable=key_option, value=val,
                           bg="#282828", fg="white", selectcolor="#444444", 
                           activebackground="#282828", activeforeground="white")
            rb.pack(side=tk.LEFT, padx=10)
            return rb

        create_radio(radio_frame, "Simples", "Simples")
        create_radio(radio_frame, "Manter", "Manter")
        create_radio(radio_frame, "Repetida", "Repetida")
        
        capture_frame = tk.Frame(window, bg="#282828")
        capture_frame.pack(pady=5)
        tk.Label(capture_frame, text="Combinação:", bg="#282828", fg="white", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=5)
        entry_display = tk.Entry(capture_frame, width=30, font=("Segoe UI", 10), justify="center",
                                 bg="#404040", fg="white", insertbackground="white", relief=tk.FLAT)
        entry_display.pack(side=tk.LEFT, padx=5)
        entry_display.insert(0, " + ".join(key_combination))
        
        btn_clear = tk.Button(capture_frame, text="🧹", 
                              command=lambda: (key_combination.clear(), entry_display.delete(0, tk.END)),
                              bg="#535353", fg="white", relief=tk.FLAT, bd=0, width=3)
        btn_clear.pack(side=tk.LEFT, padx=2)

        param_frame = tk.Frame(window, bg="#282828")
        param_label = tk.Label(param_frame, text="", bg="#282828", fg="white")
        param_label.pack(side=tk.LEFT)
        param_entry = tk.Entry(param_frame, width=10)
        param_entry.pack(side=tk.LEFT, padx=5)
        param_entry.insert(0, initial_duration)
        param_frame.pack_forget()
        
        def update_key_param(*args):
            opt = key_option.get()
            if opt == "Simples": param_frame.pack_forget()
            elif opt == "Manter": param_label.config(text="Duração (s):"); param_frame.pack(pady=5)
            elif opt == "Repetida": param_label.config(text="Repetir por (s):"); param_frame.pack(pady=5)
        key_option.trace("w", update_key_param)
        update_key_param() 
        
        def on_key_press(event):
            if event.keysym not in key_combination:
                key_combination.append(event.keysym)
            entry_display.delete(0, tk.END)
            entry_display.insert(0, " + ".join(key_combination))
            return "break"
        entry_display.bind("<KeyPress>", on_key_press)
        
        def save_action():
            opt = key_option.get()
            param = param_entry.get().strip() or "1.0"
            if key_combination:
                if on_confirm: on_confirm(opt, key_combination, param)
                window.destroy()
            else: messagebox.showwarning("Atenção", "Nenhuma tecla gravada!", parent=window)
        
        ok_button = tk.Button(window, text="OK", command=save_action,
                            bg="#535353", fg="white", font=("Segoe UI", 12, "bold"), width=15, bd=0)
        ok_button.pack(side=tk.BOTTOM, pady=15)
        entry_display.focus_set()

    def _open_text_dialog(self, title, initial_text="", on_confirm=None):
        window = tk.Toplevel(self.root)
        window.title(title)
        self.center_window(window, 600, 400)
        window.attributes("-topmost", True)
        window.grid_rowconfigure(0, weight=1)
        window.grid_columnconfigure(0, weight=1)
        
        text_frame = tk.Frame(window, bg="#282828")
        text_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set,
                              bg="white", fg="black", insertbackground="black", relief=tk.FLAT, bd=0)
        text_widget.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        scrollbar.config(command=text_widget.yview)
        text_widget.insert("1.0", initial_text)
        text_widget.focus_set()

        btn_frame = tk.Frame(window, bg="#282828")
        btn_frame.grid(row=1, column=0, sticky="ew", pady=10)
        
        def save_action():
            full_text = text_widget.get("1.0", tk.END).rstrip("\n")
            if on_confirm: on_confirm(full_text)
            window.destroy()

        tk.Button(btn_frame, text="OK", command=save_action,
                  bg="#535353", fg="white", font=("Segoe UI", 12), width=15, bd=0).pack()

    def _open_wait_dialog(self, title, initial_value="", on_confirm=None):
        window = tk.Toplevel(self.root)
        window.title(title)
        self.center_window(window, 400, 180)
        window.attributes("-topmost", True)
        
        tk.Label(window, text="Digite o tempo em segundos (decimais permitidos):",
                 padx=20, pady=15, bg="#282828", fg="white", font=("Segoe UI", 10)).pack(fill=tk.X)
        
        entry = tk.Entry(window, width=20, bg="white", fg="black", relief=tk.FLAT, bd=0, font=("Segoe UI", 12), justify="center")
        entry.pack(pady=5)
        entry.insert(0, initial_value)
        entry.focus_set()
        
        vcmd = (window.register(lambda P: bool(re.match(r'^[0-9]*\.?[0-9]*$', P))), '%P')
        entry.config(validate='key', validatecommand=vcmd)
        
        def save_action(e=None):
            val = entry.get()
            if val.strip():
                if on_confirm: on_confirm(val)
                window.destroy()
        entry.bind("<Return>", save_action)
        tk.Button(window, text="OK", command=save_action, bg="#535353", fg="white", width=15, bd=0).pack(pady=15)

    def _open_mouse_dialog(self, title, initial_mode="Simples", initial_param="", on_confirm=None):
        window = tk.Toplevel(self.root)
        window.title(title)
        self.center_window(window, 400, 450)
        window.attributes("-topmost", True)
        
        tk.Label(window, text="Posicione o mouse e aperte ENTER para confirmar.", 
                 padx=20, pady=10, bg="#282828", fg="#A0A0A0", font=("Segoe UI", 10)).pack(fill=tk.X)
        
        btn_var = tk.StringVar(value="Esquerdo")
        type_var = tk.StringVar(value="Simples")
        
        if "Direito" in initial_mode: btn_var.set("Direito")
        elif "Scroll" in initial_mode: btn_var.set("Scroll")
        
        if "Duplo" in initial_mode: type_var.set("Duplo")
        elif "Pressionar" in initial_mode: type_var.set("Pressionar")
        elif "Repetido" in initial_mode: type_var.set("Repetido")

        tk.Label(window, text="Botão", bg="#282828", fg="white", font=("Segoe UI", 10, "bold")).pack(pady=(5, 0))
        btn_frame = tk.Frame(window, bg="#282828")
        btn_frame.pack(pady=5)
        
        def create_radio(parent, text, variable, val):
            tk.Radiobutton(parent, text=text, variable=variable, value=val,
                           bg="#282828", fg="white", selectcolor="#444444", 
                           activebackground="#282828", activeforeground="white").pack(side=tk.LEFT, padx=5)

        create_radio(btn_frame, "Esquerdo", btn_var, "Esquerdo")
        create_radio(btn_frame, "Scroll", btn_var, "Scroll")
        create_radio(btn_frame, "Direito", btn_var, "Direito")

        tk.Label(window, text="Tipo de clique", bg="#282828", fg="white", font=("Segoe UI", 10, "bold")).pack(pady=(10, 0))
        type_frame = tk.Frame(window, bg="#282828")
        type_frame.pack(pady=5)
        
        create_radio(type_frame, "Simples", type_var, "Simples")
        create_radio(type_frame, "Pressionar", type_var, "Pressionar")
        create_radio(type_frame, "Repetido", type_var, "Repetido")
        create_radio(type_frame, "Duplo", type_var, "Duplo")

        param_frame = tk.Frame(window, bg="#282828")
        param_label = tk.Label(param_frame, text="", bg="#282828", fg="white")
        param_label.pack(side=tk.LEFT)
        param_entry = tk.Entry(param_frame, width=8, justify="center")
        param_entry.pack(side=tk.LEFT, padx=5)
        param_entry.insert(0, initial_param)
        
        def update_ui_state(*args):
            tipo = type_var.get()
            if tipo == "Pressionar":
                param_label.config(text="Duração (s):")
                param_frame.pack(pady=10)
            elif tipo == "Repetido":
                param_label.config(text="Repetir por (s):")
                param_frame.pack(pady=10)
            else:
                param_frame.pack_forget()

        type_var.trace("w", update_ui_state)
        btn_var.trace("w", update_ui_state)
        update_ui_state()

        coord_frame = tk.Frame(window, bg="#282828", bd=1, relief=tk.SOLID)
        coord_frame.pack(pady=20, ipadx=10, ipady=5)
        coord_label = tk.Label(coord_frame, text="X: 0   Y: 0", bg="#282828", fg="#00FF00", font=("Consolas", 16, "bold"))
        coord_label.pack()

        self._capturing = True 

        def confirm_action(event=None):
            self._capturing = False
            x, y = pyautogui.position()
            btn = btn_var.get()
            tipo = type_var.get()
            param = param_entry.get().strip() or "1.0"
            
            mode_str = "Simples"
            if btn == "Esquerdo":
                if tipo == "Simples": mode_str = "Simples"
                elif tipo == "Duplo": mode_str = "Duplo Clique"
                elif tipo == "Pressionar": mode_str = "Pressionar"
                elif tipo == "Repetido": mode_str = "Repetido"
            elif btn == "Direito": mode_str = "Botão Direito"
            elif btn == "Scroll": mode_str = "Scroll"
                
            if on_confirm: on_confirm(x, y, mode_str, param)
            window.destroy()

        def update_position_loop():
            if not window.winfo_exists() or not self._capturing: return
            try:
                if ctypes.windll.user32.GetAsyncKeyState(0x0D) & 0x8000:
                    window.after(50, confirm_action)
                    return
                x, y = pyautogui.position()
                coord_label.config(text=f"X: {x}   Y: {y}")
            except Exception: pass
            window.after(50, update_position_loop)
        
        update_position_loop()
        window.bind("<Return>", confirm_action)
        
        ok_btn = tk.Button(window, text="Gravar Posição Atual (ENTER)", command=confirm_action,
                           bg="#535353", fg="white", font=("Segoe UI", 10, "bold"), bd=0, height=2)
        ok_btn.pack(fill=tk.X, side=tk.BOTTOM, padx=20, pady=15)
        ok_btn.focus_set()

    def _open_list_dialog(self, title, initial_path="", initial_ignore=False, on_confirm=None):
        win = tk.Toplevel(self.root)
        win.title(title)
        self.center_window(win, 450, 220)
        win.attributes("-topmost", True)
        
        selected_file = tk.StringVar(value=initial_path)
        ignore_blank = tk.BooleanVar(value=initial_ignore)

        file_frame = tk.Frame(win, bg="#282828")
        file_frame.pack(fill=tk.X, padx=20, pady=20)
        tk.Label(file_frame, text="Arquivo selecionado:", bg="#282828", fg="white", anchor="w").pack(fill=tk.X)
        tk.Entry(file_frame, textvariable=selected_file, bg="#404040", fg="white", relief=tk.FLAT).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        
        def browse_file():
            path = filedialog.askopenfilename(parent=win, filetypes=[("Text Files", "*.txt")])
            if path: selected_file.set(path)
        
        tk.Button(file_frame, text="📂", command=browse_file, bg="#535353", fg="white", bd=0, width=4).pack(side=tk.RIGHT, padx=(5, 0))

        check_frame = tk.Frame(win, bg="#282828")
        check_frame.pack(fill=tk.X, padx=20)
        tk.Checkbutton(check_frame, text="Ignorar linhas em branco", variable=ignore_blank,
                       bg="#282828", fg="white", selectcolor="#444444", 
                       activebackground="#282828", activeforeground="white",
                       onvalue=True, offvalue=False).pack(anchor="w")
        
        def confirm_action():
            file_path = selected_file.get()
            if not file_path or not os.path.exists(file_path):
                messagebox.showwarning("Atenção", "Selecione um arquivo válido.", parent=win)
                return
            
            if on_confirm:
                # Tenta executar a ação. Se der certo, espera receber uma STRING de sucesso.
                success_message = on_confirm(file_path, ignore_blank.get())
                
                if success_message:
                    # 1. Fecha a janela IMEDIATAMENTE
                    win.destroy()
                    self.root.update() # Força atualização visual
                    
                    # 2. Mostra a mensagem DEPOIS
                    messagebox.showinfo("Sucesso", success_message, parent=self.root)

        tk.Button(win, text="Salvar", command=confirm_action,
                  bg="#535353", fg="white", font=("Segoe UI", 10, "bold"), bd=0, height=2).pack(fill=tk.X, side=tk.BOTTOM, padx=20, pady=20)
         
    # -------------------------------------------------------------------------
    #  IMPLEMENTAÇÃO DAS AÇÕES (ADD/EDIT)
    # -------------------------------------------------------------------------
    def add_key_event(self):
        def on_save(mode, keys, duration):
            combo_str = "+".join(keys)
            if mode == "Simples": self.add_event(f"Pressionar Tecla: {combo_str}")
            elif mode == "Manter": self.add_event(f"Manter pressionada: {combo_str} - Duração: {duration}s")
            elif mode == "Repetida": self.add_event(f"Tecla repetida: {combo_str} - Repetir por: {duration}s")
        self._open_key_dialog("Adicionar Tecla", on_confirm=on_save)

    def edit_key_event(self, event_label):
        current = event_label.cget("text")
        mode, keys_str, dur = "Simples", "", ""
        if " - Duração: " in current:
            mode = "Manter"
            keys_str = current.split(" - Duração: ")[0].replace("Manter pressionada: ", "")
            dur = current.split(" - Duração: ")[1].replace("s", "").strip()
        elif " - Repetir por: " in current:
            mode = "Repetida"
            keys_str = current.split(" - Repetir por: ")[0].replace("Tecla repetida: ", "")
            dur = current.split(" - Repetir por: ")[1].replace("s", "").strip()
        elif current.startswith("Pressionar Tecla:"):
            keys_str = current.replace("Pressionar Tecla: ", "")
        else: keys_str = current
        initial_keys = keys_str.split("+") if keys_str else []

        def on_update(mode, keys, duration):
            combo_str = "+".join(keys)
            new_text = ""
            if mode == "Simples": new_text = f"Pressionar Tecla: {combo_str}"
            elif mode == "Manter": new_text = f"Manter pressionada: {combo_str} - Duração: {duration}s"
            elif mode == "Repetida": new_text = f"Tecla repetida: {combo_str} - Repetir por: {duration}s"
            event_label.config(text=new_text)
        self._open_key_dialog("Editar Tecla", initial_mode=mode, initial_keys=initial_keys, initial_duration=dur, on_confirm=on_update)

    def add_text_event(self):
        def on_save(full_text):
            if full_text.strip():
                single_line = " ".join(full_text.splitlines())
                summary = single_line if len(single_line) <= 40 else single_line[:40] + "..."
                self.add_event(f"Digitar: {summary}")
                self.events[-1]["label"].full_text = full_text
        self._open_text_dialog("Adicionar Texto", on_confirm=on_save)

    def edit_text_event(self, event_label):
        if hasattr(event_label, "full_text"): full_text = event_label.full_text
        else: full_text = event_label.cget("text").replace("Digitar:", "").strip()
        
        def on_update(new_text):
            single_line = " ".join(new_text.splitlines())
            summary = single_line if len(single_line) <= 40 else single_line[:40] + "..."
            event_label.config(text=f"Digitar: {summary}")
            event_label.full_text = new_text
        self._open_text_dialog("Editar Texto", initial_text=full_text, on_confirm=on_update)

    def add_wait_event(self):
        def on_save(time_val): self.add_event(f"Esperar {time_val} segundos")
        self._open_wait_dialog("Adicionar Espera", on_confirm=on_save)

    def edit_wait_event(self, event_label):
        m = re.search(r"Esperar (\d+\.?\d*) segundos", event_label.cget("text"))
        existing = m.group(1) if m else ""
        def on_update(new_val): event_label.config(text=f"Esperar {new_val} segundos")
        self._open_wait_dialog("Editar Espera", initial_value=existing, on_confirm=on_update)

    def capture_mouse_click(self):
        def on_save(x, y, mode, param):
            if mode == "Simples": self.add_event(f"Clique Simples em ({x}, {y})")
            elif mode == "Duplo Clique": self.add_event(f"Duplo Clique em ({x}, {y})")
            elif mode == "Botão Direito": self.add_event(f"Botão Direito em ({x}, {y})")
            elif mode == "Pressionar": self.add_event(f"Pressionar por tempo em ({x}, {y}) - Duração: {param}s")
            elif mode == "Repetido": self.add_event(f"Clique repetido em ({x}, {y}) - Repetir por: {param}s")
        self._open_mouse_dialog("Capturar Clique", on_confirm=on_save)

    def edit_click_event(self, event_label):
        text = event_label.cget("text")
        mode, param = "Simples", ""
        if "Pressionar por tempo" in text: mode = "Pressionar"; param = text.split(" - Duração: ")[1].replace("s", "")
        elif "Clique repetido" in text: mode = "Repetido"; param = text.split(" - Repetir por: ")[1].replace("s", "")
        elif "Duplo Clique" in text: mode = "Duplo Clique"
        elif "Botão Direito" in text: mode = "Botão Direito"
        
        def on_update(x, y, mode, param):
            new_text = ""
            if mode == "Simples": new_text = f"Clique Simples em ({x}, {y})"
            elif mode == "Duplo Clique": new_text = f"Duplo Clique em ({x}, {y})"
            elif mode == "Botão Direito": new_text = f"Botão Direito em ({x}, {y})"
            elif mode == "Pressionar": new_text = f"Pressionar por tempo em ({x}, {y}) - Duração: {param}s"
            elif mode == "Repetido": new_text = f"Clique repetido em ({x}, {y}) - Repetir por: {param}s"
            event_label.config(text=new_text)
        self._open_mouse_dialog("Editar Clique", initial_mode=mode, initial_param=param, on_confirm=on_update)

    def add_clear_event(self): self.add_event("Apagar Campo")

    def load_timeline(self):
        def on_save(file_path, should_ignore):
            try:
                with open(file_path, "r") as file: lines = file.read().splitlines()
                if should_ignore:
                    items = [line.strip() for line in lines if line.strip()]
                else:
                    items = [line.strip() for line in lines]
                
                if items is not None:
                    full_path = os.path.abspath(file_path)
                    self.loaded_lists[full_path] = items
                    self.loaded_index[full_path] = 0
                    self.list_settings[full_path] = should_ignore
                    
                    if not any(i["label"].cget("text") == f"Lista: {full_path}" for i in self.events):
                        self.add_event(f"Lista: {full_path}")
                    
                    msg_extra = " (ignorando vazias)" if should_ignore else " (incluindo vazias)"
                    
                    # RETORNA A MENSAGEM (Não exibe aqui para não travar)
                    return f"Arquivo carregado com {len(items)} itens{msg_extra}."
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao ler arquivo: {e}", parent=self.root)
                return False
                
        self._open_list_dialog("Carregar Lista", on_confirm=on_save)

    def edit_list_event(self, event_label):
        path = event_label.cget("text").split("Lista:")[1].strip()
        setting = self.list_settings.get(path, False)
        
        def on_update(new_path, new_ignore):
            try:
                with open(new_path, "r") as file: lines = file.read().splitlines()
                if new_ignore:
                    items = [line.strip() for line in lines if line.strip()]
                else:
                    items = [line.strip() for line in lines]
                
                full_path = os.path.abspath(new_path)
                self.loaded_lists[full_path] = items
                self.loaded_index[full_path] = 0
                self.list_settings[full_path] = new_ignore
                
                event_label.config(text=f"Lista: {full_path}")
                
                msg_extra = " (ignorando vazias)" if new_ignore else " (incluindo vazias)"
                
                # RETORNA A MENSAGEM
                return f"Lista atualizada. {len(items)} itens carregados{msg_extra}."
            except Exception as e:
                messagebox.showerror("Erro", f"{e}", parent=self.root)
                return False
                
        self._open_list_dialog("Editar Lista", initial_path=path, initial_ignore=setting, on_confirm=on_update)

    def import_timeline(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if file_path:
            try:
                with open(file_path, "r") as file: lines = file.readlines()
                for widget in self.scrollable_frame.winfo_children(): widget.destroy()
                self.events = []
                self.list_settings = {}
                i = 0
                while i < len(lines):
                    line = lines[i].rstrip("\n")
                    if line.startswith("Lista:"):
                        if " | ignore=" in line:
                            parts = line.split(" | ignore=")
                            path = parts[0].replace("Lista: ", "").strip()
                            self.list_settings[path] = (parts[1].strip() == "True")
                            self.add_event(f"Lista: {path}")
                        else: self.add_event(line.strip())
                    elif line.startswith("Digitar: <<START>>"):
                        full_text_lines = []
                        i += 1
                        while i < len(lines) and lines[i].strip() != "<<END>>":
                            full_text_lines.append(lines[i].rstrip("\n"))
                            i += 1
                        full_text = "\n".join(full_text_lines)
                        single = " ".join(full_text.splitlines())
                        summary = single if len(single) <= 40 else single[:40] + "..."
                        self.add_event("Digitar: " + summary)
                        self.events[-1]["label"].full_text = full_text
                    else:
                        if line.strip(): self.add_event(line.strip())
                    i += 1
                messagebox.showinfo("Importar", f"Timeline importada.")
            except Exception as e: messagebox.showerror("Erro", f"{e}")
    
    def export_timeline(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if file_path:
            try:
                with open(file_path, "w") as file:
                    for item in self.events:
                        text = item["label"].cget("text")
                        if text.startswith("Lista:"):
                            clean_path = text.split("Lista:")[1].strip()
                            ignore = self.list_settings.get(clean_path, False)
                            file.write(f"Lista: {clean_path} | ignore={ignore}\n")
                        elif text.startswith("Digitar:") and hasattr(item["label"], "full_text"):
                            file.write("Digitar: <<START>>\n" + item["label"].full_text + "\n<<END>>\n")
                        else: file.write(text + "\n")
                messagebox.showinfo("Exportar", f"Timeline exportada.")
            except Exception as e: messagebox.showerror("Erro", f"{e}")

    # -------------------- Execução Blindada --------------------
    def execute_with_loops(self):
        loop_win = tk.Toplevel(self.root)
        loop_win.title("Execução em Loop")
        self.center_window(loop_win, 300, 180)
        loop_win.attributes("-topmost", True)
        result = {"count": None}
        tk.Label(loop_win, text="Quantas vezes repetir a macro?", bg="#282828", fg="white", font=("Segoe UI", 11), pady=10).pack()
        entry = tk.Entry(loop_win, width=10, justify="center", font=("Segoe UI", 12))
        entry.insert(0, "1")
        entry.pack(pady=5)
        entry.focus_set()
        entry.select_range(0, tk.END)
        
        def on_confirm(event=None):
            if entry.get().isdigit() and int(entry.get()) > 0:
                result["count"] = int(entry.get())
                loop_win.destroy()
            else: messagebox.showwarning("Inválido", "Digite um número maior que 0.", parent=loop_win)
        loop_win.bind("<Return>", on_confirm)
        btn_frame = tk.Frame(loop_win, bg="#282828")
        btn_frame.pack(pady=15)
        tk.Button(btn_frame, text="Iniciar", command=on_confirm, bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"), bd=0, padx=15).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Cancelar", command=loop_win.destroy, bg="#f44336", fg="white", font=("Segoe UI", 10), bd=0, padx=10).pack(side=tk.LEFT, padx=10)
        self.root.wait_window(loop_win)
        
        if result["count"] is None: return 
        self.prepare_and_start(total_loops=result["count"])

    def execute_timeline(self):
        if self.executing: return messagebox.showwarning("Atenção", "Macro já está em execução!")
        self.prepare_and_start(total_loops=1)

    def prepare_and_start(self, total_loops):
        required_files = set()
        for item in self.events:
            if item["label"].cget("text").startswith("Lista:"):
                required_files.add(item["label"].cget("text").split("Lista:")[1].strip())
        
        for path in required_files:
            if os.path.exists(path):
                try:
                    with open(path, "r") as f: lines = f.read().splitlines()
                    ignore = self.list_settings.get(path, False)
                    if ignore: self.loaded_lists[path] = [l.strip() for l in lines if l.strip()]
                    else: self.loaded_lists[path] = [l.strip() for l in lines]
                    self.loaded_index[path] = 0
                except Exception as e: return messagebox.showerror("Erro", f"Erro ao carregar '{path}': {e}")
            else: return messagebox.showerror("Erro", f"Lista '{path}' não encontrada.")

        self.stop_requested = False
        self.interrupt_reason = None
        self.executing = True
        self.message_shown = False
        self.start_visual_countdown(required_files, total_loops)

    def start_visual_countdown(self, required_files, total_loops):
        cw = tk.Toplevel(self.root)
        cw.overrideredirect(True)
        cw.configure(bg="white")
        cw.attributes("-topmost", True)
        self.center_window(cw, 300, 150)
        cw.configure(bg="white")
        cw.focus_force()
        
        frame = tk.Frame(cw, bg="white")
        frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        
        lbl_top = tk.Label(frame, text=f"Iniciando {total_loops} Repetições em:", font=("Segoe UI", 14), bg="white", fg="#333333")
        lbl_top.pack()
        lbl_num = tk.Label(frame, text="3", font=("Segoe UI", 48, "bold"), bg="white", fg="#FF5722")
        lbl_num.pack()
        tk.Label(frame, text="Sacuda o mouse para cancelar", font=("Segoe UI", 10, "italic"), bg="white", fg="#999999").pack()
        
        shake_thread = threading.Thread(target=self._monitor_mouse_shake)
        shake_thread.daemon = True
        shake_thread.start()
        
        def check_abort_ui():
            if self.stop_requested:
                cw.destroy()
                self.executing = False
                return
            if cw.winfo_exists(): cw.after(50, check_abort_ui)
        check_abort_ui()

        def update_timer(count):
            if not cw.winfo_exists(): return
            if self.stop_requested: return
            try: cw.lift(); cw.attributes("-topmost", True)
            except: pass
            lbl_num.config(text=str(count))
            if count > 0:
                cw.after(1000, update_timer, count - 1)
            else:
                cw.destroy()
                threading.Thread(target=self._worker_thread, args=(required_files, total_loops)).start()
        update_timer(3)

    def _worker_thread(self, required_files, total_loops):
        for i in range(total_loops):
            if self.stop_requested: break
            for path in required_files:
                if path in self.loaded_lists: self.loaded_index[path] = 0
            
            self._run_timeline_logic(required_files)
            if i < total_loops - 1: time.sleep(0.5)

        self.executing = False
        if not self.stop_requested and not self.message_shown:
            self._show_message("Finalizado", "Macro executada com sucesso.")

    def _run_timeline_logic(self, required_files):
        tem_lista = any("Lista:" in item["label"].cget("text") for item in self.events)
        if tem_lista:
            while (not self.stop_requested) and any(self.loaded_index[f] < len(self.loaded_lists[f]) for f in required_files):
                for item in list(self.events):
                    if self.stop_requested: return
                    self._execute_event_action(item)
        else:
            for item in list(self.events):
                if self.stop_requested: return
                self._execute_event_action(item)

    def _execute_event_action(self, item):
        if self.stop_requested: return
        text = item["label"].cget("text")
        
        if " em (" in text and ("Clique" in text or "Botão" in text or "Scroll" in text or "Pressionar por" in text):
            match = re.search(r"\((\d+),\s*(\d+)\)", text)
            if not match: return
            x, y = int(match.group(1)), int(match.group(2))
            if text.startswith("Botão Direito"): pyautogui.click(x, y, button="right")
            elif text.startswith("Duplo Clique"): pyautogui.doubleClick(x, y)
            elif text.startswith("Scroll"): pyautogui.click(x, y, button="middle")
            elif text.startswith("Pressionar por tempo"):
                d = float(re.search(r"Duração: (\d+\.?\d*)s", text).group(1))
                pyautogui.mouseDown(x, y); time.sleep(d); pyautogui.mouseUp(x, y)
            elif text.startswith("Clique repetido"):
                d = float(re.search(r"Repetir por: (\d+\.?\d*)s", text).group(1))
                end = time.time() + d
                while time.time() < end:
                    if self.stop_requested: break
                    pyautogui.click(x, y); time.sleep(0.1)
            else: pyautogui.click(x, y)
            time.sleep(0.2)
        elif text.startswith("Digitar:"):
            full_text = item["label"].full_text if hasattr(item["label"], "full_text") else text.replace("Digitar:", "").strip()
            pyautogui.write(full_text); time.sleep(0.2)
        elif "Tecla" in text or "pressionada:" in text:
            if text.startswith("Pressionar Tecla:"):
                keys = [normalize_key(k) for k in text.replace("Pressionar Tecla: ", "").strip().split("+")]
                pyautogui.hotkey(*keys)
            elif text.startswith("Manter pressionada:"):
                parts = text.split(" - Duração: ")
                dur = float(parts[1].replace("s", "").strip())
                keys = [normalize_key(k) for k in parts[0].replace("Manter pressionada: ", "").split("+")]
                for k in keys: pyautogui.keyDown(k)
                time.sleep(dur)
                for k in reversed(keys): pyautogui.keyUp(k)
            elif text.startswith("Tecla repetida:"):
                parts = text.split(" - Repetir por: ")
                dur = float(parts[1].replace("s", "").strip())
                keys = [normalize_key(k) for k in parts[0].replace("Tecla repetida: ", "").split("+")]
                end = time.time() + dur
                while time.time() < end:
                    if self.stop_requested: break
                    pyautogui.hotkey(*keys); time.sleep(0.1)
            time.sleep(0.2)
        elif text.startswith("Esperar"):
            sec = float(re.search(r"Esperar (\d+\.?\d*) segundos", text).group(1))
            for _ in range(int(sec * 10)):
                if self.stop_requested: break
                time.sleep(0.1)
        elif text.startswith("Apagar Campo"):
            pyautogui.hotkey('ctrl', 'a'); pyautogui.press('backspace'); time.sleep(0.2)
        elif text.startswith("Lista:"):
            path = text.split("Lista:")[1].strip()
            if path in self.loaded_lists and self.loaded_index[path] < len(self.loaded_lists[path]):
                pyautogui.write(self.loaded_lists[path][self.loaded_index[path]])
                self.loaded_index[path] += 1; time.sleep(0.2)

    def _monitor_mouse_shake(self):
        last_pos = pyautogui.position()
        shake_score = 0
        last_x_dir, last_y_dir = 0, 0
        min_movement, max_score, decay_rate = 100, 4, 0.1
        
        try:
            while self.executing and not self.stop_requested:
                time.sleep(0.05)
                try: current_pos = pyautogui.position()
                except: continue
                
                dx, dy = current_pos.x - last_pos.x, current_pos.y - last_pos.y
                moved_brusquely = False

                if abs(dx) > min_movement:
                    current_x_dir = 1 if dx > 0 else -1
                    if current_x_dir != last_x_dir and last_x_dir != 0:
                        shake_score += 1; moved_brusquely = True
                    last_x_dir = current_x_dir
                
                if abs(dy) > min_movement:
                    current_y_dir = 1 if dy > 0 else -1
                    if current_y_dir != last_y_dir and last_y_dir != 0:
                        shake_score += 1; moved_brusquely = True
                    last_y_dir = current_y_dir

                if not moved_brusquely and shake_score > 0:
                    shake_score = max(0, shake_score - decay_rate)

                last_pos = current_pos
                if shake_score >= max_score:
                    self.interrupt_reason = "Macro interrompida por sacudir o mouse."
                    self.stop_requested = True
                    self._show_message("Interrompido", self.interrupt_reason)
                    break
        except Exception as e: print(f"Erro monitor: {e}")
    
    def stop_execution(self):
        if not self.stop_requested: self.interrupt_reason = "Interrompido pelo usuário."
        self.stop_requested = True
        self._show_message("Interrompido", self.interrupt_reason)
    
    def _show_message(self, title, message):
        if not self.message_shown:
            self.message_shown = True
            self.root.after(0, lambda: messagebox.showinfo(title, message, parent=self.root))

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    
    app = MacroApp(root)
    root.bind("<Delete>", lambda event: app.delete_selected_events(event))
    
    splash = tk.Toplevel(root)
    splash.overrideredirect(True)
    splash.configure(bg="#282828")
    w, h = 350, 220
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    splash.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
    
    try: tk.Label(splash, text="🖱️", font=("Segoe UI Emoji", 60), bg="#282828", fg="white").pack(pady=(15, 0))
    except: pass
    tk.Label(splash, text=app.APP_NAME, font=("Segoe UI", 18, "bold"), bg="#282828", fg="white").pack()
    tk.Label(splash, text=app.APP_VERSION, font=("Segoe UI", 10), bg="#282828", fg="#A0A0A0").pack()
    tk.Label(splash, text=f"Created by: {app.APP_AUTHOR}", font=("Segoe UI", 9), bg="#282828", fg="#808080").pack(pady=(5, 0))
    tk.Label(splash, text="Carregando sistema...", font=("Segoe UI", 8, "italic"), bg="#282828", fg="#606060").pack(side=tk.BOTTOM, pady=10)
    splash.update()

    def start_main_window():
        splash.destroy()
        root.deiconify()
    
    root.after(2500, start_main_window)
    root.mainloop()