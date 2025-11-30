import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import threading
import time
import re
import os
import sys
import pyautogui
import ctypes

# --- UTILITÁRIOS GERAIS ---
def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def normalize_key(key):
    key = key.lower()
    mapping = {
        'return': 'enter', 'control_l': 'ctrl', 'control_r': 'ctrl',
        'shift_l': 'shift', 'shift_r': 'shift', 'alt_l': 'alt', 'alt_r': 'alt',
        'prior': 'pageup', 'next': 'pagedown', 'escape': 'esc',
        'caps_lock': 'capslock', 'num_lock': 'numlock', 'scroll_lock': 'scrolllock',
        'backspace': 'backspace', 'delete': 'delete', 'insert': 'insert',
        'home': 'home', 'end': 'end', 'up': 'up', 'down': 'down',
        'left': 'left', 'right': 'right', 'space': 'space', 'tab': 'tab',
        'win_l': 'win', 'win_r': 'win'
    }
    return mapping.get(key, key)

# --- CLASSES DE INTERFACE ---
class CreateToolTip:
    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.showtip)
        widget.bind("<Leave>", self.hidetip)
    def showtip(self, event=None):
        if self.tipwindow or not self.text: return
        x, y = self.widget.winfo_rootx() + 20, self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1)
        tw.configure(bg="#2b2b2b")
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self.text, justify=tk.LEFT, background="#ffffe0", relief=tk.SOLID, borderwidth=1, font=("tahoma", "8", "normal")).pack(ipadx=1)
    def hidetip(self, event=None):
        if self.tipwindow: self.tipwindow.destroy(); self.tipwindow = None

def add_hover_effect(widget, normal_bg, hover_bg):
    widget.bind("<Enter>", lambda e: widget.config(bg=hover_bg), add="+")
    widget.bind("<Leave>", lambda e: widget.config(bg=normal_bg), add="+")

# --- APLICAÇÃO PRINCIPAL ---
class MacroApp:
    def __init__(self, root):
        self.root = root
        self.APP_NAME = "MacTime Pro"
        self.APP_VERSION = "v3.1"
        self.APP_AUTHOR = "pdrGow2"
        self.APP_DESC = "Automação avançada com Interface Moderna."
        
        try: self.root.iconbitmap(resource_path("icone.ico"))
        except: pass
        
        # CORES
        self.colors = {
            "bg": "#2b2b2b", "card": "#404040", "card_hover": "#4a4a4a",  
            "card_selected": "#264f78", "text": "#ffffff", "accent": "#007acc",
            "timeline_bg": "#333333", "btn_active": "#007acc", "btn_inactive": "#3a3a3a"
        }
        
        self.root.title(self.APP_NAME)
        self.root.configure(bg=self.colors["bg"])
        self.root.geometry("940x550")
        
        self.executing, self.stop_requested, self.message_shown = False, False, False
        self.suppress_messages = False; self.interrupt_reason = None
        self.loaded_lists, self.loaded_index, self.list_settings = {}, {}, {}
        self.events = []
        
        # Drag & Drop
        self.drag_data = {"item_index": -1, "active": False, "ghost": None}
        self.last_selected_index = None
        
        self.create_ui()

    def create_ui(self):
        btn_frame = tk.Frame(self.root, bg=self.colors["bg"])
        btn_frame.pack(fill=tk.X, pady=10)
        left_frame = tk.Frame(btn_frame, bg=self.colors["bg"])
        left_frame.pack(side=tk.LEFT, padx=15)
        right_frame = tk.Frame(btn_frame, bg=self.colors["bg"])
        right_frame.pack(side=tk.RIGHT, padx=15)
        
        def create_emoji_button(parent, emoji, cmd, tip, bg="#404040", fg="white", width=4, font=("Segoe UI Emoji", 18)):
            btn = tk.Button(parent, text=emoji, command=cmd, font=font, width=width, height=1, 
                            relief=tk.FLAT, bd=0, bg=bg, fg=fg, cursor="hand2", anchor=tk.CENTER)
            CreateToolTip(btn, tip)
            add_hover_effect(btn, normal_bg=bg, hover_bg="#5a5a5a")
            return btn
        
        for btn_def in [("🖱️", self.capture_mouse_click, "Capturar Clique"), ("📝", self.add_text_event, "Adicionar Texto"), ("⌨️", self.add_key_event, "Adicionar Tecla"), ("⏱️", self.add_wait_event, "Adicionar Espera"), ("🗑️", self.add_clear_event, "Apagar Campo"), ("📋", self.load_timeline, "Carregar Lista")]:
            create_emoji_button(left_frame, *btn_def).pack(side=tk.LEFT, padx=2)
        
        move_frame = tk.Frame(left_frame, bg=self.colors["bg"]); move_frame.pack(side=tk.LEFT, padx=5)
        create_emoji_button(move_frame, "⬆️", self.move_selected_up, "Mover Cima", width=3, font=("Segoe UI Emoji", 10), bg="#3a3a3a").pack(side=tk.TOP, pady=1)
        create_emoji_button(move_frame, "⬇️", self.move_selected_down, "Mover Baixo", width=3, font=("Segoe UI Emoji", 10), bg="#3a3a3a").pack(side=tk.TOP, pady=1)
        
        create_emoji_button(right_frame, "📥", self.import_timeline, "Importar", bg="#007acc").pack(side=tk.LEFT, padx=2)
        create_emoji_button(right_frame, "📤", self.export_timeline, "Exportar", bg="#5a2d81").pack(side=tk.LEFT, padx=2)
        create_emoji_button(right_frame, "▶️", self.execute_with_loops, "Executar", bg="#28a745").pack(side=tk.LEFT, padx=2)
        create_emoji_button(right_frame, "⏹️", self.stop_execution, "Parar", bg="#d32f2f").pack(side=tk.LEFT, padx=2)
        create_emoji_button(right_frame, "❓", self.show_about, "Sobre").pack(side=tk.LEFT, padx=2)

        tl_container = tk.Frame(self.root, bg=self.colors["timeline_bg"], highlightthickness=1, highlightbackground="#505050")
        tl_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        self.canvas = tk.Canvas(tl_container, bg=self.colors["timeline_bg"], highlightthickness=0)
        self.scrollbar = tk.Scrollbar(tl_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.colors["timeline_bg"])
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas.find_all()[0], width=e.width))
        self.canvas.bind_all("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-1>", self.deselect_all)

    def _on_mouse_wheel(self, event):
        if self.scrollable_frame.winfo_height() > self.canvas.winfo_height():
            self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

    # --- TIMELINE ITEM ---
    def add_event(self, event_text, legend="", ignore=False):
        index = len(self.events)
        card = tk.Frame(self.scrollable_frame, bg=self.colors["card"], bd=0, pady=2)
        card.pack(fill=tk.X, pady=2, padx=5, expand=True)
        var = tk.BooleanVar(value=False)
        cb = tk.Checkbutton(card, variable=var, bg=self.colors["card"], bd=0, relief=tk.FLAT,
                             activebackground=self.colors["card"], selectcolor="black", fg="white", cursor="hand2")
        cb.pack(side=tk.LEFT, padx=8)
        icon = "🔹"
        if "Clique" in event_text: icon = "🖱️"
        elif "Digitar" in event_text: icon = "📝"
        elif "Tecla" in event_text: icon = "⌨️"
        elif "Esperar" in event_text: icon = "⏱️"
        elif "Lista" in event_text: icon = "📋"
        lbl = tk.Label(card, text=f"{icon}  {event_text}", bg=self.colors["card"], fg=self.colors["text"], font=("Segoe UI", 10), anchor="w", padx=5)
        lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)
        menu_btn = tk.Label(card, text="⋮", bg=self.colors["card"], fg="#aaaaaa", font=("Segoe UI", 14, "bold"), cursor="hand2", width=3)
        menu_btn.pack(side=tk.RIGHT, padx=5)
        
        lbl_legend = tk.Label(card, text=legend, bg=self.colors["card"], fg="#888888", font=("Segoe UI", 9, "italic"), anchor="e")
        if legend: lbl_legend.pack(side=tk.RIGHT, padx=10)
        
        item_data = {
            "frame": card, "checkvar": var, "label": lbl, "text": event_text, 
            "menu_btn": menu_btn, "cb": cb, "legend_lbl": lbl_legend,
            "legend": legend, "ignore": ignore
        }
        self.events.append(item_data)
        self.update_item_style_full(item_data)
        
        def on_click(e): self.handle_selection(index, e)
        def on_enter(e): 
            if not var.get(): self.update_item_color(item_data, self.colors["card_hover"])
        def on_leave(e):
            if not var.get(): self.update_item_color(item_data, self.colors["card"])
        
        def show_menu(e):
            m = tk.Menu(self.root, tearoff=0, bg="#2d2d2d", fg="white", font=("Segoe UI", 10))
            m.add_command(label="  Editar", command=lambda: self.on_double_click_event(None, lbl))
            m.add_command(label="  Legenda", command=lambda: self.edit_legend(item_data))
            ign_txt = "  Ativar" if item_data["ignore"] else "  Ignorar"
            m.add_command(label=ign_txt, command=lambda: self.toggle_ignore(item_data))
            m.add_separator()
            m.add_command(label="  Remover", command=lambda: self.delete_single_item(item_data))
            m.post(e.x_root, e.y_root)

        for w in [card, lbl, lbl_legend]:
            w.bind("<Button-1>", on_click)
            w.bind("<B1-Motion>", self.drag_motion)
            w.bind("<ButtonRelease-1>", self.drag_stop)
            w.bind("<Double-Button-1>", lambda e: self.on_double_click_event(e, lbl))
            w.bind("<Enter>", on_enter); w.bind("<Leave>", on_leave)
        menu_btn.bind("<Button-1>", show_menu)

    def update_item_style_full(self, item):
        bg_c = self.colors["card_selected"] if item["checkvar"].get() else self.colors["card"]
        if item["ignore"]:
            fnt = ("Segoe UI", 10, "overstrike")
            fg_c = "#777777"
        else:
            fnt = ("Segoe UI", 10)
            fg_c = self.colors["text"]
        item["label"].config(font=fnt, fg=fg_c)
        self.update_item_color(item, bg_c)

    def update_item_color(self, item, color):
        item["frame"].config(bg=color); item["label"].config(bg=color); item["menu_btn"].config(bg=color)
        item["cb"].config(bg=color, activebackground=color); item["legend_lbl"].config(bg=color)

    def refresh_timeline(self):
        data = []
        for item in self.events:
            data.append({
                "text": self._clean_text(item["label"].cget("text")),
                "full": getattr(item["label"], "full_text", None),
                "chk": item["checkvar"].get(),
                "legend": item["legend"],
                "ignore": item["ignore"]
            })
        for w in self.scrollable_frame.winfo_children(): w.destroy()
        self.events = []
        for d in data:
            self.add_event(d["text"], legend=d["legend"], ignore=d["ignore"])
            if d["full"]: self.events[-1]["label"].full_text = d["full"]
            self.events[-1]["checkvar"].set(d["chk"])
            self.update_item_style_full(self.events[-1])

    def _clean_text(self, text):
        return text.replace("🖱️  ", "").replace("📝  ", "").replace("⌨️  ", "").replace("⏱️  ", "").replace("📋  ", "").replace("🔹  ", "")

    # --- SELEÇÃO & DRAG ---
    def get_event_index(self, widget):
        for i, item in enumerate(self.events):
            if item["frame"] == widget or item["label"] == widget or item.get("legend_lbl") == widget: return i
        return -1

    def handle_selection(self, index, event):
        idx = self.get_event_index(event.widget)
        if idx == -1: idx = index
        ctrl, shift = (event.state & 0x0004), (event.state & 0x0001)
        if shift and self.last_selected_index is not None:
            start, end = min(self.last_selected_index, idx), max(self.last_selected_index, idx)
            if not ctrl: self.deselect_all(None)
            for i in range(start, end + 1):
                self.events[i]["checkvar"].set(True); self.update_item_style_full(self.events[i])
        elif ctrl:
            state = not self.events[idx]["checkvar"].get(); self.events[idx]["checkvar"].set(state)
            self.update_item_style_full(self.events[idx])
            self.last_selected_index = idx
        else:
            if not self.events[idx]["checkvar"].get():
                self.deselect_all(None); self.events[idx]["checkvar"].set(True)
                self.update_item_style_full(self.events[idx])
            self.last_selected_index = idx
        self.drag_data["item_index"] = idx; self.drag_data["active"] = True

    def deselect_all(self, event):
        for item in self.events: item["checkvar"].set(False); self.update_item_style_full(item)

    def drag_motion(self, event):
        if not self.drag_data["active"]: return
        if not self.drag_data["ghost"]:
            self.drag_data["ghost"] = tk.Toplevel(self.root)
            self.drag_data["ghost"].overrideredirect(True)
            self.drag_data["ghost"].attributes("-alpha", 0.6)
            self.drag_data["ghost"].configure(bg=self.colors["card_selected"])
            c = sum(1 for e in self.events if e["checkvar"].get())
            txt = f"Movendo {c} itens..." if c > 0 else f"{self._clean_text(self.events[self.drag_data['item_index']]['label'].cget('text'))[:30]}..."
            tk.Label(self.drag_data["ghost"], text=txt, bg=self.colors["card_selected"], fg="white", padx=10, pady=5, relief=tk.RIDGE, bd=2).pack()
        self.drag_data["ghost"].geometry(f"+{event.x_root + 15}+{event.y_root + 10}")
        target_idx = max(0, min((event.y_root - self.scrollable_frame.winfo_rooty()) // 38, len(self.events) - 1))
        sel = [i for i, ev in enumerate(self.events) if ev["checkvar"].get()]
        if not sel: sel = [self.drag_data["item_index"]]
        if target_idx not in sel:
            items = [self.events[i] for i in sel]
            for i in sorted(sel, reverse=True): del self.events[i]
            ins = max(0, target_idx - (len(items) - 1 if target_idx > sel[0] else 0))
            for item in reversed(items): self.events.insert(ins, item)
            self.refresh_timeline(); self.drag_data["item_index"] = target_idx 

    def drag_stop(self, event):
        self.drag_data["active"] = False
        if self.drag_data["ghost"]: self.drag_data["ghost"].destroy(); self.drag_data["ghost"] = None

    # --- UTILITÁRIOS E MENUS ---
    def toggle_ignore(self, item_data):
        item_data["ignore"] = not item_data["ignore"]
        self.update_item_style_full(item_data)

    def edit_legend(self, item_data):
        def content(win):
            tk.Label(win, text="Texto da Legenda:", bg="#2b2b2b", fg="#A0A0A0", font=("Segoe UI", 10)).pack(pady=(15, 5))
            e = tk.Entry(win, bg="#404040", fg="white", relief=tk.FLAT, font=("Segoe UI", 11)); e.pack(padx=20, fill=tk.X, ipady=3); e.insert(0, item_data["legend"]); e.focus(); win.user_data = e
        def confirm(win):
            txt = win.user_data.get().strip()
            item_data["legend"] = txt
            item_data["legend_lbl"].config(text=txt)
            if txt: item_data["legend_lbl"].pack(side=tk.RIGHT, padx=10)
            else: item_data["legend_lbl"].pack_forget()
            return True
        self._open_generic_dialog("Editar Legenda", 150, content, confirm)

    def on_double_click_event(self, event, lbl_widget=None):
        lbl = lbl_widget if lbl_widget else event.widget
        text = self._clean_text(lbl.cget("text"))
        class DummyLabel:
            def __init__(self, t, l): self.text = t; self.lbl = l
            def cget(self, p): return self.text
            def config(self, text): 
                icon = "🔹"
                if "Clique" in text: icon = "🖱️"
                elif "Digitar" in text: icon = "📝"
                elif "Tecla" in text: icon = "⌨️"
                elif "Esperar" in text: icon = "⏱️"
                elif "Lista" in text: icon = "📋"
                self.lbl.config(text=f"{icon}  {text}")
            @property
            def full_text(self): return getattr(self.lbl, "full_text", None)
            @full_text.setter
            def full_text(self, v): self.lbl.full_text = v
        dummy = DummyLabel(text, lbl)
        if any(x in text for x in ["Clique", "Duplo", "Botão", "Pressionar por", "repetido"]): self.edit_click_event(dummy)
        elif text.startswith("Digitar:"): self.edit_text_event(dummy)
        elif any(x in text for x in ["Pressionar", "Manter", "Tecla"]): self.edit_key_event(dummy)
        elif text.startswith("Esperar"): self.edit_wait_event(dummy)
        elif text.startswith("Lista:"): self.edit_list_event(dummy)

    def delete_single_item(self, item):
        if messagebox.askyesno("Confirmar", "Tem certeza que deseja remover este item?", parent=self.root):
            item["frame"].destroy(); self.events.remove(item); self.refresh_timeline()

    def delete_selected_events(self, event=None):
        sel = [item for item in self.events if item["checkvar"].get()]
        if not sel: return
        msg = "Tem certeza que deseja remover o item selecionado?" if len(sel) == 1 else f"Tem certeza que deseja remover {len(sel)} itens?"
        if messagebox.askyesno("Confirmar Exclusão", msg, parent=self.root):
            [item["frame"].destroy() for item in sel]
            for item in sel: self.events.remove(item)
            self.refresh_timeline()
    
    def move_selected_up(self): self._move_selection(-1)
    def move_selected_down(self): self._move_selection(1)
    def _move_selection(self, direction):
        sel = sorted([i for i, e in enumerate(self.events) if e["checkvar"].get()], reverse=(direction>0))
        for i in sel:
            if 0 <= i + direction < len(self.events) and not self.events[i+direction]["checkvar"].get():
                self.events[i], self.events[i+direction] = self.events[i+direction], self.events[i]
        self.refresh_timeline()

    # --- MODAIS ---
    def center_window(self, win, width, height):
        x, y = (self.root.winfo_screenwidth() - width) // 2, (self.root.winfo_screenheight() - height) // 2
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.configure(bg="#2b2b2b")
        try: win.iconbitmap(resource_path("icone.ico"))
        except: pass
        if win != self.root: win.transient(self.root); win.grab_set(); win.focus_force()

    def _open_generic_dialog(self, title, height, content_fn, confirm_fn, bind_return=True):
        win = tk.Toplevel(self.root); win.title(title); self.center_window(win, 400, height); win.attributes("-topmost", True)
        content_fn(win)
        def on_ok(event=None):
            res = confirm_fn(win)
            if res is True: win.destroy()
            elif isinstance(res, str): win.destroy(); self.root.update(); messagebox.showinfo("Sucesso", res, parent=self.root)
        
        bf = tk.Frame(win, bg="#2b2b2b"); bf.pack(side=tk.BOTTOM, pady=20, fill=tk.X)
        bs = tk.Button(bf, text="Salvar", command=on_ok, bg=self.colors["btn_active"], fg="white", font=("Segoe UI", 10, "bold"), bd=0, padx=20, pady=5, cursor="hand2")
        bs.pack(side=tk.RIGHT, padx=20); add_hover_effect(bs, self.colors["btn_active"], "#005f9e")
        bc = tk.Button(bf, text="Cancelar", command=win.destroy, bg="#d32f2f", fg="white", font=("Segoe UI", 10), bd=0, padx=10, pady=5, cursor="hand2")
        bc.pack(side=tk.RIGHT); add_hover_effect(bc, "#d32f2f", "#a52424")
        if bind_return: win.bind("<Return>", on_ok)
        win.focus_set()

    def _toggle_helper(self, parent, options, var, lbl_txt=None):
        if lbl_txt: tk.Label(parent, text=lbl_txt, bg="#2b2b2b", fg="white", font=("", 10, "bold")).pack(pady=(10, 5))
        fr = tk.Frame(parent, bg="#2b2b2b"); fr.pack()
        buttons = []
        def upd():
            curr = var.get()
            for b, v in buttons:
                if v == curr: b.config(bg=self.colors["btn_active"])
                else: b.config(bg=self.colors["btn_inactive"])
        for txt, val in options:
            b = tk.Button(fr, text=txt, command=lambda v=val: (var.set(v), upd()),
                          bg=self.colors["btn_inactive"], fg="white", relief=tk.FLAT, bd=0, width=10, pady=5, cursor="hand2")
            b.pack(side=tk.LEFT, padx=2)
            buttons.append((b, val))
        upd()

    # --- JANELAS ---
    def _open_mouse_dialog(self, title, initial_mode="Simples", initial_param="", on_confirm=None):
        win = tk.Toplevel(self.root); win.title(title); self.center_window(win, 400, 450); win.attributes("-topmost", True)
        tk.Label(win, text="Posicione o mouse e aperte ENTER.", padx=20, pady=10, bg="#2b2b2b", fg="#A0A0A0", font=("Segoe UI", 10)).pack(fill=tk.X)
        btn_var, type_var = tk.StringVar(value="Esq"), tk.StringVar(value="Simples")
        if "Direito" in initial_mode: btn_var.set("Dir")
        elif "Scroll" in initial_mode: btn_var.set("Scr")
        if "Duplo" in initial_mode: type_var.set("Duplo")
        elif "Pressionar" in initial_mode: type_var.set("Pres")
        elif "Repetido" in initial_mode: type_var.set("Rep")

        self._toggle_helper(win, [("Esquerdo","Esq"),("Scroll","Scr"),("Direito","Dir")], btn_var, "Botão")
        self._toggle_helper(win, [("Simples","Simples"),("Pressionar","Pres"),("Repetido","Rep"),("Duplo","Duplo")], type_var, "Tipo de Clique")

        p_fr = tk.Frame(win, bg="#2b2b2b"); p_fr.pack(pady=20)
        p_lbl = tk.Label(p_fr, text="", bg="#2b2b2b", fg="white"); p_lbl.pack(side=tk.LEFT)
        p_ent = tk.Entry(p_fr, width=8, justify="center"); p_ent.pack(side=tk.LEFT, padx=5); p_ent.insert(0, initial_param)
        
        def upd_ui(*a):
            t = type_var.get()
            if t == "Pres": p_lbl.config(text="Duração (s):"); p_fr.pack()
            elif t == "Rep": p_lbl.config(text="Repetir por (s):"); p_fr.pack()
            else: p_fr.pack_forget()
        type_var.trace("w", upd_ui); upd_ui()

        coord = tk.Label(win, text="X: 0  Y: 0", font=("Consolas", 16, "bold"), bg="#2b2b2b", fg="#00ff00"); coord.pack(pady=10)
        self._capturing = True
        def loop():
            if not win.winfo_exists() or not self._capturing: return
            try:
                if ctypes.windll.user32.GetAsyncKeyState(0x0D) & 0x8000: confirm(); return
                x,y = pyautogui.position()
                coord.config(text=f"X: {x}  Y: {y}")
            except: pass
            win.after(50, loop)
        
        def confirm(e=None):
            self._capturing = False
            x, y = pyautogui.position(); b, t = btn_var.get(), type_var.get()
            m_str = "Simples"
            if b == "Dir": m_str = "Botão Direito"
            elif b == "Scr": m_str = "Scroll"
            else:
                if t == "Duplo": m_str = "Duplo Clique"
                elif t == "Pres": m_str = "Pressionar"
                elif t == "Rep": m_str = "Repetido"
            if on_confirm: on_confirm(x, y, m_str, p_ent.get())
            win.destroy()

        loop(); win.bind("<Return>", confirm)
        bf = tk.Frame(win, bg="#2b2b2b"); bf.pack(side=tk.BOTTOM, pady=20, fill=tk.X)
        bs = tk.Button(bf, text="Gravar (ENTER)", command=confirm, bg=self.colors["btn_active"], fg="white", font=("", 10, "bold"), bd=0, height=2, cursor="hand2")
        bs.pack(fill=tk.X, padx=20); add_hover_effect(bs, self.colors["btn_active"], "#005f9e")
        bs.focus_set()

    def capture_mouse_click(self):
        def save(x, y, m, p):
            if m=="Simples": txt = f"Clique Simples em ({x}, {y})"
            elif m=="Duplo Clique": txt = f"Duplo Clique em ({x}, {y})"
            elif m=="Botão Direito": txt = f"Botão Direito em ({x}, {y})"
            elif m=="Scroll": txt = f"Scroll em ({x}, {y})"
            elif m=="Pressionar": txt = f"Pressionar por tempo em ({x}, {y}) - Duração: {p}s"
            else: txt = f"Clique repetido em ({x}, {y}) - Repetir por: {p}s"
            self.add_event(txt)
        self._open_mouse_dialog("Capturar Clique", on_confirm=save)

    def edit_click_event(self, label):
        t = label.cget("text"); m, p = "Simples", ""
        if "Pressionar" in t: 
            m = "Pressionar"; p = t.split("Duração: ")[1].replace("s","")
        elif "repetido" in t: 
            m = "Repetido"; p = t.split("Repetir por: ")[1].replace("s","")
        elif "Duplo" in t: m = "Duplo"
        elif "Direito" in t: m = "Direito"
        elif "Scroll" in t: m = "Scroll"
        def save(x, y, mo, pa):
            if mo=="Simples": txt = f"Clique Simples em ({x}, {y})"
            elif mo=="Duplo Clique": txt = f"Duplo Clique em ({x}, {y})"
            elif mo=="Botão Direito": txt = f"Botão Direito em ({x}, {y})"
            elif mo=="Scroll": txt = f"Scroll em ({x}, {y})"
            elif mo=="Pressionar": txt = f"Pressionar por tempo em ({x}, {y}) - Duração: {pa}s"
            else: txt = f"Clique repetido em ({x}, {y}) - Repetir por: {pa}s"
            label.config(text=txt)
        self._open_mouse_dialog("Editar Clique", m, p, save)

    def add_text_event(self):
        def content(win):
            t = tk.Text(win, height=10, bg="white", fg="black", relief=tk.FLAT, font=("Consolas", 10)); t.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
            t.focus(); win.user_data = t
        def confirm(win):
            txt = win.user_data.get("1.0", tk.END).strip()
            if txt: 
                self.add_event(f"Digitar: {txt.splitlines()[0][:30]}...")
                self.events[-1]["label"].full_text = txt
            return True
        self._open_generic_dialog("Adicionar Texto", 450, content, confirm, bind_return=False)

    def edit_text_event(self, label):
        full = label.full_text if hasattr(label, "full_text") else label.cget("text").replace("Digitar:", "").strip()
        def content(win):
            t = tk.Text(win, height=10, bg="white", fg="black", relief=tk.FLAT, font=("Consolas", 10)); t.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
            t.insert("1.0", full); t.focus(); win.user_data = t
        def confirm(win):
            txt = win.user_data.get("1.0", tk.END).strip()
            label.config(text=f"Digitar: {txt.splitlines()[0][:30]}...")
            label.full_text = txt
            return True
        self._open_generic_dialog("Editar Texto", 450, content, confirm, bind_return=False)

    def _open_key_dialog(self, title, initial_mode="Simples", initial_keys=None, initial_duration="", on_confirm=None):
        keys_captured = list(initial_keys) if initial_keys else []
        def content(win):
            tk.Label(win, text="Pressione as teclas.", bg="#2b2b2b", fg="#ccc").pack(pady=5)
            mode = tk.StringVar(value=initial_mode)
            self._toggle_helper(win, [("Simples","Simples"), ("Manter","Manter"), ("Repetida","Repetida")], mode)
            row = tk.Frame(win, bg="#2b2b2b"); row.pack(pady=15)
            tk.Label(row, text="Combinação:", bg="#2b2b2b", fg="white", font=("",10,"bold")).pack(side=tk.LEFT, padx=5)
            ent = tk.Entry(row, width=20, justify="center", bg="#404040", fg="white", relief=tk.FLAT); ent.pack(side=tk.LEFT, padx=5, ipady=3)
            ent.insert(0, "+".join(keys_captured))
            tk.Button(row, text="🗑️", command=lambda: (keys_captured.clear(), ent.delete(0, tk.END)), bg="#505050", fg="white", bd=0, width=3, cursor="hand2").pack(side=tk.LEFT, padx=5)
            p_fr = tk.Frame(win, bg="#2b2b2b"); p_fr.pack(pady=5)
            lbl_p = tk.Label(p_fr, text="Tempo (s):", bg="#2b2b2b", fg="white"); lbl_p.pack(side=tk.LEFT)
            p_ent = tk.Entry(p_fr, width=6, justify="center"); p_ent.pack(side=tk.LEFT, padx=5); p_ent.insert(0, initial_duration)
            def upd(*a):
                m = mode.get()
                if m == "Simples": p_fr.pack_forget()
                elif m == "Manter": p_fr.pack(); lbl_p.config(text="Duração (s):")
                elif m == "Repetida": p_fr.pack(); lbl_p.config(text="Quantidade:")
            mode.trace("w", upd); upd()
            def on_k(e):
                if e.keysym not in keys_captured: keys_captured.append(e.keysym)
                ent.delete(0, tk.END); ent.insert(0, "+".join(keys_captured)); return "break"
            ent.bind("<KeyPress>", on_k); ent.focus()
            win.user_data = {"m": mode, "k": keys_captured, "p": p_ent}

        def confirm(win):
            d = win.user_data; k = d["k"]; m = d["m"].get(); p = d["p"].get()
            if not k: return False
            if on_confirm: on_confirm(m, k, p.strip() or "1")
            return True
        self._open_generic_dialog(title, 320, content, confirm)

    def add_key_event(self):
        self._open_key_dialog("Adicionar Tecla", on_confirm=lambda m, k, d: self.add_event(f"Pressionar Tecla: {'+'.join(k)}" if m=="Simples" else f"Manter pressionada: {'+'.join(k)} - Duração: {d}s" if m=="Manter" else f"Tecla repetida: {'+'.join(k)} - Repetir: {d}x"))

    def edit_key_event(self, label):
        txt = label.cget("text"); m, k, d = "Simples", [], ""
        if " - Duração: " in txt: 
            m="Manter"; k=txt.split(" - Duração: ")[0].replace("Manter pressionada: ", "").split("+")
            d=txt.split(" - Duração: ")[1].replace("s","")
        elif " - Repetir: " in txt: 
            m="Repetida"; k=txt.split(" - Repetir: ")[0].replace("Tecla repetida: ", "").split("+")
            d=txt.split(" - Repetir: ")[1].replace("x","")
        elif "Pressionar Tecla: " in txt: k=txt.replace("Pressionar Tecla: ", "").split("+")
        def save(mode, keys, dur):
            label.config(text=f"Pressionar Tecla: {'+'.join(keys)}" if mode=="Simples" else f"Manter pressionada: {'+'.join(keys)} - Duração: {dur}s" if mode=="Manter" else f"Tecla repetida: {'+'.join(keys)} - Repetir: {dur}x")
        self._open_key_dialog("Editar Tecla", m, k, d, save)

    # Lista
    def load_timeline(self):
        def content(win):
            tk.Label(win, text="Selecione o arquivo (.txt):", bg="#2b2b2b", fg="#A0A0A0", font=("Segoe UI", 10), anchor="w").pack(fill=tk.X, pady=(15, 5))
            fr = tk.Frame(win, bg="#2b2b2b"); fr.pack(fill=tk.X, pady=5)
            path = tk.StringVar()
            entry = tk.Entry(fr, textvariable=path, bg="#404040", fg="white", relief=tk.FLAT, font=("Segoe UI", 11))
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 5))
            btn_folder = tk.Button(fr, text="📂", command=lambda: path.set(filedialog.askopenfilename(filetypes=[("Txt","*.txt")])), 
                                   bg="#505050", fg="white", bd=0, font=("Segoe UI Emoji", 12), width=4, cursor="hand2")
            btn_folder.pack(side=tk.RIGHT); add_hover_effect(btn_folder, "#505050", "#666666")
            ign = tk.BooleanVar()
            cb = tk.Checkbutton(win, text="Ignorar linhas em branco", variable=ign, 
                                bg="#2b2b2b", fg="white", selectcolor="black", 
                                activebackground="#2b2b2b", font=("Segoe UI", 11), cursor="hand2")
            cb.pack(anchor="w", pady=15)
            win.user_data = {"p": path, "i": ign}
        
        def confirm(win):
            p = win.user_data["p"].get(); i = win.user_data["i"].get()
            if not p: return False
            try:
                with open(p, "r") as f: l = f.read().splitlines()
                items = [x.strip() for x in l if (x.strip() if i else True)]
                fp = os.path.abspath(p)
                self.loaded_lists[fp] = items; self.loaded_index[fp] = 0; self.list_settings[fp] = i
                if not any(f"Lista: {fp}" in e["label"].cget("text") for e in self.events): self.add_event(f"Lista: {fp}")
                return f"Carregado {len(items)} itens." 
            except Exception as e: messagebox.showerror("Erro", str(e), parent=self.root); return False
        self._open_generic_dialog("Carregar Lista", 250, content, confirm)

    def edit_list_event(self, label): self.load_timeline() 

    # Wait/Clear
    def _wait_diag(self, title, val, cb):
        def content(win):
            tk.Label(win, text="Tempo de Espera", bg="#2b2b2b", fg="#A0A0A0", font=("Segoe UI", 10)).pack(pady=(15, 5))
            fr = tk.Frame(win, bg="#2b2b2b"); fr.pack(pady=5)
            e = tk.Entry(fr, justify="center", bg="#404040", fg="white", relief=tk.FLAT, font=("Segoe UI", 20, "bold"), width=6)
            e.pack(side=tk.LEFT); e.insert(0, val); e.focus()
            tk.Label(fr, text="segundos", bg="#2b2b2b", fg="white", font=("Segoe UI", 12)).pack(side=tk.LEFT, padx=10)
            win.user_data=e
        def ok(win):
            v = win.user_data.get().replace(",", ".")
            try:
                if float(v) >= 0: cb(v); return True
            except: pass
            return False
        self._open_generic_dialog(title, 200, content, ok)

    def add_wait_event(self): self._wait_diag("Adicionar Espera", "", lambda v: self.add_event(f"Esperar {v} segundos"))
    def edit_wait_event(self, l): 
        exist = re.search(r"(\d+\.?\d*)", l.cget("text")).group(1)
        self._wait_diag("Editar Espera", exist, lambda v: l.config(text=f"Esperar {v} segundos"))
    def add_clear_event(self): self.add_event("Apagar Campo")

    # EXPORT/IMPORT/SOBRE
    def show_about(self):
        win = tk.Toplevel(self.root); win.title("Sobre"); self.center_window(win, 400, 250); win.attributes("-topmost", True)
        try: tk.Label(win, text="🖱️", font=("", 40), bg="#2b2b2b", fg="white").pack()
        except: pass
        tk.Label(win, text=f"{self.APP_NAME} {self.APP_VERSION}", font=("", 14, "bold"), bg="#2b2b2b", fg="white").pack()
        tk.Label(win, text=f"by {self.APP_AUTHOR}", bg="#2b2b2b", fg="#888").pack()
        tk.Label(win, text=self.APP_DESC, bg="#333", fg="#ccc", padx=10, pady=10).pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

    def export_timeline(self):
        f = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Txt","*.txt")])
        if f:
            with open(f, "w") as file:
                for item in self.events:
                    t = self._clean_text(item["label"].cget("text"))
                    extras = []
                    if item["ignore"]: extras.append("ignore=True")
                    if item["legend"]: extras.append(f"legend={item['legend']}")
                    extra_str = " | ".join(extras)
                    if extra_str: extra_str = " | " + extra_str

                    if t.startswith("Digitar:") and hasattr(item["label"], "full_text"):
                        file.write(f"Digitar: <<START>>{extra_str}\n{item['label'].full_text}\n<<END>>\n")
                    elif t.startswith("Lista:"): 
                        p = t.split("Lista:")[1].strip()
                        ign_blank = self.list_settings.get(p, False)
                        line = f"Lista: {p} | list_ignore={ign_blank}"
                        if item["ignore"]: line += " | ignore=True"
                        if item["legend"]: line += f" | legend={item['legend']}"
                        file.write(line + "\n")
                    else:
                        file.write(t + extra_str + "\n")
            messagebox.showinfo("Sucesso", "Exportado.")

    def import_timeline(self):
        f = filedialog.askopenfilename(filetypes=[("Txt","*.txt")])
        if f:
            with open(f, "r") as file: lines = file.readlines()
            for w in self.scrollable_frame.winfo_children(): w.destroy()
            self.events = []; self.list_settings = {}; i = 0
            while i < len(lines):
                l = lines[i].rstrip()
                legend = ""; ignore = False
                if " | " in l:
                    parts = l.split(" | ")
                    clean_l = parts[0]
                    for p in parts[1:]:
                        if p.startswith("legend="): legend = p.replace("legend=", "")
                        if p == "ignore=True": ignore = True
                    l = clean_l
                
                if l.startswith("Digitar: <<START>>"):
                    full, i = [], i+1
                    while i < len(lines) and lines[i].strip() != "<<END>>": full.append(lines[i].rstrip()); i+=1
                    self.add_event(f"Digitar: {' '.join(full)[:30]}...", legend=legend, ignore=ignore)
                    self.events[-1]["label"].full_text = "\n".join(full)
                elif l.startswith("Lista:"):
                    raw_line = lines[i].rstrip()
                    list_ign = "list_ignore=True" in raw_line
                    p = l.replace("Lista: ", "").strip()
                    self.list_settings[p] = list_ign
                    self.add_event(f"Lista: {p}", legend=legend, ignore=ignore)
                elif l: self.add_event(l, legend=legend, ignore=ignore)
                i+=1
            messagebox.showinfo("Sucesso", "Importado.")

    # EXECUÇÃO
    def stop_execution(self):
        if not self.stop_requested: self.interrupt_reason = "Parado pelo usuário."; self.stop_requested = True; self._show_message("Parado", self.interrupt_reason)

    def _show_message(self, t, m):
        if not self.message_shown: self.message_shown = True; self.root.after(0, lambda: messagebox.showinfo(t, m, parent=self.root))

    def execute_with_loops(self):
        win = tk.Toplevel(self.root); win.title("Loop"); self.center_window(win, 350, 220); win.attributes("-topmost", True)
        tk.Label(win, text="Repetições", bg="#2b2b2b", fg="#A0A0A0", font=("Segoe UI", 11)).pack(pady=(20, 5))
        e = tk.Entry(win, justify="center", font=("Segoe UI", 30, "bold"), bg="#2b2b2b", fg=self.colors["accent"], bd=0, width=5)
        e.pack(pady=5); e.insert(0, "1"); tk.Frame(win, bg=self.colors["accent"], height=2, width=100).pack()
        e.focus(); e.select_range(0, tk.END)
        res = {"n": None}
        def ok(ev=None): 
            if e.get().isdigit(): res["n"] = int(e.get()); win.destroy()
        win.bind("<Return>", ok)
        bf = tk.Frame(win, bg="#2b2b2b"); bf.pack(side=tk.BOTTOM, pady=25, fill=tk.X)
        b_run = tk.Button(bf, text="▶ INICIAR", command=ok, bg="#28a745", fg="white", font=("Segoe UI", 10, "bold"), bd=0, padx=20, pady=8, cursor="hand2")
        b_run.pack(side=tk.RIGHT, padx=20); add_hover_effect(b_run, "#28a745", "#34ce57")
        b_can = tk.Button(bf, text="Cancelar", command=win.destroy, bg="#d32f2f", fg="white", font=("Segoe UI", 10), bd=0, padx=10, pady=8, cursor="hand2")
        b_can.pack(side=tk.RIGHT); add_hover_effect(b_can, "#d32f2f", "#ff4d4d")
        self.root.wait_window(win)
        if res["n"]: self.prepare_and_start(res["n"])

    def prepare_and_start(self, loops):
        active_events = [e for e in self.events if not e["ignore"]]
        req_files = set()
        for item in active_events:
            txt = self._clean_text(item["label"].cget("text"))
            if "Lista:" in txt:
                req_files.add(txt.split("Lista:")[1].strip())

        for p in req_files:
            if not os.path.exists(p): messagebox.showerror("Erro", f"Lista não encontrada: {p}"); return
            try: 
                with open(p, "r") as f: l = f.read().splitlines()
                ign = self.list_settings.get(p, False)
                self.loaded_lists[p] = [x.strip() for x in l if (x.strip() if ign else True)]
                self.loaded_index[p] = 0
            except: messagebox.showerror("Erro", f"Erro ao ler: {p}"); return
        
        self.stop_requested, self.executing, self.message_shown = False, True, False
        self.start_visual_countdown(req_files, loops)

    def start_visual_countdown(self, files, loops):
        cw = tk.Toplevel(self.root); cw.overrideredirect(True); cw.attributes("-topmost", True)
        self.center_window(cw, 320, 180); cw.focus_force()
        main_fr = tk.Frame(cw, bg="white", highlightthickness=3, highlightbackground="#1e1e1e")
        main_fr.pack(fill=tk.BOTH, expand=True)
        tk.Label(main_fr, text=f"Iniciando {loops}x em:", font=("Segoe UI", 14), bg="white", fg="#333").pack(pady=(15, 5))
        num = tk.Label(main_fr, text="3", font=("Segoe UI", 50, "bold"), bg="white", fg="#FF5722"); num.pack()
        tk.Label(main_fr, text="Sacuda o mouse para cancelar", bg="white", fg="#999", font=("Segoe UI", 9, "italic")).pack(pady=(0, 15))
        
        threading.Thread(target=self._monitor_shake, daemon=True).start()
        def check():
            if self.stop_requested: cw.destroy(); self.executing = False
            elif cw.winfo_exists(): cw.after(50, check)
        check()
        def timer(c):
            if not cw.winfo_exists() or self.stop_requested: return
            try: cw.lift(); cw.attributes("-topmost", True)
            except: pass
            num.config(text=str(c))
            if c > 0: cw.after(1000, timer, c-1)
            else: cw.destroy(); threading.Thread(target=self._worker, args=(files, loops)).start()
        timer(3)

    def _monitor_shake(self):
        last = pyautogui.position(); score = 0; lx, ly = 0, 0
        try:
            while self.executing and not self.stop_requested:
                time.sleep(0.05)
                curr = pyautogui.position()
                dx, dy = curr.x - last.x, curr.y - last.y
                move = False
                if abs(dx) > 100:
                    cdx = 1 if dx > 0 else -1
                    if cdx != lx and lx != 0: score += 1; move = True
                    lx = cdx
                if abs(dy) > 100:
                    cdy = 1 if dy > 0 else -1
                    if cdy != ly and ly != 0: score += 1; move = True
                    ly = cdy
                if not move and score > 0: score = max(0, score - 0.1)
                last = curr
                if score >= 4:
                    self.interrupt_reason = "Sacudida detectada!"; self.stop_requested = True; self._show_message("Parado", self.interrupt_reason); break
        except: pass

    def _worker(self, files, loops):
        for i in range(loops):
            if self.stop_requested: break
            for p in files: 
                if p in self.loaded_lists: self.loaded_index[p] = 0
            
            active_events = [e for e in self.events if not e["ignore"]]
            if not active_events: break

            has_list = any("Lista:" in self._clean_text(e["label"].cget("text")) for e in active_events)
            if has_list:
                active_lists = {self._clean_text(e["label"].cget("text")).split("Lista:")[1].strip() for e in active_events if "Lista:" in self._clean_text(e["label"].cget("text"))}
                
                while not self.stop_requested and any(self.loaded_index[f] < len(self.loaded_lists[f]) for f in active_lists if f in self.loaded_lists):
                    for item in active_events: 
                        if self.stop_requested: break
                        self._execute_event_action(item)
            else:
                for item in active_events:
                    if self.stop_requested: break
                    self._execute_event_action(item)
            
            if i < loops - 1: time.sleep(0.5)
        
        self.executing = False
        if not self.stop_requested and not self.message_shown: self._show_message("Fim", "Concluído com sucesso.")

    def _execute_event_action(self, item):
        if self.stop_requested: return
        if item["ignore"]: return

        text = self._clean_text(item["label"].cget("text"))
        
        if " em (" in text:
            m = re.search(r"\((\d+),\s*(\d+)\)", text); x, y = int(m.group(1)), int(m.group(2))
            if "Direito" in text: pyautogui.click(x, y, button="right")
            elif "Duplo" in text: pyautogui.doubleClick(x, y)
            elif "Scroll" in text: pyautogui.click(x, y, button="middle")
            elif "Pressionar por" in text: 
                d = float(re.search(r"Duração: (\d+\.?\d*)s", text).group(1)); pyautogui.mouseDown(x, y); time.sleep(d); pyautogui.mouseUp(x, y)
            elif "repetido" in text:
                d = float(re.search(r"Repetir por: (\d+\.?\d*)s", text).group(1)); end = time.time() + d
                while time.time() < end and not self.stop_requested: pyautogui.click(x, y); time.sleep(0.1)
            else: pyautogui.click(x, y)
            time.sleep(0.2)
        elif "Digitar:" in text:
            ft = item["label"].full_text if hasattr(item["label"], "full_text") else text.replace("Digitar:", "").strip()
            self.root.clipboard_clear()
            self.root.clipboard_append(ft)
            self.root.update()
            time.sleep(0.1)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.2)
        elif "Tecla" in text or "pressionada" in text:
            try:
                if "Pressionar Tecla" in text: 
                    k = [normalize_key(x) for x in text.replace("Pressionar Tecla: ", "").strip().split("+")]
                    pyautogui.hotkey(*k)
                elif "Manter" in text:
                    # Manter AGORA É RAPID FIRE (SPAM)
                    parts = text.split(" - Duração: ")
                    d = float(parts[1].replace("s","").strip())
                    k = [normalize_key(x) for x in parts[0].replace("Manter pressionada: ", "").split("+")]
                    
                    end_time = time.time() + d
                    while time.time() < end_time:
                        if self.stop_requested: break
                        pyautogui.hotkey(*k)
                        time.sleep(0.05) # ~20x por segundo
                        
                elif "repetida" in text:
                    # Repetida AGORA É QUANTIDADE
                    parts = text.split(" - Repetir: ")
                    count = int(parts[1].replace("x","").strip())
                    k = [normalize_key(x) for x in parts[0].replace("Tecla repetida: ", "").split("+")]
                    
                    for _ in range(count):
                        if self.stop_requested: break
                        pyautogui.hotkey(*k)
                        time.sleep(0.05)
            except Exception as e: print(f"Erro tecla: {e}")
            time.sleep(0.2)
        elif "Esperar" in text:
            s = float(re.search(r"Esperar (\d+\.?\d*)", text).group(1))
            for _ in range(int(s*10)): 
                if self.stop_requested: break
                time.sleep(0.1)
        elif "Apagar" in text: pyautogui.hotkey("ctrl", "a"); pyautogui.press("backspace"); time.sleep(0.2)
        elif "Lista:" in text:
            try:
                p = text.split("Lista:")[1].strip()
                if p in self.loaded_lists and self.loaded_index[p] < len(self.loaded_lists[p]):
                    val = self.loaded_lists[p][self.loaded_index[p]]
                    self.root.clipboard_clear(); self.root.clipboard_append(val); self.root.update()
                    pyautogui.hotkey("ctrl", "v")
                    self.loaded_index[p] += 1; time.sleep(0.2)
            except: pass

if __name__ == "__main__":
    root = tk.Tk(); root.withdraw()
    app = MacroApp(root)
    root.bind("<Delete>", lambda e: app.delete_selected_events())
    
    splash = tk.Toplevel(root); splash.overrideredirect(True); splash.configure(bg="#2b2b2b")
    w, h = 350, 260; sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    splash.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
    
    try:
        img = tk.PhotoImage(file=resource_path("logo.png"))
        lbl_icon = tk.Label(splash, image=img, bg="#2b2b2b"); lbl_icon.image = img; lbl_icon.pack(pady=(15,0))
    except:
        try: tk.Label(splash, text="🖱️", font=("", 60), bg="#2b2b2b", fg="white").pack(pady=(15,0))
        except: pass

    tk.Label(splash, text=app.APP_NAME, font=("", 18, "bold"), bg="#2b2b2b", fg="white").pack()
    tk.Label(splash, text=app.APP_VERSION, font=("", 10), bg="#2b2b2b", fg="#aaa").pack()
    tk.Label(splash, text=f"Created by: {app.APP_AUTHOR}", font=("", 9), bg="#2b2b2b", fg="#808080").pack(pady=(5, 0))
    tk.Label(splash, text="Carregando...", font=("", 8, "italic"), bg="#2b2b2b", fg="#666").pack(side=tk.BOTTOM, pady=10)
    splash.update()
    root.after(2000, lambda: (splash.destroy(), root.deiconify()))
    root.mainloop()