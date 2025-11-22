import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import threading
import time
import re
import os
import sys
import pyautogui

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
        # -----------------------------------
        
        try:
            self.root.iconbitmap(resource_path("icone.ico"))
        except:
            pass 
        self.root.title(self.APP_NAME)
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
        self.list_settings = {}
        
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
        # 1. Calcula a posição central
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        # 2. Aplica geometria e cor
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.configure(bg="#282828")
        
        # --- SOLUÇÃO 1: Ícone em TODAS as janelas ---
        try:
            win.iconbitmap(resource_path("icone.ico"))
        except Exception:
            pass # Se não achar o ícone, segue sem travar
            
        # --- SOLUÇÃO 2: Janela Modal (Bloqueia o resto) ---
        # Isso impede clicar na janela principal enquanto essa estiver aberta
        if win != self.root: # Não aplica na janela principal, só nas filhas
            win.transient(self.root) # Diz ao sistema que essa janela pertence à principal
            win.grab_set()           # "Agarra" o foco: nada mais pode ser clicado
            win.focus_force()        # Traz para frente

    def show_about(self):
        about_win = tk.Toplevel(self.root)
        about_win.resizable(False, False)
        about_win.title(f"Sobre - {self.APP_NAME}")
        about_win.configure(bg="#282828")
        self.center_window(about_win, 400, 250)
        about_win.attributes("-topmost", True)
        
        # Tenta por o ícone grande
        try:
            tk.Label(about_win, text="🖱️", font=("Segoe UI Emoji", 40), bg="#282828", fg="white").pack(pady=(10, 0))
        except: pass

        tk.Label(about_win, text=self.APP_NAME, font=("Segoe UI", 14, "bold"), bg="#282828", fg="white").pack()
        tk.Label(about_win, text=f"Versão: {self.APP_VERSION}", font=("Segoe UI", 10), bg="#282828", fg="#A0A0A0").pack()
        tk.Label(about_win, text=f"Created by: {self.APP_AUTHOR}", font=("Segoe UI", 9), bg="#282828", fg="#808080").pack(pady=5)
        
        # Frame para a descrição com borda sutil
        desc_frame = tk.Frame(about_win, bg="#333333", padx=10, pady=10)
        desc_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        tk.Label(desc_frame, text=self.APP_DESC, font=("Segoe UI", 9), justify="left", bg="#333333", fg="#E0E0E0").pack()
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
                if text.startswith("Clique") or text.startswith("Duplo") or text.startswith("Botão"):
                    self.edit_click_event(lbl)
                elif text.startswith("Digitar:"):
                    self.edit_text_event(lbl)
                elif text.startswith("Pressionar") or text.startswith("Manter") or text.startswith("Tecla"):
                    self.edit_key_event(lbl)
                elif text.startswith("Esperar"):
                    self.edit_wait_event(lbl)
                elif text.startswith("Lista:"): # <--- ADICIONADO AQUI
                    self.edit_list_event(lbl)
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
        current_text = event_label.cget("text")
        
        # Parser (tenta descobrir o modo atual)
        mode_found = "Simples"
        param_val = ""
        
        if "Pressionar por tempo" in current_text:
            mode_found = "Pressionar"
            if " - Duração: " in current_text:
                param_val = current_text.split(" - Duração: ")[1].replace("s", "")
        elif "Clique repetido" in current_text:
            mode_found = "Repetido"
            if " - Repetir por: " in current_text:
                param_val = current_text.split(" - Repetir por: ")[1].replace("s", "")
        elif "Duplo Clique" in current_text:
            mode_found = "Duplo Clique"
        elif "Botão Direito" in current_text:
            mode_found = "Botão Direito"
        
        def on_update(x, y, mode, param):
            new_text = ""
            if mode == "Simples":
                new_text = f"Clique Simples em ({x}, {y})"
            elif mode == "Duplo Clique":
                new_text = f"Duplo Clique em ({x}, {y})"
            elif mode == "Botão Direito":
                new_text = f"Botão Direito em ({x}, {y})"
            elif mode == "Pressionar":
                new_text = f"Pressionar por tempo em ({x}, {y}) - Duração: {param}s"
            elif mode == "Repetido":
                new_text = f"Clique repetido em ({x}, {y}) - Repetir por: {param}s"
            
            event_label.config(text=new_text)

        self._open_mouse_dialog("Editar Clique", initial_mode=mode_found, initial_param=param_val, on_confirm=on_update)

    def edit_text_event(self, event_label):
        # Recupera o texto completo (se existir atributo oculto ou se for curto)
        if hasattr(event_label, "full_text"):
            full_text = event_label.full_text
        else:
            prefix = "Digitar:"
            full_text = event_label.cget("text")[len(prefix):].strip() if event_label.cget("text").startswith(prefix) else ""
            
        def on_update(new_text):
            single_line = " ".join(new_text.splitlines())
            summary = single_line if len(single_line) <= 40 else single_line[:40] + "..."
            event_label.config(text=f"Digitar: {summary}")
            event_label.full_text = new_text

        self._open_text_dialog("Editar Texto", initial_text=full_text, on_confirm=on_update)

    def _save_text_edit(self, text_widget, window):
        full_text = text_widget.get("1.0", tk.END).rstrip("\n")
        single_line = " ".join(full_text.splitlines())
        summary = single_line if len(single_line) <= 40 else single_line[:40] + "..."
        self.add_event("Digitar: " + summary)
        self.events[-1]["label"].full_text = full_text
        window.destroy()

    def edit_wait_event(self, event_label):
        current_text = event_label.cget("text")
        m = re.search(r"Esperar (\d+\.?\d*) segundos", current_text) # Regex melhorado para decimais
        existing = m.group(1) if m else ""
        
        def on_update(new_val):
            event_label.config(text=f"Esperar {new_val} segundos")
            
        self._open_wait_dialog("Editar Espera", initial_value=existing, on_confirm=on_update)

    def add_clear_event(self):
        self.add_event("Apagar Campo")
    
    # -------------------------------------------------------------------------
    # FUNÇÕES ADD (Carregar) / EDIT (Editar)
    # -------------------------------------------------------------------------
    def load_timeline(self):
        # Função interna chamada ao clicar em Salvar
        def on_save(file_path, should_ignore):
            try:
                with open(file_path, "r") as file:
                    lines = file.read().splitlines()
                
                if should_ignore:
                    items = [line.strip() for line in lines if line.strip()]
                else:
                    items = [line.strip() for line in lines]
                
                if items is not None:
                    full_path = os.path.abspath(file_path)
                    self.loaded_lists[full_path] = items
                    self.loaded_index[full_path] = 0
                    self.list_settings[full_path] = should_ignore
                    
                    # Evita duplicar evento visual se já existir
                    ja_tem = any(item["label"].cget("text") == f"Lista: {full_path}" for item in self.events)
                    if not ja_tem:
                        self.add_event(f"Lista: {full_path}")
                    
                    msg_extra = " (ignorando vazias)" if should_ignore else " (incluindo vazias)"
                    messagebox.showinfo("Sucesso", f"Arquivo carregado com {len(items)} itens{msg_extra}.")
                    return True # Indica sucesso para fechar a janela
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao ler arquivo: {e}")
                return False

        self._open_list_dialog("Carregar Lista", on_confirm=on_save)

    def edit_list_event(self, event_label):
        # Extrai o caminho atual do texto do label
        current_text = event_label.cget("text")
        current_path = current_text.split("Lista:")[1].strip()
        
        # Pega a configuração atual (ou False se não achar)
        current_setting = self.list_settings.get(current_path, False)
        
        def on_update(new_path, new_ignore_setting):
            try:
                with open(new_path, "r") as file:
                    lines = file.read().splitlines()
                
                if new_ignore_setting:
                    items = [line.strip() for line in lines if line.strip()]
                else:
                    items = [line.strip() for line in lines]
                
                full_path = os.path.abspath(new_path)
                
                # Se o caminho mudou, precisamos limpar o antigo do dicionário? 
                # O ideal é só garantir que o novo esteja lá.
                self.loaded_lists[full_path] = items
                self.loaded_index[full_path] = 0
                self.list_settings[full_path] = new_ignore_setting
                
                # Atualiza o texto do Label na timeline
                event_label.config(text=f"Lista: {full_path}")
                
                msg_extra = " (ignorando vazias)" if new_ignore_setting else " (incluindo vazias)"
                messagebox.showinfo("Atualizado", f"Lista atualizada. {len(items)} itens carregados{msg_extra}.")
                return True
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao ler arquivo: {e}")
                return False

        self._open_list_dialog("Editar Lista", initial_path=current_path, initial_ignore=current_setting, on_confirm=on_update)    
    
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
        # --- CRIAÇÃO DA JANELA DE LOOP CUSTOMIZADA ---
        loop_win = tk.Toplevel(self.root)
        loop_win.title("Execução em Loop")
        self.center_window(loop_win, 300, 180) # Usa sua função center_window (já resolve ícone e tema)
        loop_win.attributes("-topmost", True)
        
        # Variável para armazenar o resultado
        result = {"count": None}
        
        lbl = tk.Label(loop_win, text="Quantas vezes repetir a macro?", 
                       bg="#282828", fg="white", font=("Segoe UI", 11), pady=10)
        lbl.pack()
        
        entry = tk.Entry(loop_win, width=10, justify="center", font=("Segoe UI", 12))
        entry.insert(0, "1")
        entry.pack(pady=5)
        entry.focus_set()
        entry.select_range(0, tk.END) # Seleciona o texto para facilitar digitação
        
        def on_confirm(event=None):
            val = entry.get()
            if val.isdigit() and int(val) > 0:
                result["count"] = int(val)
                loop_win.destroy()
            else:
                messagebox.showwarning("Inválido", "Digite um número maior que 0.", parent=loop_win)
        
        def on_cancel():
            loop_win.destroy() # Fecha sem salvar nada em result["count"]

        btn_frame = tk.Frame(loop_win, bg="#282828")
        btn_frame.pack(pady=15)
        
        btn_ok = tk.Button(btn_frame, text="Iniciar", command=on_confirm,
                           bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"), bd=0, padx=15, pady=5)
        btn_ok.pack(side=tk.LEFT, padx=10)
        
        btn_cancel = tk.Button(btn_frame, text="Cancelar", command=on_cancel,
                               bg="#f44336", fg="white", font=("Segoe UI", 10), bd=0, padx=10, pady=5)
        btn_cancel.pack(side=tk.LEFT, padx=10)
        
        loop_win.bind("<Return>", on_confirm)
        
        # Espera a janela fechar antes de continuar (Comportamento Modal Manual)
        self.root.wait_window(loop_win)
        
        # --- LÓGICA DE EXECUÇÃO (SÓ RODA SE TIVER RESULTADO) ---
        loop_count = result["count"]
        
        if loop_count is None:
            return # Se fechou ou cancelou, PARA TUDO.

        if loop_count == 1:
            self.execute_timeline()
        else:
            def loop_runner():
                self.stop_requested = False
                self.message_shown = False
                self.executing = True
                self.suppress_messages = True
                
                for i in range(loop_count):
                    # Reseta índices das listas
                    for file_path in self.loaded_lists:
                        self.loaded_index[file_path] = 0
                    
                    # Passa a informação do loop atual para a contagem regressiva
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
        countdown_window.configure(bg="white")
        countdown_window.attributes("-topmost", True)
        countdown_window.lift()
        
        win_width, win_height = 300, 150
        self.center_window(countdown_window, win_width, win_height)
        countdown_window.configure(bg="white")
        countdown_window.focus_force()
        
        frame = tk.Frame(countdown_window, bg="white")
        frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        
        top_text = f"Macro {current_loop}/{total_loops} em:" if current_loop else "Começando em:"
        tk.Label(frame, text=top_text, font=("Segoe UI", 14), bg="white", fg="#333333").pack()
        
        number_label = tk.Label(frame, text="3", font=("Segoe UI", 48, "bold"), bg="white", fg="#FF5722")
        number_label.pack()
        tk.Label(frame, text="Sacuda o mouse para cancelar", font=("Segoe UI", 10, "italic"), bg="white", fg="#999999").pack()
        
        shake_thread = threading.Thread(target=self._monitor_mouse_shake)
        shake_thread.daemon = True
        shake_thread.start()
        
        # --- POLLING ULTRA-RÁPIDO PARA FECHAR JANELA ---
        def check_abort():
            if self.stop_requested:
                if countdown_window.winfo_exists():
                    countdown_window.destroy()
                self.executing = False
                return
            if countdown_window.winfo_exists():
                countdown_window.after(10, check_abort) # Checa a cada 10ms
        check_abort()

        def update_count(count):
            if not countdown_window.winfo_exists(): return
            if self.stop_requested: return

            # Garante topo
            try:
                countdown_window.lift()
                countdown_window.attributes("-topmost", True)
            except: pass

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
        countdown_window.configure(bg="white")
        countdown_window.attributes("-topmost", True)
        
        win_width, win_height = 300, 150
        self.center_window(countdown_window, win_width, win_height)
        countdown_window.configure(bg="white")
        countdown_window.focus_force()
        
        frame = tk.Frame(countdown_window, bg="white")
        frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        
        top_text = f"Macro {current_loop}/{total_loops} em:" if current_loop else "Começando em:"
        tk.Label(frame, text=top_text, font=("Segoe UI", 14), bg="white", fg="#333333").pack()
        number_label = tk.Label(frame, text="3", font=("Segoe UI", 48, "bold"), bg="white", fg="#FF5722")
        number_label.pack()
        tk.Label(frame, text="Sacuda o mouse para cancelar", font=("Segoe UI", 10, "italic"), bg="white", fg="#999999").pack()
        
        shake_thread = threading.Thread(target=self._monitor_mouse_shake)
        shake_thread.daemon = True
        shake_thread.start()
        
        for count in range(3, 0, -1):
            if self.stop_requested: break
            
            try:
                countdown_window.lift()
                countdown_window.attributes("-topmost", True)
            except: pass
            
            number_label.config(text=str(count))
            countdown_window.update()
            
            # Espera 1 segundo divido em 20 fatias de 0.05s para resposta instantânea
            for _ in range(20):
                if self.stop_requested: break
                time.sleep(0.05)
            
            if self.stop_requested: break
            
        countdown_window.destroy()
        
        if not self.stop_requested:
            self._run_macro(required_files)
        else:
            self.executing = False
    
    # -------------------------------------------------------------------------
    #  MÉTODOS REFATORADOS PARA EXECUÇÃO EFICIENTE
    # -------------------------------------------------------------------------
    def _execute_event_action(self, item):
        """Executa a ação de um único item da timeline."""
        if self.stop_requested:
            return

        text = item["label"].cget("text")

        # --- Eventos de Mouse ---
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

        # --- Eventos de Digitação ---
        elif text.startswith("Digitar:"):
            if hasattr(item["label"], "full_text"):
                full_text = item["label"].full_text
            else:
                full_text = text[len("Digitar:"):].strip()
            pyautogui.write(full_text)
            time.sleep(0.2)

        # --- Eventos de Teclado ---
        elif text.startswith("Pressionar Tecla:"):
            key_str = text[len("Pressionar Tecla:"):].strip()
            if "+" in key_str:
                keys = [normalize_key(k) for k in key_str.split("+")]
                pyautogui.hotkey(*keys)
            else:
                pyautogui.press(normalize_key(key_str))
            time.sleep(0.2)

        # --- Eventos de Espera ---
        elif text.startswith("Esperar"):
            match = re.search(r"Esperar (\d+) segundos", text)
            if match:
                seconds = int(match.group(1))
                # Divide a espera em pequenos passos para permitir interrupção rápida
                for _ in range(seconds * 10):
                    if self.stop_requested:
                        break
                    time.sleep(0.1)

        # --- Evento de Apagar ---
        elif text.startswith("Apagar Campo"):
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('backspace')
            time.sleep(0.2)

        # --- Eventos de Lista (Preenchimento dinâmico) ---
        elif text.startswith("Lista:"):
            file_path = text.split("Lista:")[1].strip()
            # Verifica se o arquivo existe e se ainda há itens para usar
            if file_path in self.loaded_lists and self.loaded_index[file_path] < len(self.loaded_lists[file_path]):
                item_text = self.loaded_lists[file_path][self.loaded_index[file_path]]
                pyautogui.write(item_text)
                self.loaded_index[file_path] += 1
                time.sleep(0.2)

    def _run_macro(self, required_files):
        tem_lista = any(item["label"].cget("text").startswith("Lista:") for item in self.events)

        if tem_lista:
            # Modo LISTA: Executa o loop enquanto houver itens nas listas carregadas
            while (not self.stop_requested) and any(self.loaded_index[fname] < len(self.loaded_lists[fname]) for fname in required_files):
                for item in list(self.events):
                    if self.stop_requested:
                        break
                    self._execute_event_action(item)
        else:
            # Modo SIMPLES: Executa a timeline uma única vez (o loop externo controla as repetições)
            for item in list(self.events):
                if self.stop_requested:
                    break
                self._execute_event_action(item)
        
        # Finalização
        self.executing = False
        if not self.suppress_messages and not self.message_shown:
            if self.stop_requested:
                self._show_message("Interrompido", self.interrupt_reason)
            else:
                self._show_message("Finalizado", "A macro foi executada com sucesso.")
    
    def _monitor_mouse_shake(self):
        last_pos = pyautogui.position()
        shake_score = 0
        last_x_dir = 0 
        last_y_dir = 0
        
        # SENSIBILIDADE
        min_movement = 40  # Movimento mínimo para considerar (pixels)
        max_score = 4      # Quantos "movimentos bruscos" para cancelar
        decay_rate = 0.1   # Quanto o score abaixa por ciclo (para zerar se parar)
        
        # Proteção para o monitor não cair
        try:
            while self.executing and not self.stop_requested:
                time.sleep(0.05) # 20 checagens por segundo
                
                try:
                    current_pos = pyautogui.position()
                except:
                    # Se der erro de leitura (ex: fail-safe do pyautogui), continua tentando
                    continue
                
                dx = current_pos.x - last_pos.x
                dy = current_pos.y - last_pos.y
                
                moved_brusquely = False

                # --- ANÁLISE HORIZONTAL (X) ---
                if abs(dx) > min_movement:
                    current_x_dir = 1 if dx > 0 else -1
                    # Se inverteu direção (ex: Direita -> Esquerda)
                    if current_x_dir != last_x_dir and last_x_dir != 0:
                        shake_score += 1
                        moved_brusquely = True
                    last_x_dir = current_x_dir
                
                # --- ANÁLISE VERTICAL (Y) - AGORA INCLUÍDA ---
                if abs(dy) > min_movement:
                    current_y_dir = 1 if dy > 0 else -1
                    # Se inverteu direção (ex: Cima -> Baixo)
                    if current_y_dir != last_y_dir and last_y_dir != 0:
                        shake_score += 1
                        moved_brusquely = True
                    last_y_dir = current_y_dir

                # Decaimento (Se parar de mexer, o score baixa devagar)
                if not moved_brusquely and shake_score > 0:
                    shake_score = max(0, shake_score - decay_rate)

                last_pos = current_pos
                
                # --- GATILHO DE PARADA ---
                if shake_score >= max_score:
                    self.interrupt_reason = "Macro interrompida por sacudir o mouse."
                    self.stop_requested = True
                    # Tenta forçar parada visualmente
                    self._show_message("Interrompido", self.interrupt_reason)
                    break
        except Exception as e:
            print(f"Erro no monitor de mouse: {e}")
    
    def stop_execution(self):
        if not self.stop_requested:
            self.interrupt_reason = "Macro interrompida pelo usuário."
        self.stop_requested = True
        self._show_message("Interrompido", self.interrupt_reason)
    
    def _show_message(self, title, message):
        if not self.message_shown:
            self.message_shown = True
            self.root.after(0, lambda: messagebox.showinfo(title, message))

    # -------------------------------------------------------------------------
    # NOVAS FUNÇÕES ADD/EDIT (MOUSE)
    # -------------------------------------------------------------------------
    def capture_mouse_click(self):
        def on_save(x, y, mode, param):
            if mode == "Simples":
                self.add_event(f"Clique Simples em ({x}, {y})")
            elif mode == "Duplo Clique":
                self.add_event(f"Duplo Clique em ({x}, {y})")
            elif mode == "Botão Direito":
                self.add_event(f"Botão Direito em ({x}, {y})")
            elif mode == "Pressionar":
                self.add_event(f"Pressionar por tempo em ({x}, {y}) - Duração: {param}s")
            elif mode == "Repetido":
                self.add_event(f"Clique repetido em ({x}, {y}) - Repetir por: {param}s")
        
        self._open_mouse_dialog("Capturar Clique", on_confirm=on_save)

    def add_text_event(self):
        def on_save(full_text):
            if full_text.strip():
                single_line = " ".join(full_text.splitlines())
                summary = single_line if len(single_line) <= 40 else single_line[:40] + "..."
                self.add_event(f"Digitar: {summary}")
                self.events[-1]["label"].full_text = full_text
        self._open_text_dialog("Adicionar Texto", on_confirm=on_save)

    # -------------------------------------------------------------------------
    # MÉTODO AUXILIAR PARA LISTAS (Carregar/Editar)
    # -------------------------------------------------------------------------
    def _open_list_dialog(self, title, initial_path="", initial_ignore=False, on_confirm=None):
        win = tk.Toplevel(self.root)
        win.title(title)
        self.center_window(win, 450, 220)
        win.attributes("-topmost", True)
        win.configure(bg="#282828")
        
        # Variáveis
        selected_file = tk.StringVar(value=initial_path)
        ignore_blank = tk.BooleanVar(value=initial_ignore)

        # 1. Seção de Seleção de Arquivo
        file_frame = tk.Frame(win, bg="#282828")
        file_frame.pack(fill=tk.X, padx=20, pady=20)
        
        lbl_instruction = tk.Label(file_frame, text="Arquivo selecionado:", bg="#282828", fg="white", anchor="w")
        lbl_instruction.pack(fill=tk.X)

        path_display = tk.Entry(file_frame, textvariable=selected_file, bg="#404040", fg="white", 
                            relief=tk.FLAT)
        path_display.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        
        def browse_file():
            path = filedialog.askopenfilename(parent=win, filetypes=[("Text Files", "*.txt")])
            if path:
                selected_file.set(path)
        
        btn_browse = tk.Button(file_frame, text="📂", command=browse_file,
                               bg="#535353", fg="white", bd=0, relief=tk.FLAT, width=4)
        btn_browse.pack(side=tk.RIGHT, padx=(5, 0))

        # 2. Opção de Linhas em Branco
        check_frame = tk.Frame(win, bg="#282828")
        check_frame.pack(fill=tk.X, padx=20)
        
        cb = tk.Checkbutton(check_frame, text="Ignorar linhas em branco", variable=ignore_blank,
                            bg="#282828", fg="white", selectcolor="#444444", 
                            activebackground="#282828", activeforeground="white",
                            onvalue=True, offvalue=False)
        cb.pack(anchor="w")
        
        # 3. Botão Confirmar
        def confirm_action():
            file_path = selected_file.get()
            should_ignore = ignore_blank.get()
            
            if not file_path or not os.path.exists(file_path):
                messagebox.showwarning("Atenção", "Por favor, selecione um arquivo válido.", parent=win)
                return
            
            if on_confirm:
                success = on_confirm(file_path, should_ignore)
                if success:
                    win.destroy()

        btn_ok = tk.Button(win, text="Salvar", command=confirm_action,
                           bg="#535353", fg="white", font=("Segoe UI", 10, "bold"),
                           relief=tk.FLAT, bd=0, height=2)
        btn_ok.pack(fill=tk.X, side=tk.BOTTOM, padx=20, pady=20)

    # -------------------------------------------------------------------------
    # MÉTODO AUXILIAR PARA MOUSE (COM MONITORAMENTO DE POSIÇÃO)
    # -------------------------------------------------------------------------
    def _open_mouse_dialog(self, title, initial_mode="Simples", initial_param="", on_confirm=None):
        window = tk.Toplevel(self.root)
        window.title(title)
        self.center_window(window, 450, 280)
        window.attributes("-topmost", True)
        window.configure(bg="#282828")
        
        # Label de instrução que vai atualizar com as coordenadas
        info_label = tk.Label(window, text="Mova o mouse e aperte ENTER", 
                              padx=20, pady=10, bg="#282828", fg="white", font=("Segoe UI", 10))
        info_label.pack(fill=tk.X)
        
        # Opções
        option_frame = tk.Frame(window, bg="#282828")
        option_frame.pack(fill=tk.X, padx=20, pady=10)
        
        click_option = tk.StringVar(value=initial_mode)
        
        def create_radio(parent, text, val):
            rb = tk.Radiobutton(parent, text=text, variable=click_option, value=val,
                           bg="#282828", fg="white", selectcolor="#444444", 
                           activebackground="#282828", activeforeground="white")
            rb.pack(side=tk.LEFT, padx=10)
            return rb

        create_radio(option_frame, "Simples", "Simples")
        create_radio(option_frame, "Pressionar", "Pressionar")
        create_radio(option_frame, "Repetido", "Repetido")
        # Adicionei estas opções que existiam na lógica de execução mas não na de criação visual
        create_radio(option_frame, "Duplo", "Duplo Clique")
        create_radio(option_frame, "Direito", "Botão Direito")

        # Parâmetros
        param_frame = tk.Frame(window, bg="#282828")
        param_label = tk.Label(param_frame, text="", bg="#282828", fg="white")
        param_label.pack(side=tk.LEFT)
        param_entry = tk.Entry(param_frame, width=10)
        param_entry.pack(side=tk.LEFT, padx=5)
        param_entry.insert(0, initial_param)
        param_frame.pack_forget()

        def update_param_visibility(*args):
            opt = click_option.get()
            if opt in ["Simples", "Duplo Clique", "Botão Direito"]:
                param_frame.pack_forget()
            elif opt == "Pressionar":
                param_label.config(text="Duração (s):")
                param_frame.pack(pady=5)
            elif opt == "Repetido":
                param_label.config(text="Repetir por (s):")
                param_frame.pack(pady=5)
        
        click_option.trace("w", update_param_visibility)
        update_param_visibility()

        # Loop de atualização da posição
        def update_position():
            # Verifica se a janela ainda existe antes de tentar atualizar
            if not window.winfo_exists():
                return
            x = self.root.winfo_pointerx()
            y = self.root.winfo_pointery()
            info_label.config(text=f"Posicione o mouse e aperte ENTER para confirmar.\nCoordenadas atuais: ({x}, {y})")
            window.after(50, update_position)
        
        update_position()
        
        def confirm_action(event=None):
            x = self.root.winfo_pointerx()
            y = self.root.winfo_pointery()
            opt = click_option.get()
            param = param_entry.get().strip() or "1.0"
            
            if on_confirm:
                on_confirm(x, y, opt, param)
            window.destroy()

        window.bind("<Return>", confirm_action)
        # Opcional: Botão na tela também
        ok_btn = tk.Button(window, text="Gravar Posição Atual (ENTER)", command=confirm_action,
                           bg="#535353", fg="white", bd=0, relief=tk.FLAT, height=2)
        ok_btn.pack(fill=tk.X, side=tk.BOTTOM, padx=20, pady=10)
        window.focus_set()

    # -------------------------------------------------------------------------
    # MÉTODO AUXILIAR PARA TEXTO
    # -------------------------------------------------------------------------
    def _open_text_dialog(self, title, initial_text="", on_confirm=None):
        window = tk.Toplevel(self.root)
        window.title(title)
        self.center_window(window, 600, 400)
        window.attributes("-topmost", True)
        window.configure(bg="#282828")
        
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
            if on_confirm:
                on_confirm(full_text)
            window.destroy()

        ok_button = tk.Button(btn_frame, text="OK", command=save_action,
                              bg="#535353", fg="white", font=("Segoe UI", 12),
                              width=15, height=1, relief=tk.FLAT, bd=0)
        ok_button.pack()

    # -------------------------------------------------------------------------
    # MÉTODO AUXILIAR PARA ESPERA
    # -------------------------------------------------------------------------
    def _open_wait_dialog(self, title, initial_value="", on_confirm=None):
        window = tk.Toplevel(self.root)
        window.title(title)
        self.center_window(window, 400, 180)
        window.attributes("-topmost", True)
        window.configure(bg="#282828")
        
        lbl = tk.Label(window, text="Digite o tempo em segundos (decimais permitidos):",
                       padx=20, pady=15, bg="#282828", fg="white", font=("Segoe UI", 10))
        lbl.pack(fill=tk.X)
        
        entry = tk.Entry(window, width=20, bg="white", fg="black", relief=tk.FLAT, bd=0, font=("Segoe UI", 12), justify="center")
        entry.pack(pady=5)
        entry.insert(0, initial_value)
        entry.focus_set()
        
        # Validação para aceitar apenas números e ponto
        def is_valid_decimal(P):
            return bool(re.match(r'^[0-9]*\.?[0-9]*$', P))
        vcmd = (window.register(is_valid_decimal), '%P')
        entry.config(validate='key', validatecommand=vcmd)
        
        def save_action(e=None):
            val = entry.get()
            if val.strip():
                if on_confirm:
                    on_confirm(val)
                window.destroy()
        
        entry.bind("<Return>", save_action)
        
        ok_button = tk.Button(window, text="OK", command=save_action,
                              bg="#535353", fg="white", font=("Segoe UI", 12),
                              width=15, height=1, relief=tk.FLAT, bd=0)
        ok_button.pack(pady=15)

# -------------------------------------------------------------------------
    # MÉTODO AUXILIAR (Gerador de Janela de Teclas)
    # Coloque este método antes do add_key_event
    # -------------------------------------------------------------------------
    def _open_key_dialog(self, title, initial_mode="Simples", initial_keys=None, initial_duration="", on_confirm=None):
        """Cria a janela de diálogo para teclas, usada tanto para criar quanto para editar."""
        window = tk.Toplevel(self.root)
        window.title(title)
        self.center_window(window, 450, 300)
        window.attributes("-topmost", True)
        window.configure(bg="#282828")
        
        key_combination = list(initial_keys) if initial_keys else []

        # Instrução
        instr_label = tk.Label(window, text="Selecione o tipo e clique no campo abaixo para gravar as teclas.",
                               padx=20, pady=10, bg="#282828", fg="white", wraplength=400)
        instr_label.pack(fill=tk.X)
        
        # Radio Buttons
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
        
        # Campo de Captura
        capture_frame = tk.Frame(window, bg="#282828")
        capture_frame.pack(pady=5)
        
        tk.Label(capture_frame, text="Combinação:", bg="#282828", fg="white", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=5)
        
        entry_display = tk.Entry(capture_frame, width=30, font=("Segoe UI", 10), justify="center",
                                 bg="#404040", fg="white", insertbackground="white", relief=tk.FLAT)
        entry_display.pack(side=tk.LEFT, padx=5)
        entry_display.insert(0, " + ".join(key_combination))
        
        btn_clear_keys = tk.Button(capture_frame, text="🧹", 
                                   command=lambda: (key_combination.clear(), entry_display.delete(0, tk.END)),
                                   bg="#535353", fg="white", relief=tk.FLAT, bd=0, width=3)
        btn_clear_keys.pack(side=tk.LEFT, padx=2)
        CreateToolTip(btn_clear_keys, "Limpar teclas gravadas")

        # Parâmetros extras (tempo)
        param_frame = tk.Frame(window, bg="#282828")
        param_label = tk.Label(param_frame, text="", bg="#282828", fg="white")
        param_label.pack(side=tk.LEFT)
        param_entry = tk.Entry(param_frame, width=10)
        param_entry.pack(side=tk.LEFT, padx=5)
        param_entry.insert(0, initial_duration)
        param_frame.pack_forget()
        
        def update_key_param(*args):
            opt = key_option.get()
            if opt == "Simples":
                param_frame.pack_forget()
            elif opt == "Manter":
                param_label.config(text="Duração (s):")
                param_frame.pack(pady=5)
            elif opt == "Repetida":
                param_label.config(text="Repetir por (s):")
                param_frame.pack(pady=5)
        
        key_option.trace("w", update_key_param)
        update_key_param() # Chama uma vez para ajustar estado inicial
        
        def on_key_press(event):
            keysym = event.keysym
            if keysym not in key_combination:
                key_combination.append(keysym)
            display_text = " + ".join(key_combination)
            entry_display.delete(0, tk.END)
            entry_display.insert(0, display_text)
            return "break"

        entry_display.bind("<KeyPress>", on_key_press)
        
        def save_action():
            opt = key_option.get()
            param = param_entry.get().strip() or "1.0"
            
            if key_combination:
                if on_confirm:
                    # Chama a função de callback passando os dados capturados
                    on_confirm(opt, key_combination, param)
                window.destroy()
            else:
                messagebox.showwarning("Atenção", "Nenhuma tecla foi gravada!", parent=window)
        
        ok_button = tk.Button(window, text="OK", command=save_action,
                            bg="#535353", fg="white", font=("Segoe UI", 12, "bold"),
                            width=15, height=1, relief=tk.FLAT, bd=0)
        ok_button.pack(side=tk.BOTTOM, pady=15)
        
        entry_display.focus_set()

    # -------------------------------------------------------------------------
    # NOVAS VERSÕES SIMPLIFICADAS
    # -------------------------------------------------------------------------

    def add_key_event(self):
        # Função interna que sabe o que fazer quando o usuário clicar em OK
        def on_save(mode, keys, duration):
            combo_str = "+".join(keys)
            if mode == "Simples":
                self.add_event(f"Pressionar Tecla: {combo_str}")
            elif mode == "Manter":
                self.add_event(f"Manter pressionada: {combo_str} - Duração: {duration}s")
            elif mode == "Repetida":
                self.add_event(f"Tecla repetida: {combo_str} - Repetir por: {duration}s")

        # Chama o auxiliar
        self._open_key_dialog("Adicionar Tecla", on_confirm=on_save)

    def edit_key_event(self, event_label):
        current_text = event_label.cget("text")
        
        # Lógica de Parsing (leitura)
        mode_found = "Simples"
        keys_str = ""
        duration_val = "" # Começa vazio para o placeholder se necessário
        
        if " - Duração: " in current_text:
            mode_found = "Manter"
            parts = current_text.split(" - Duração: ")
            keys_str = parts[0].replace("Manter pressionada: ", "")
            duration_val = parts[1].replace("s", "").strip()
        elif " - Repetir por: " in current_text:
            mode_found = "Repetida"
            parts = current_text.split(" - Repetir por: ")
            keys_str = parts[0].replace("Tecla repetida: ", "")
            duration_val = parts[1].replace("s", "").strip()
        elif current_text.startswith("Pressionar Tecla:"):
            mode_found = "Simples"
            keys_str = current_text.replace("Pressionar Tecla: ", "")
        else:
            keys_str = current_text
        
        initial_keys = keys_str.split("+") if keys_str else []

        # Função interna de salvamento (Edição)
        def on_update(mode, keys, duration):
            combo_str = "+".join(keys)
            new_text = ""
            if mode == "Simples":
                new_text = f"Pressionar Tecla: {combo_str}"
            elif mode == "Manter":
                new_text = f"Manter pressionada: {combo_str} - Duração: {duration}s"
            elif mode == "Repetida":
                new_text = f"Tecla repetida: {combo_str} - Repetir por: {duration}s"
            event_label.config(text=new_text)

        # Chama o auxiliar passando os dados antigos
        self._open_key_dialog("Editar Tecla", 
                              initial_mode=mode_found, 
                              initial_keys=initial_keys, 
                              initial_duration=duration_val, 
                              on_confirm=on_update)

    def add_wait_event(self):
        def on_save(time_val):
            self.add_event(f"Esperar {time_val} segundos")
        self._open_wait_dialog("Adicionar Espera", on_confirm=on_save)

    def add_clear_event(self):
        self.add_event("Apagar Campo")

if __name__ == "__main__":
    root = tk.Tk()
    
    # 1. Esconde a janela principal imediatamente
    root.withdraw()
    
    # 2. Inicializa a aplicação (Carrega a classe para termos acesso às variáveis de versão/nome)
    app = MacroApp(root)
    root.bind("<Delete>", lambda event: app.delete_selected_events(event))
    
    # 3. Cria a tela de Splash
    splash = tk.Toplevel(root)
    splash.overrideredirect(True) # Remove bordas
    splash.configure(bg="#282828")
    
    # Tamanho do Splash
    w, h = 350, 220
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    splash.geometry(f"{w}x{h}+{x}+{y}")
    
    # --- Conteúdo do Splash (Usando dados do app) ---
    try:
        # Logo Central (Emoji)
        tk.Label(splash, text="🖱️", font=("Segoe UI Emoji", 60), bg="#282828", fg="white").pack(pady=(15, 0))
    except:
        pass
        
    # Nome do App (Puxando da classe)
    tk.Label(splash, text=app.APP_NAME, font=("Segoe UI", 18, "bold"), bg="#282828", fg="white").pack()
    
    # Versão e Autor (Puxando da classe)
    tk.Label(splash, text=app.APP_VERSION, font=("Segoe UI", 10), bg="#282828", fg="#A0A0A0").pack()
    tk.Label(splash, text=f"Created by: {app.APP_AUTHOR}", font=("Segoe UI", 9), bg="#282828", fg="#808080").pack(pady=(5, 0))
    
    # Texto de carregamento
    tk.Label(splash, text="Carregando sistema...", font=("Segoe UI", 8, "italic"), bg="#282828", fg="#606060").pack(side=tk.BOTTOM, pady=10)
    
    # Garante que o splash apareça antes de entrar no loop
    splash.update()

    # 4. Função para fechar o splash e mostrar o app
    def start_main_window():
        splash.destroy()
        root.deiconify() # Mostra a janela principal
    
    # Define o tempo do splash (2500ms = 2.5 segundos)
    root.after(2500, start_main_window)
    
    root.mainloop()