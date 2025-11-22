import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import threading
import time
import re
import pyautogui
import os
import sys

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

# Classe auxiliar para tooltips
class CreateToolTip:
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
        tw.configure(bg="#282828")
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

# Função auxiliar para efeito hover
def add_hover_effect(widget, normal_bg, hover_bg):
    widget.bind("<Enter>", lambda e: widget.config(bg=hover_bg), add="+")
    widget.bind("<Leave>", lambda e: widget.config(bg=normal_bg), add="+")

class MacroApp:
    def __init__(self, root):
        self.root = root
        self.root.iconbitmap(resource_path("icone.ico"))
        self.root.title("MacTime Pro")
        self.root.configure(bg="#282828")
        self.root.geometry("940x400")
        
        # Variáveis de controle
        self.executing = False
        self.stop_requested = False
        self.interrupt_reason = None
        self.message_shown = False
        self.suppress_messages = False
        
        # Dicionários para listas carregadas
        self.loaded_lists = {}
        self.loaded_index = {}
        
        # Lista de eventos – cada evento é um dicionário com chaves: frame, checkvar, label e text
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
        
        # Botões para mover itens (um para cima e um para baixo)
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

        
        # Área da timeline
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

    # Para janelas de edição ou captura, usa fundo "#282828" (preto mais claro)
    def center_window(self, win, width, height):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        win.geometry(f"{width}x{height}+{x}+{y}")
        if "Editar" in win.title() or "Capturar" in win.title():
            win.configure(bg="#282828")
        else:
            win.configure(bg="#282828")

    def show_about(self):
        about_win = tk.Toplevel(self.root)
        about_win.resizable(False, False)  # Impede redimensionamento e maximização
        about_win.title("Sobre")
        about_win.configure(bg="#282828")
        self.center_window(about_win, 500, 300)
        about_win.attributes("-topmost", True)
        info = (
            "MacroApp - Automação por Timeline\n"
            "Versão 1.0\n\n"
            "Funcionalidades:\n"
            "  - Capturar cliques, adicionar textos, teclas, esperas, apagar campo\n"
            "  - Suporte a listas (importação/exportação)\n"
            "  - Execução com contagem regressiva e monitor de sacudir o mouse\n"
            "  - Modo de execução em loop\n\n"
            "Atalhos:\n"
            "  * Clique simples: seleciona/deseleciona (exclusivo, salvo CTRL para múltipla)\n"
            "  * Se um item estiver selecionado, clicar em outro substitui a seleção\n"
            "  * Utilize os botões de seta para mover os itens selecionados\n"
            "  * Duplo clique: edita o item"
        )
        label = tk.Label(about_win, text=info, font=("Arial", 10), justify="left", bg="#282828", fg="white")
        label.pack(padx=10, pady=10, expand=True, fill=tk.BOTH)

    def _on_mouse_wheel(self, event):
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    def deselect_event(self, event):
        pass

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

    def on_double_click_event(self, event):
        lbl = event.widget
        for item in self.events:
            if item["label"] == lbl:
                text = lbl.cget("text")
                if text.startswith("Clique"):
                    self.edit_click_event(lbl)
                elif text.startswith("Digitar:"):
                    self.edit_text_event(lbl)
                elif text.startswith("Pressionar Tecla:"):
                    self.edit_key_event(lbl)
                elif text.startswith("Esperar"):
                    self.edit_wait_event(lbl)
                break

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
        if not selected_items:
            return
        y = event.y_root - self.scrollable_frame.winfo_rooty()
        remaining = [item for item in self.events if item not in selected_items]
        insert_index = 0
        for item in remaining:
            center = item["frame"].winfo_y() + item["frame"].winfo_height() / 2
            if center < y:
                insert_index += 1
        new_order = remaining[:insert_index] + selected_items + remaining[insert_index:]
        self.events = new_order
        self.refresh_timeline()

    def edit_click_event(self, event_label):
        current = event_label.cget("text")
        try:
            tipo_atual, coords = current.split(" em ", 1)
        except ValueError:
            tipo_atual = "Clique Simples"
            coords = "(0, 0)"
        window = tk.Toplevel(self.root)
        window.title("Editar Clique")
        self.center_window(window, 400, 200)
        window.attributes("-topmost", True)
        pos_label = tk.Label(window, text="Mova o mouse e aperte ENTER", padx=20, pady=10, bg="#282828", fg="white")
        pos_label.pack(expand=True, fill=tk.BOTH)
        radio_frame = tk.Frame(window, bg="#282828")
        radio_frame.pack(pady=5)
        click_type_var = tk.StringVar(value=tipo_atual.strip())
        selected_label = tk.Label(window, text=f"Tipo selecionado: {click_type_var.get()}", bg="#282828", fg="white")
        selected_label.pack()
        def update_radio():
            selected_label.config(text=f"Tipo selecionado: {click_type_var.get()}")
        for op in ["Clique Simples", "Duplo Clique", "Botão Direito", "Scroll"]:
            rb = tk.Radiobutton(radio_frame, text=op, variable=click_type_var, value=op,
                                bg="#282828", fg="white", relief=tk.FLAT, selectcolor="#444444",
                                command=update_radio)
            rb.pack(anchor="w")
            add_hover_effect(rb, normal_bg="#282828", hover_bg="#444444")
        def update_position():
            x = self.root.winfo_pointerx()
            y = self.root.winfo_pointery()
            pos_label.config(text=f"Mova o mouse e aperte ENTER\nPosição atual: ({x}, {y})")
            window.after(50, update_position)
        update_position()
        def on_enter(e):
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
        window.configure(bg="#282828")
        window.grid_rowconfigure(0, weight=1)
        window.grid_rowconfigure(1, weight=0)
        window.grid_columnconfigure(0, weight=1)
        text_frame = tk.Frame(window, bg="#282828")
        text_frame.grid(row=0, column=0, sticky="nsew")
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set,
                              bg="white", fg="black", insertbackground="black", relief=tk.FLAT, bd=0)
        text_widget.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        scrollbar.config(command=text_widget.yview)
        text_widget.insert("1.0", full_text)
        btn_frame = tk.Frame(window, bg="#282828")
        btn_frame.grid(row=1, column=0, sticky="ew")
        ok_button = tk.Button(btn_frame, text="OK", command=lambda: self._save_text_edit(text_widget, window),
                              bg="#535353", fg="white", font=("Segoe UI", 12),
                              width=10, height=1, relief=tk.FLAT, bd=0)
        ok_button.pack(pady=5)

    def _save_text_edit(self, text_widget, window):
        full_text = text_widget.get("1.0", tk.END).rstrip("\n")
        single_line = " ".join(full_text.splitlines())
        summary = single_line if len(single_line) <= 40 else single_line[:40] + "..."
        self.add_event("Digitar: " + summary)
        self.events[-1]["label"].full_text = full_text
        window.destroy()

    def edit_key_event(self, event_label):
        current_text = event_label.cget("text")
        prefix = "Pressionar Tecla:"
        existing = current_text[len(prefix):].strip() if current_text.startswith(prefix) else ""
        window = tk.Toplevel(self.root)
        window.title("Editar Tecla")
        self.center_window(window, 400, 200)
        window.attributes("-topmost", True)
        window.configure(bg="#282828")
        instr_label = tk.Label(window, text="Pressione a(s) tecla(s) desejada(s) e aperte ENTER para confirmar", padx=20, pady=10, bg="#282828", fg="white")
        instr_label.pack(expand=True, fill=tk.BOTH)
        combo_label = tk.Label(window, text="Combinação: " + existing, padx=20, pady=5, bg="#282828", fg="white")
        combo_label.pack()
        key_combination = [] if not existing else existing.split("+")
        def on_key(e):
            if e.keysym == "Return":
                return
            if e.keysym not in key_combination:
                key_combination.append(e.keysym)
            combo_label.config(text="Combinação: " + "+".join(key_combination))
        window.bind("<Key>", on_key)
        clear_button = tk.Button(window, text="Limpar", command=lambda: (key_combination.clear(), combo_label.config(text="Combinação: ")),
                                 bg="#535353", fg="white", relief=tk.FLAT, bd=0, width=10, height=1)
        clear_button.pack(pady=5)
        def save_keys(e=None):
            if key_combination:
                event_label.config(text=f"Pressionar Tecla: {'+'.join(key_combination)}")
            else:
                event_label.config(text=f"Pressionar Tecla: {existing}")
            window.destroy()
        window.bind("<Return>", save_keys)
        ok_button = tk.Button(window, text="OK", command=save_keys,
                              bg="#535353", fg="white", font=("Segoe UI", 12),
                              width=10, height=1, relief=tk.FLAT, bd=0)
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
        window.configure(bg="#282828")
        label = tk.Label(window, text="Digite o tempo (somente números) e aperte ENTER ou clique em OK", padx=20, pady=10, bg="#282828", fg="white")
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
        ok_button = tk.Button(window, text="OK", command=save_edit, bg="#535353", fg="white", font=("Segoe UI", 12),
                              width=10, height=1, relief=tk.FLAT, bd=0)
        ok_button.pack(pady=5)

    def add_clear_event(self):
        self.add_event("Apagar Campo")

    # -------------------- Métodos de Importação, Exportação e Execução --------------------
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
                        self.events[-1]["label"].full_text = full_text
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
                    for item in self.events:
                        text = item["label"].cget("text")
                        if text.startswith("Digitar:") and hasattr(item["label"], "full_text"):
                            file.write("Digitar: <<START>>\n" + item["label"].full_text + "\n<<END>>\n")
                        else:
                            file.write(text + "\n")
                messagebox.showinfo("Exportar", f"Timeline exportada para o arquivo {os.path.basename(file_path)}.")
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível exportar a timeline: {e}")

    # -------------------- Execução --------------------
    def execute_with_loops(self):
        loop_count = simpledialog.askinteger("Loop", "Digite a quantidade de loops (1 = normal):", initialvalue=1)
        if loop_count is None or loop_count == 1:
            self.execute_timeline()
        else:
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
        
    def execute_timeline(self):
        if self.executing:
            messagebox.showwarning("Atenção", "Macro já está em execução!")
            return
        self.message_shown = False
        required_files = set()
        for item in self.events:
            text = item["label"].cget("text")
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
        tem_lista = any(item["label"].cget("text").startswith("Lista:") for item in self.events)
        if tem_lista:
            while (not self.stop_requested) and any(self.loaded_index[fname] < len(self.loaded_lists[fname]) for fname in required_files):
                for item in list(self.events):
                    if self.stop_requested:
                        break
                    text = item["label"].cget("text")
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
                        if hasattr(item["label"], "full_text"):
                            full_text = item["label"].full_text
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
                            item_text = self.loaded_lists[file_path][self.loaded_index[file_path]]
                            pyautogui.write(item_text)
                            self.loaded_index[file_path] += 1
                            time.sleep(0.2)
        else:
            for item in list(self.events):
                if self.stop_requested:
                    break
                text = item["label"].cget("text")
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
                    if hasattr(item["label"], "full_text"):
                        full_text = item["label"].full_text
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

# MÉTODOS DE CAPTURA E ADIÇÃO (mantidos inalterados)
    def capture_mouse_click(self):
        cap_win = tk.Toplevel(self.root)
        cap_win.title("Capturar Clique")
        self.center_window(cap_win, 400, 250)
        cap_win.attributes("-topmost", True)
        cap_win.configure(bg="#282828")
        
        label = tk.Label(cap_win, text="Mova o mouse até a posição desejada e aperte ENTER", 
                        padx=20, pady=10, bg="#282828", fg="white")
        label.pack(fill=tk.X)
        
        # Opções para o clique
        option_frame = tk.Frame(cap_win, bg="#282828")
        option_frame.pack(fill=tk.X, padx=20, pady=5)
        click_option = tk.StringVar(value="Simples")
        tk.Radiobutton(option_frame, text="Simples", variable=click_option, value="Simples",
                    bg="#282828", fg="white", selectcolor="#444444").pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(option_frame, text="Pressionar", variable=click_option, value="Pressionar",
                    bg="#282828", fg="white", selectcolor="#444444").pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(option_frame, text="Repetido", variable=click_option, value="Repetido",
                    bg="#282828", fg="white", selectcolor="#444444").pack(side=tk.LEFT, padx=5)
        
        # Parâmetro opcional (duração ou período)
        param_frame = tk.Frame(cap_win, bg="#282828")
        param_label = tk.Label(param_frame, text="", bg="#282828", fg="white")
        param_label.pack(side=tk.LEFT)
        param_entry = tk.Entry(param_frame)
        param_entry.pack(side=tk.LEFT, padx=5)
        # Inicialmente, escondemos
        param_frame.pack_forget()

        def update_param_visibility(*args):
            opt = click_option.get()
            if opt == "Simples":
                param_frame.pack_forget()
            elif opt == "Pressionar":
                param_label.config(text="Duração (s):")
                param_frame.pack(fill=tk.X, padx=20, pady=5)
            elif opt == "Repetido":
                param_label.config(text="Repetir por (s):")
                param_frame.pack(fill=tk.X, padx=20, pady=5)
        click_option.trace("w", update_param_visibility)
        
        def update_position():
            x = self.root.winfo_pointerx()
            y = self.root.winfo_pointery()
            label.config(text=f"Mova o mouse até a posição desejada e aperte ENTER\nPosição atual: ({x}, {y})")
            cap_win.after(50, update_position)
        update_position()
        
        def on_enter(event):
            x = self.root.winfo_pointerx()
            y = self.root.winfo_pointery()
            opt = click_option.get()
            param = param_entry.get().strip() or "1.0"
            cap_win.destroy()
            if opt == "Simples":
                self.add_event(f"Clique Simples em ({x}, {y})")
            elif opt == "Pressionar":
                self.add_event(f"Pressionar por tempo em ({x}, {y}) - Duração: {param}s")
            elif opt == "Repetido":
                self.add_event(f"Clique repetido em ({x}, {y}) - Repetir por: {param}s")
        cap_win.bind("<Return>", on_enter)
        cap_win.focus_set()

    def add_text_event(self):
        text_win = tk.Toplevel(self.root)
        text_win.title("Adicionar Texto")
        self.center_window(text_win, 600, 400)
        text_win.attributes("-topmost", True)
        text_win.configure(bg="#282828")
        text_win.grid_rowconfigure(0, weight=1)
        text_win.grid_rowconfigure(1, weight=0)
        text_win.grid_columnconfigure(0, weight=1)
        text_frame = tk.Frame(text_win, bg="#282828")
        text_frame.grid(row=0, column=0, sticky="nsew")
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set,
                              bg="white", fg="black", insertbackground="black", relief=tk.FLAT, bd=0)
        text_widget.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        scrollbar.config(command=text_widget.yview)
        btn_frame = tk.Frame(text_win, bg="#282828")
        btn_frame.grid(row=1, column=0, sticky="ew")
        def save_text():
            full_text = text_widget.get("1.0", tk.END).rstrip("\n")
            single_line = " ".join(full_text.splitlines())
            summary = single_line if len(single_line) <= 40 else single_line[:40] + "..."
            if full_text.strip():
                self.add_event(f"Digitar: {summary}")
                self.events[-1]["label"].full_text = full_text
            text_win.destroy()
        ok_button = tk.Button(btn_frame, text="OK", command=save_text,
                              bg="#535353", fg="white", font=("Segoe UI", 12),
                              width=10, height=1, relief=tk.FLAT, bd=0)
        ok_button.pack(pady=5)
    def add_key_event(self):
        key_win = tk.Toplevel(self.root)
        key_win.title("Adicionar Tecla")
        self.center_window(key_win, 400, 250)
        key_win.attributes("-topmost", True)
        key_win.configure(bg="#282828")
        
        instr_label = tk.Label(key_win, text="Pressione a(s) tecla(s) desejada(s) e aperte ENTER para confirmar",
                                padx=20, pady=10, bg="#282828", fg="white")
        instr_label.pack(fill=tk.X)
        
        # Opções para o evento de tecla
        option_frame = tk.Frame(key_win, bg="#282828")
        option_frame.pack(fill=tk.X, padx=20, pady=5)
        key_option = tk.StringVar(value="Simples")
        tk.Radiobutton(option_frame, text="Simples", variable=key_option, value="Simples",
                    bg="#282828", fg="white", selectcolor="#444444").pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(option_frame, text="Manter", variable=key_option, value="Manter",
                    bg="#282828", fg="white", selectcolor="#444444").pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(option_frame, text="Repetida", variable=key_option, value="Repetida",
                    bg="#282828", fg="white", selectcolor="#444444").pack(side=tk.LEFT, padx=5)
        
        # Parâmetro opcional
        param_frame = tk.Frame(key_win, bg="#282828")
        param_label = tk.Label(param_frame, text="", bg="#282828", fg="white")
        param_label.pack(side=tk.LEFT)
        param_entry = tk.Entry(param_frame)
        param_entry.pack(side=tk.LEFT, padx=5)
        param_frame.pack_forget()
        
        def update_key_param(*args):
            opt = key_option.get()
            if opt == "Simples":
                param_frame.pack_forget()
            elif opt == "Manter":
                param_label.config(text="Duração (s):")
                param_frame.pack(fill=tk.X, padx=20, pady=5)
            elif opt == "Repetida":
                param_label.config(text="Repetir por (s):")
                param_frame.pack(fill=tk.X, padx=20, pady=5)
        key_option.trace("w", update_key_param)
        
        combo_label = tk.Label(key_win, text="Combinação: ", padx=20, pady=5, bg="#282828", fg="white")
        combo_label.pack()
        key_combination = []
        def on_key(e):
            if e.keysym == "Return":
                return
            if e.keysym not in key_combination:
                key_combination.append(e.keysym)
            combo_label.config(text="Combinação: " + "+".join(key_combination))
        key_win.bind("<Key>", on_key)
        
        clear_button = tk.Button(key_win, text="Limpar", 
                                command=lambda: (key_combination.clear(), combo_label.config(text="Combinação: ")),
                                bg="#535353", fg="white", relief=tk.FLAT, bd=0, width=10, height=1)
        clear_button.pack(pady=5)
        
        def save_keys(e=None):
            opt = key_option.get()
            param = param_entry.get().strip() or "1.0"
            if key_combination:
                if opt == "Simples":
                    self.add_event(f"Pressionar Tecla: {'+'.join(key_combination)}")
                elif opt == "Manter":
                    self.add_event(f"Manter pressionada: {'+'.join(key_combination)} - Duração: {param}s")
                elif opt == "Repetida":
                    self.add_event(f"Tecla repetida: {'+'.join(key_combination)} - Repetir por: {param}s")
            key_win.destroy()
        key_win.bind("<Return>", save_keys)
        
        ok_button = tk.Button(key_win, text="OK", command=save_keys,
                            bg="#535353", fg="white", font=("Segoe UI", 12),
                            width=10, height=1, relief=tk.FLAT, bd=0)
        ok_button.pack(pady=5)


    def add_wait_event(self):
        wait_win = tk.Toplevel(self.root)
        wait_win.title("Adicionar Espera")
        self.center_window(wait_win, 400, 150)
        wait_win.attributes("-topmost", True)
        wait_win.configure(bg="#282828")
        lbl = tk.Label(wait_win, text="Digite o tempo em segundos (decimais permitidos) e aperte ENTER ou OK",
                       padx=20, pady=10, bg="#282828", fg="white")
        lbl.pack(expand=True, fill=tk.BOTH)
        time_entry = tk.Entry(wait_win, width=20, bg="white", fg="black", relief=tk.FLAT, bd=0)
        time_entry.pack(pady=5)
        time_entry.focus_set()
        def is_valid_decimal(P):
            return bool(re.match(r'^[0-9]*\.?[0-9]*$', P))
        vcmd = (wait_win.register(is_valid_decimal), '%P')
        time_entry.config(validate='key', validatecommand=vcmd)
        def process_time(e=None):
            tempo = time_entry.get()
            if tempo.strip():
                self.add_event(f"Esperar {tempo} segundos")
            wait_win.destroy()
        time_entry.bind("<Return>", process_time)
        ok_button = tk.Button(wait_win, text="OK", command=process_time,
                              bg="#535353", fg="white", font=("Segoe UI", 12),
                              width=10, height=1, relief=tk.FLAT, bd=0)
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
                        self.events[-1]["label"].full_text = full_text
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
                    for item in self.events:
                        text = item["label"].cget("text")
                        if text.startswith("Digitar:") and hasattr(item["label"], "full_text"):
                            file.write("Digitar: <<START>>\n" + item["label"].full_text + "\n<<END>>\n")
                        else:
                            file.write(text + "\n")
                messagebox.showinfo("Exportar", f"Timeline exportada para o arquivo {os.path.basename(file_path)}.")
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível exportar a timeline: {e}")

    def execute_with_loops(self):
        loop_count = simpledialog.askinteger("Loop", "Digite a quantidade de loops (1 = normal):", initialvalue=1)
        if loop_count is None or loop_count == 1:
            self.execute_timeline()
        else:
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
        
    def execute_timeline(self):
        if self.executing:
            messagebox.showwarning("Atenção", "Macro já está em execução!")
            return
        self.message_shown = False
        required_files = set()
        for item in self.events:
            text = item["label"].cget("text")
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
        tem_lista = any(item["label"].cget("text").startswith("Lista:") for item in self.events)
        if tem_lista:
            while (not self.stop_requested) and any(self.loaded_index[fname] < len(self.loaded_lists[fname]) for fname in required_files):
                for item in list(self.events):
                    if self.stop_requested:
                        break
                    text = item["label"].cget("text")
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
                        if hasattr(item["label"], "full_text"):
                            full_text = item["label"].full_text
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
                            item_text = self.loaded_lists[file_path][self.loaded_index[file_path]]
                            pyautogui.write(item_text)
                            self.loaded_index[file_path] += 1
                            time.sleep(0.2)
        else:
            for item in list(self.events):
                if self.stop_requested:
                    break
                text = item["label"].cget("text")
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
                    if hasattr(item["label"], "full_text"):
                        full_text = item["label"].full_text
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

if __name__ == "__main__":
    root = tk.Tk()
    app = MacroApp(root)
    root.bind("<Delete>", lambda event: app.delete_selected_events(event))
    root.mainloop()
