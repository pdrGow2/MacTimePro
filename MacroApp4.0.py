import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import threading
import time
import re
import os
import sys
import pyautogui
import ctypes
import copy

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

class CreateToolTip:
    def __init__(self, widget, text='widget info'):
        self.widget = widget; self.text = text; self.tipwindow = None
        widget.bind("<Enter>", self.showtip); widget.bind("<Leave>", self.hidetip)
    def showtip(self, event=None):
        if self.tipwindow or not self.text: return
        x, y = self.widget.winfo_rootx() + 20, self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(1); tw.configure(bg="#2b2b2b")
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(tw, text=self.text, justify=tk.LEFT, background="#ffffe0", relief=tk.SOLID, borderwidth=1, font=("tahoma", "8", "normal")).pack(ipadx=1)
    def hidetip(self, event=None):
        if self.tipwindow: self.tipwindow.destroy(); self.tipwindow = None

def add_hover_effect(widget, normal_bg, hover_bg):
    widget.bind("<Enter>", lambda e: widget.config(bg=hover_bg), add="+")
    widget.bind("<Leave>", lambda e: widget.config(bg=normal_bg), add="+")

# --- APP PRINCIPAL ---
class MacroApp:
    def __init__(self, root):
        self.root = root
        self.APP_NAME = "MacTime Pro"
        self.APP_VERSION = "v4.0"
        self.APP_AUTHOR = "pdrGow2"
        self.FILE_VERSION = "4.0" 
        self.APP_DESC = "Automação com suporte a Grupos, Pastas e UX Avançada."
        
        try: self.root.iconbitmap(resource_path("icone.ico"))
        except: pass
        
        self.colors = {
            "bg": "#2b2b2b", "card": "#404040", "card_hover": "#4a4a4a",  
            "card_selected": "#264f78", "text": "#ffffff", "accent": "#007acc",
            "timeline_bg": "#333333", "btn_active": "#007acc", "btn_inactive": "#3a3a3a",
            "group_bg": "#252526", "group_border": "#555555"
        }
        
        self.root.title(self.APP_NAME); self.root.configure(bg=self.colors["bg"]); self.root.geometry("940x600")
        
        self.executing, self.stop_requested, self.message_shown = False, False, False
        self.suppress_messages, self.interrupt_reason = False, None
        self.loaded_lists, self.loaded_index, self.list_settings = {}, {}, {}
        
        self.events = [] 
        self.history = []; self.history_index = -1; self.is_undoing = False
        
        self.drag_data = {"item_index": -1, "active": False, "ghost": None, "moved": False}
        self.last_selected_index = None

        self.root.bind("<Control-z>", self.undo); self.root.bind("<Control-y>", self.redo)
        self.create_ui()
        self.save_history()

    # --- HISTÓRICO ---
    def get_snapshot(self):
        return {
            "events": self._serialize_events(self.events),
            "list_settings": copy.deepcopy(self.list_settings)
        }

    def _serialize_events(self, event_list):
        serial = []
        for item in event_list:
            data = {
                "type": item.get("type", "action"),
                "text": self._clean_text(item["label"].cget("text")) if item.get("label") else item["text"],
                "chk": item["checkvar"].get(),
                "legend": item["legend"],
                "ignore": item["ignore"]
            }
            if data["type"] == "action":
                data["full"] = getattr(item["label"], "full_text", None)
            elif data["type"] == "group":
                data["expanded"] = item["expanded"]
                data["children"] = self._serialize_events(item["children"])
            serial.append(data)
        return serial

    def save_history(self):
        if self.is_undoing: return
        if self.history_index < len(self.history) - 1: self.history = self.history[:self.history_index + 1]
        current_state = self.get_snapshot()
        if self.history and self.history[-1] == current_state: return
        self.history.append(current_state)
        self.history_index += 1
        if len(self.history) > 50: self.history.pop(0); self.history_index -= 1

    def restore_snapshot(self, snapshot):
        self.is_undoing = True
        self.list_settings = copy.deepcopy(snapshot["list_settings"])
        for w in self.scrollable_frame.winfo_children(): w.destroy()
        self.events = []
        self._rebuild_from_serial(snapshot["events"], self.events)
        self.is_undoing = False

    def _rebuild_from_serial(self, serial_list, target_list, parent_frame=None):
        target_ui_frame = parent_frame if parent_frame else self.scrollable_frame
        for d in serial_list:
            if d["type"] == "action":
                self.add_event(d["text"], legend=d["legend"], ignore=d["ignore"], save=False, target_list=target_list, parent_ui=target_ui_frame)
                if d["full"]: target_list[-1]["label"].full_text = d["full"]
                target_list[-1]["checkvar"].set(d["chk"])
                self.update_item_style_full(target_list[-1])
            elif d["type"] == "group":
                self.add_group(d["text"], legend=d["legend"], ignore=d["ignore"], expanded=d["expanded"], save=False, target_list=target_list, parent_ui=target_ui_frame)
                grp = target_list[-1]
                grp["checkvar"].set(d["chk"])
                self._rebuild_from_serial(d["children"], grp["children"], grp["child_frame"])
                self.update_group_style(grp)

    def undo(self, event=None):
        if self.history_index > 0: self.history_index -= 1; self.restore_snapshot(self.history[self.history_index])
    def redo(self, event=None):
        if self.history_index < len(self.history) - 1: self.history_index += 1; self.restore_snapshot(self.history[self.history_index])

    # --- UI ---
    def create_ui(self):
        btn_frame = tk.Frame(self.root, bg=self.colors["bg"]); btn_frame.pack(fill=tk.X, pady=10)
        left_frame = tk.Frame(btn_frame, bg=self.colors["bg"]); left_frame.pack(side=tk.LEFT, padx=15)
        right_frame = tk.Frame(btn_frame, bg=self.colors["bg"]); right_frame.pack(side=tk.RIGHT, padx=15)
        
        def mkbtn(p, e, c, t, b="#404040", w=4):
            x = tk.Button(p, text=e, command=c, font=("Segoe UI Emoji", 18), width=w, height=1, relief=tk.FLAT, bd=0, bg=b, fg="white", cursor="hand2", anchor=tk.CENTER)
            CreateToolTip(x, t); add_hover_effect(x, b, "#5a5a5a"); return x
        
        for b in [("🖱️", self.capture_mouse_click, "Capturar Clique"), ("📝", self.add_text_event, "Adicionar Texto"), ("⌨️", self.add_key_event, "Adicionar Tecla"), ("⏱️", self.add_wait_event, "Adicionar Espera"), ("🗑️", self.add_clear_event, "Apagar Campo"), ("📋", self.load_timeline, "Carregar Lista")]:
            mkbtn(left_frame, *b).pack(side=tk.LEFT, padx=2)
        
        mf = tk.Frame(left_frame, bg=self.colors["bg"]); mf.pack(side=tk.LEFT, padx=5)
        mkbtn(mf, "⬆️", self.move_selected_up, "Cima", "#3a3a3a", 3).pack(pady=1)
        mkbtn(mf, "⬇️", self.move_selected_down, "Baixo", "#3a3a3a", 3).pack(pady=1)
        
        mkbtn(right_frame, "📥", self.import_timeline, "Importar", "#007acc").pack(side=tk.LEFT, padx=2)
        mkbtn(right_frame, "📤", self.export_timeline, "Exportar", "#5a2d81").pack(side=tk.LEFT, padx=2)
        mkbtn(right_frame, "▶️", self.execute_with_loops, "Executar", "#28a745").pack(side=tk.LEFT, padx=2)
        mkbtn(right_frame, "⏹️", self.stop_execution, "Parar", "#d32f2f").pack(side=tk.LEFT, padx=2)
        mkbtn(right_frame, "❓", self.show_about, "Sobre").pack(side=tk.LEFT, padx=2)

        tl_c = tk.Frame(self.root, bg=self.colors["timeline_bg"], highlightthickness=1, highlightbackground="#505050")
        tl_c.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        self.cv = tk.Canvas(tl_c, bg=self.colors["timeline_bg"], highlightthickness=0)
        self.sb = tk.Scrollbar(tl_c, orient=tk.VERTICAL, command=self.cv.yview)
        self.scrollable_frame = tk.Frame(self.cv, bg=self.colors["timeline_bg"])
        self.cv.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.cv.configure(yscrollcommand=self.sb.set)
        self.cv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True); self.sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.scrollable_frame.bind("<Configure>", lambda e: self.cv.configure(scrollregion=self.cv.bbox("all")))
        self.cv.bind("<Configure>", lambda e: self.cv.itemconfig(self.cv.find_all()[0], width=e.width))
        self.cv.bind_all("<MouseWheel>", lambda e: self.cv.yview_scroll(-1*(e.delta//120), "units") if self.scrollable_frame.winfo_height() > self.cv.winfo_height() else None)
        self.cv.bind("<Button-1>", self.deselect_all)

    # --- ITENS (AÇÃO e GRUPO) ---
    def add_group(self, title="Novo Grupo", legend="", ignore=False, expanded=True, save=True, target_list=None, parent_ui=None):
        dest_list = target_list if target_list is not None else self.events
        parent_widget = parent_ui if parent_ui else self.scrollable_frame
        
        group_main = tk.Frame(parent_widget, bg=self.colors["timeline_bg"], bd=0, pady=2)
        group_main.pack(fill=tk.X, pady=5, padx=2)
        header = tk.Frame(group_main, bg=self.colors["group_bg"], bd=1, relief=tk.RAISED)
        header.pack(fill=tk.X, ipady=2)
        
        var = tk.BooleanVar(value=False)
        btn_exp = tk.Label(header, text="▼" if expanded else "▶", bg=self.colors["group_bg"], fg="#ccc", cursor="hand2", font=("", 10))
        btn_exp.pack(side=tk.LEFT, padx=5)
        cb = tk.Checkbutton(header, variable=var, bg=self.colors["group_bg"], bd=0, relief=tk.FLAT, selectcolor="black", activebackground=self.colors["group_bg"])
        cb.pack(side=tk.LEFT, padx=2)
        icon_lbl = tk.Label(header, text="📁", bg=self.colors["group_bg"], fg="#ffca28", font=("Segoe UI Emoji", 12))
        icon_lbl.pack(side=tk.LEFT)
        lbl = tk.Label(header, text=title, bg=self.colors["group_bg"], fg="white", font=("Segoe UI", 10, "bold"), anchor="w")
        lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)
        menu_btn = tk.Label(header, text="⋮", bg=self.colors["group_bg"], fg="#aaaaaa", cursor="hand2", width=3)
        menu_btn.pack(side=tk.RIGHT, padx=5)
        lbl_leg = tk.Label(header, text=legend, bg=self.colors["group_bg"], fg="#888", font=("", 9, "italic"))
        if legend: lbl_leg.pack(side=tk.RIGHT, padx=10)

        child_frame = tk.Frame(group_main, bg=self.colors["timeline_bg"])
        if expanded: child_frame.pack(fill=tk.X, padx=(25, 0))

        group_data = {
            "type": "group", "frame": group_main, "header_frame": header, "checkvar": var, 
            "label": lbl, "text": title, "menu_btn": menu_btn, "cb": cb, "legend_lbl": lbl_leg,
            "legend": legend, "ignore": ignore, "expanded": expanded,
            "exp_btn": btn_exp, "child_frame": child_frame, "children": [],
            "parent_list": dest_list 
        }
        dest_list.append(group_data)

        def toggle_expand(e=None):
            group_data["expanded"] = not group_data["expanded"]
            btn_exp.config(text="▼" if group_data["expanded"] else "▶")
            if group_data["expanded"]: child_frame.pack(fill=tk.X, padx=(25, 0))
            else: child_frame.pack_forget()
            self.save_history()
        btn_exp.bind("<Button-1>", toggle_expand)
        
        def show_menu(e):
            m = tk.Menu(self.root, tearoff=0, bg="#2d2d2d", fg="white")
            m.add_command(label="  Renomear", command=lambda: self.rename_group(group_data))
            m.add_command(label="  Legenda", command=lambda: self.edit_legend(group_data))
            ign_txt = "  Ativar Grupo" if group_data["ignore"] else "  Ignorar Grupo"
            m.add_command(label=ign_txt, command=lambda: self.toggle_ignore(group_data))
            m.add_separator()
            m.add_command(label="  Desagrupar (Manter Itens)", command=lambda: self.ungroup(group_data))
            m.add_command(label="  Excluir Tudo", command=lambda: self.delete_single_item(group_data))
            m.post(e.x_root, e.y_root)

        for w in [header, lbl, lbl_leg, icon_lbl]:
            w.bind("<Button-1>", lambda e: self.handle_selection(group_data, e))
            w.bind("<Button-3>", show_menu)
        menu_btn.bind("<Button-1>", show_menu)
        
        self.update_group_style(group_data)
        if save: self.save_history()
        return group_data

    def add_event(self, event_text, legend="", ignore=False, save=True, target_list=None, parent_ui=None):
        dest_list = target_list if target_list is not None else self.events
        parent_widget = parent_ui if parent_ui else self.scrollable_frame
        
        card = tk.Frame(parent_widget, bg=self.colors["card"], bd=0, pady=2)
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
        menu_btn = tk.Label(card, text="⋮", bg=self.colors["card"], fg="#aaaaaa", font=("", 14, "bold"), cursor="hand2", width=3)
        menu_btn.pack(side=tk.RIGHT, padx=5)
        lbl_leg = tk.Label(card, text=legend, bg=self.colors["card"], fg="#888", font=("", 9, "italic"))
        if legend: lbl_leg.pack(side=tk.RIGHT, padx=10)
        
        item_data = {
            "type": "action", "frame": card, "checkvar": var, "label": lbl, "text": event_text, 
            "menu_btn": menu_btn, "cb": cb, "legend_lbl": lbl_leg,
            "legend": legend, "ignore": ignore, "parent_list": dest_list
        }
        dest_list.append(item_data)
        self.update_item_style_full(item_data)
        
        def on_enter(e): 
            if not var.get(): self.update_item_color(item_data, self.colors["card_hover"])
        def on_leave(e):
            if not var.get(): self.update_item_color(item_data, self.colors["card"])
        
        def show_menu(e):
            m = tk.Menu(self.root, tearoff=0, bg="#2d2d2d", fg="white")
            m.add_command(label="  Editar", command=lambda: self.on_double_click_event(None, lbl))
            m.add_command(label="  Legenda", command=lambda: self.edit_legend(item_data))
            ign_txt = "  Ativar" if item_data["ignore"] else "  Ignorar"
            m.add_command(label=ign_txt, command=lambda: self.toggle_ignore(item_data))
            m.add_separator()
            if dest_list == self.events:
                 sel_count = sum(1 for x in self.events if x["checkvar"].get())
                 if sel_count > 0: m.add_command(label="  📁 Agrupar Seleção", command=self.group_selection)
            m.add_command(label="  Remover", command=lambda: self.delete_single_item(item_data))
            m.post(e.x_root, e.y_root)

        for w in [card, lbl, lbl_leg]:
            w.bind("<Button-1>", lambda e: self.handle_selection(item_data, e))
            w.bind("<Double-Button-1>", lambda e: self.on_double_click_event(e, lbl))
            w.bind("<Enter>", on_enter); w.bind("<Leave>", on_leave)
            w.bind("<Button-3>", show_menu)
        menu_btn.bind("<Button-1>", show_menu)
        
        if save: self.save_history()

    # --- ESTILOS ---
    def update_item_style_full(self, item):
        bg_c = self.colors["card_selected"] if item["checkvar"].get() else self.colors["card"]
        fnt = ("Segoe UI", 10, "overstrike") if item["ignore"] else ("Segoe UI", 10)
        fg_c = "#777777" if item["ignore"] else self.colors["text"]
        item["label"].config(font=fnt, fg=fg_c)
        self.update_item_color(item, bg_c)

    def update_item_color(self, item, color):
        item["frame"].config(bg=color); item["label"].config(bg=color); item["menu_btn"].config(bg=color)
        item["cb"].config(bg=color, activebackground=color); item["legend_lbl"].config(bg=color)

    def update_group_style(self, group):
        bg_c = "#3c3c3c" if group["checkvar"].get() else self.colors["group_bg"]
        fnt = ("Segoe UI", 10, "bold", "overstrike") if group["ignore"] else ("Segoe UI", 10, "bold")
        fg_c = "#777" if group["ignore"] else "white"
        group["header_frame"].config(bg=bg_c); group["label"].config(bg=bg_c, font=fnt, fg=fg_c)
        group["exp_btn"].config(bg=bg_c); group["menu_btn"].config(bg=bg_c); group["cb"].config(bg=bg_c, activebackground=bg_c)
        group["legend_lbl"].config(bg=bg_c)

    def refresh_timeline(self, save=True):
        if save: self.save_history()
        self.restore_snapshot(self.get_snapshot())

    def _clean_text(self, text):
        return text.replace("🖱️  ", "").replace("📝  ", "").replace("⌨️  ", "").replace("⏱️  ", "").replace("📋  ", "").replace("🔹  ", "")

    # --- SELEÇÃO ---
    def handle_selection(self, item_data, event):
        parent_list = item_data.get("parent_list", self.events)
        try: idx = parent_list.index(item_data)
        except: return 

        ctrl, shift = (event.state & 0x0004), (event.state & 0x0001)
        
        if shift and self.last_selected_index is not None:
             start, end = min(self.last_selected_index, idx), max(self.last_selected_index, idx)
             if not ctrl: self.deselect_all(None)
             for i in range(start, end + 1):
                 if i < len(parent_list):
                     parent_list[i]["checkvar"].set(True)
                     if parent_list[i]["type"]=="group": self.update_group_style(parent_list[i])
                     else: self.update_item_style_full(parent_list[i])
        elif ctrl:
            state = not item_data["checkvar"].get()
            item_data["checkvar"].set(state)
        else:
            if not item_data["checkvar"].get():
                self.deselect_all(None)
                item_data["checkvar"].set(True)
            self.last_selected_index = idx
            
        if item_data["type"]=="group": self.update_group_style(item_data)
        else: self.update_item_style_full(item_data)
        
        # Drag simplificado (reordena na lista atual)
        self.drag_data["item_index"] = idx
        self.drag_data["active"] = True
        self.drag_data["current_list"] = parent_list

    def deselect_all(self, event):
        self._deselect_recursive(self.events)
        self._update_style_recursive(self.events)

    def _deselect_recursive(self, lst):
        for it in lst:
            it["checkvar"].set(False)
            if it["type"] == "group": self._deselect_recursive(it["children"])

    def _update_style_recursive(self, lst):
        for it in lst:
            if it["type"] == "group":
                self.update_group_style(it)
                self._update_style_recursive(it["children"])
            else: self.update_item_style_full(it)

    # --- OPERAÇÕES DE GRUPO ---
    def group_selection(self):
        indices = [i for i, e in enumerate(self.events) if e["checkvar"].get()]
        if not indices: return
        items = []
        for i in sorted(indices, reverse=True): items.insert(0, self.events.pop(i))
        self.add_group("Novo Grupo", save=False) 
        group = self.events.pop()
        group["children"] = items
        self.events.insert(indices[0], group)
        self.refresh_timeline()

    def ungroup(self, group_item):
        try: idx = self.events.index(group_item)
        except: return 
        children = group_item["children"]
        self.events.pop(idx)
        for c in reversed(children): self.events.insert(idx, c)
        self.refresh_timeline()

    def rename_group(self, group):
        n = simpledialog.askstring("Renomear", "Nome:", initialvalue=group["text"], parent=self.root)
        if n: 
            group["text"] = n; group["label"].config(text=n); self.save_history()

    # --- UTILITÁRIOS ---
    def toggle_ignore(self, item):
        item["ignore"] = not item["ignore"]
        if item["type"] == "group": self.update_group_style(item)
        else: self.update_item_style_full(item)
        self.save_history()

    def edit_legend(self, item):
        def content(win):
            tk.Label(win, text="Legenda:", bg="#2b2b2b", fg="#ccc").pack(pady=5)
            e = tk.Entry(win, bg="#404040", fg="white"); e.pack(padx=10, fill=tk.X); e.insert(0, item["legend"]); e.focus(); win.user_data = e
        def confirm(win):
            t = win.user_data.get().strip(); item["legend"] = t
            item["legend_lbl"].config(text=t)
            if t: item["legend_lbl"].pack(side=tk.RIGHT, padx=10)
            else: item["legend_lbl"].pack_forget()
            self.save_history(); return True
        self._open_generic_dialog("Legenda", 120, content, confirm)

    def on_double_click_event(self, event, lbl_widget=None):
        lbl = lbl_widget if lbl_widget else event.widget
        text = self._clean_text(lbl.cget("text"))
        class Dummy: 
            def __init__(self): self.text=text; self.lbl=lbl
            def cget(self,x): return self.text
            def config(self, t): 
                ic="🔹"
                if "Clique" in t: ic="🖱️"
                elif "Digitar" in t: ic="📝"
                elif "Tecla" in t: ic="⌨️"
                elif "Esperar" in t: ic="⏱️"
                elif "Lista" in t: ic="📋"
                self.lbl.config(text=f"{ic}  {t}")
            @property
            def full_text(self): return getattr(self.lbl, "full_text", None)
            @full_text.setter
            def full_text(self,v): self.lbl.full_text=v
        d = Dummy()
        if any(x in text for x in ["Clique", "Duplo", "Botão", "Pressionar por", "repetido"]): self.edit_click_event(d)
        elif text.startswith("Digitar:"): self.edit_text_event(d)
        elif any(x in text for x in ["Pressionar", "Manter", "Tecla"]): self.edit_key_event(d)
        elif text.startswith("Esperar"): self.edit_wait_event(d)
        elif text.startswith("Lista:"): self.edit_list_event(d)

    def delete_single_item(self, item):
        parent = item["parent_list"]
        if item["type"] == "group":
             res = messagebox.askyesnocancel("Excluir Grupo", "Sim: Exclui Tudo\nNão: Desagrupa (Mantém itens)", parent=self.root)
             if res is None: return
             if res: parent.remove(item)
             else: self.ungroup(item)
        else:
            if messagebox.askyesno("Confirmar", "Remover item?", parent=self.root): parent.remove(item)
        self.refresh_timeline()

    def delete_selected_events(self, event=None):
        sel = [x for x in self.events if x["checkvar"].get()]
        if sel and messagebox.askyesno("Confirmar", f"Apagar {len(sel)} itens?"):
            for x in sel: self.events.remove(x)
            self.refresh_timeline()
    
    def move_selected_up(self): self._move_simple(-1)
    def move_selected_down(self): self._move_simple(1)
    def _move_simple(self, direction):
        lst = self.events
        sel = sorted([i for i, e in enumerate(lst) if e["checkvar"].get()], reverse=(direction>0))
        for i in sel:
            if 0 <= i + direction < len(lst) and not lst[i+direction]["checkvar"].get():
                lst[i], lst[i+direction] = lst[i+direction], lst[i]
        self.refresh_timeline()

    # --- ARQUIVO ---
    def export_timeline(self):
        f = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Txt","*.txt")])
        if f:
            with open(f, "w", encoding="utf-8") as file:
                file.write(f"# MACTIME_HEADER | v={self.FILE_VERSION}\n")
                self._write_recursive(file, self.events)
            messagebox.showinfo("Sucesso", "Salvo.")

    def _write_recursive(self, file, items, indent=0):
        sp = "  " * indent
        for it in items:
            if it["type"] == "group":
                ign = " | ignore=True" if it["ignore"] else ""
                leg = f" | legend={it['legend']}" if it["legend"] else ""
                exp = " | collapsed=True" if not it["expanded"] else ""
                file.write(f"{sp}GROUP_START: {it['text']}{ign}{leg}{exp}\n")
                self._write_recursive(file, it["children"], indent + 1)
                file.write(f"{sp}GROUP_END\n")
            else:
                t = self._clean_text(it["label"].cget("text"))
                ign = " | ignore=True" if it["ignore"] else ""
                leg = f" | legend={it['legend']}" if it["legend"] else ""
                if t.startswith("Digitar:") and hasattr(it["label"], "full_text"):
                    file.write(f"{sp}Digitar: <<START>>{ign}{leg}\n{it['label'].full_text}\n<<END>>\n")
                elif t.startswith("Lista:"):
                    p = t.split("Lista:")[1].strip()
                    l_ign = self.list_settings.get(p, False)
                    file.write(f"{sp}Lista: {p} | list_ignore={l_ign}{ign}{leg}\n")
                else:
                    file.write(f"{sp}{t}{ign}{leg}\n")

    def import_timeline(self):
        f = filedialog.askopenfilename(filetypes=[("Txt","*.txt")])
        if f:
            try:
                with open(f, "r", encoding="utf-8") as file: lines = file.readlines()
            except: 
                 with open(f, "r") as file: lines = file.readlines() 
            
            try:
                if len(lines)>0 and "# MACTIME" in lines[0]: lines.pop(0)
                self.events = []; stack = [self.events]; i = 0
                while i < len(lines):
                    l = lines[i].strip()
                    if not l or l.startswith("#"): i+=1; continue
                    if "GROUP_START:" in l:
                        meta = l.replace("GROUP_START: ", "")
                        name = meta.split(" | ")[0]
                        ign = "ignore=True" in meta
                        leg = meta.split("legend=")[1].split(" | ")[0] if "legend=" in meta else ""
                        exp = "collapsed=True" not in meta
                        grp = {"type":"group", "text":name, "ignore":ign, "legend":leg, "expanded":exp, "children":[], "chk":False}
                        stack[-1].append(grp); stack.append(grp["children"])
                    elif "GROUP_END" in l:
                        if len(stack) > 1: stack.pop()
                    elif "Digitar: <<START>>" in l:
                        i+=1; full=[]
                        while i<len(lines) and "<<" not in lines[i]: full.append(lines[i].rstrip()); i+=1
                        stack[-1].append({"type":"action", "text":f"Digitar: {full[0][:10]}...", "full":"\n".join(full), "ignore":False, "legend":"", "chk":False})
                    else:
                        ign = "ignore=True" in l
                        leg = l.split("legend=")[1].split(" | ")[0] if "legend=" in l else ""
                        txt = l.split(" | ")[0]
                        if "Lista:" in txt:
                            path = txt.replace("Lista: ", "").strip()
                            list_ign = "list_ignore=True" in l
                            self.list_settings[path] = list_ign
                            txt = f"Lista: {path}"
                        stack[-1].append({"type":"action", "text":txt, "ignore":ign, "legend":leg, "chk":False, "full":None})
                    i+=1
                self.refresh_timeline()
                messagebox.showinfo("Sucesso", "Importado.")
            except Exception as e: messagebox.showerror("Erro", str(e))

    # --- JANELAS ---
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
            if confirm_fn(win) is True: win.destroy()
        bf = tk.Frame(win, bg="#2b2b2b"); bf.pack(side=tk.BOTTOM, pady=20, fill=tk.X)
        tk.Button(bf, text="Salvar", command=on_ok, bg="#007acc", fg="white", bd=0, padx=20, pady=5).pack(side=tk.RIGHT, padx=20)
        tk.Button(bf, text="Cancelar", command=win.destroy, bg="#d32f2f", fg="white", bd=0, padx=10, pady=5).pack(side=tk.RIGHT)
        if bind_return: win.bind("<Return>", on_ok)
        win.focus_set()

    def _toggle_helper(self, parent, options, var, lbl_txt=None):
        if lbl_txt: tk.Label(parent, text=lbl_txt, bg="#2b2b2b", fg="white", font=("", 10, "bold")).pack(pady=(10, 5))
        fr = tk.Frame(parent, bg="#2b2b2b"); fr.pack()
        def upd():
            curr = var.get()
            for w in fr.winfo_children():
                w.config(bg=self.colors["btn_active"] if w.cget("text") in [x[0] for x in options if x[1]==curr] else self.colors["btn_inactive"])
        for txt, val in options:
            b = tk.Button(fr, text=txt, command=lambda v=val: (var.set(v), upd()), bg=self.colors["btn_inactive"], fg="white", relief=tk.FLAT, bd=0, width=10, pady=5)
            b.pack(side=tk.LEFT, padx=2)
        upd()

    def show_about(self):
        win = tk.Toplevel(self.root); win.title("Sobre"); self.center_window(win, 400, 250); win.attributes("-topmost", True)
        try: tk.Label(win, text="🖱️", font=("", 40), bg=self.colors["bg"], fg="white").pack()
        except: pass
        tk.Label(win, text=f"{self.APP_NAME} {self.APP_VERSION}", font=("", 14, "bold"), bg=self.colors["bg"], fg="white").pack()
        tk.Label(win, text=f"by {self.APP_AUTHOR}", bg=self.colors["bg"], fg="#888").pack()
        tk.Label(win, text=self.APP_DESC, bg="#333", fg="#ccc", padx=10, pady=10).pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

    # --- AÇÕES ESPECÍFICAS ---
    def _open_mouse_dialog(self, title, initial_mode="Simples", initial_param="", on_confirm=None):
        win = tk.Toplevel(self.root); win.title(title); self.center_window(win, 400, 450); win.attributes("-topmost", True)
        tk.Label(win, text="Posicione o mouse e aperte ENTER.", padx=20, pady=10, bg="#2b2b2b", fg="#A0A0A0").pack(fill=tk.X)
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
        
        coord = tk.Label(win, text="X: 0 Y: 0", font=("Consolas", 16), bg="#2b2b2b", fg="#0f0"); coord.pack(pady=10)
        self._capturing = True
        def loop():
            if not win.winfo_exists() or not self._capturing: return
            try:
                if ctypes.windll.user32.GetAsyncKeyState(0x0D) & 0x8000: confirm(); return
                x,y = pyautogui.position(); coord.config(text=f"X: {x} Y: {y}")
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
        tk.Button(win, text="Gravar (ENTER)", command=confirm, bg="#007acc", fg="white", bd=0, height=2).pack(fill=tk.X, side=tk.BOTTOM, padx=20, pady=20)

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
        if "Pressionar" in t: m="Pressionar"; p=t.split("Duração: ")[1].replace("s","")
        elif "repetido" in t: m="Repetido"; p=t.split("Repetir por: ")[1].replace("s","")
        elif "Duplo" in t: m="Duplo"
        elif "Direito" in t: m="Direito"
        elif "Scroll" in t: m="Scroll"
        def save(x, y, mo, pa):
            if mo=="Simples": txt = f"Clique Simples em ({x}, {y})"
            elif mo=="Duplo Clique": txt = f"Duplo Clique em ({x}, {y})"
            elif mo=="Botão Direito": txt = f"Botão Direito em ({x}, {y})"
            elif mo=="Scroll": txt = f"Scroll em ({x}, {y})"
            elif mo=="Pressionar": txt = f"Pressionar por tempo em ({x}, {y}) - Duração: {pa}s"
            else: txt = f"Clique repetido em ({x}, {y}) - Repetir por: {pa}s"
            label.config(text=txt); self.save_history()
        self._open_mouse_dialog("Editar Clique", m, p, save)

    def add_text_event(self):
        def content(win):
            t = tk.Text(win, height=8); t.pack(padx=10, pady=10, fill=tk.BOTH, expand=True); t.focus(); win.user_data = t
        def confirm(win):
            txt = win.user_data.get("1.0", tk.END).strip()
            if txt: 
                self.add_event(f"Digitar: {txt.splitlines()[0][:30]}...")
                self.events[-1]["label"].full_text = txt
            return True
        self._open_generic_dialog("Adicionar Texto", 300, content, confirm, bind_return=False)
    def edit_text_event(self, label):
        full = label.full_text if hasattr(label, "full_text") else label.cget("text").replace("Digitar:", "").strip()
        def content(win):
            t = tk.Text(win, height=8); t.pack(padx=10, pady=10, fill=tk.BOTH, expand=True); t.insert("1.0", full); t.focus(); win.user_data = t
        def confirm(win):
            txt = win.user_data.get("1.0", tk.END).strip()
            label.config(text=f"Digitar: {txt.splitlines()[0][:30]}...")
            label.full_text = txt; self.save_history()
            return True
        self._open_generic_dialog("Editar Texto", 300, content, confirm, bind_return=False)

    def _open_key_dialog(self, title, initial_mode="Simples", initial_keys=None, initial_duration="", on_confirm=None):
        keys = list(initial_keys) if initial_keys else []
        def content(win):
            tk.Label(win, text="Pressione as teclas.", bg="#2b2b2b", fg="#ccc").pack()
            mode = tk.StringVar(value=initial_mode)
            self._toggle_helper(win, [("Simples","Simples"), ("Manter","Manter"), ("Repetida","Repetida")], mode)
            row = tk.Frame(win, bg="#2b2b2b"); row.pack(pady=10)
            ent = tk.Entry(row, width=20, justify="center"); ent.pack(side=tk.LEFT); ent.insert(0, "+".join(keys))
            tk.Button(row, text="Limpar", command=lambda: (keys.clear(), ent.delete(0, tk.END))).pack(side=tk.LEFT)
            p_fr = tk.Frame(win, bg="#2b2b2b"); p_fr.pack()
            lbl_p = tk.Label(p_fr, text="Tempo:", bg="#2b2b2b", fg="white"); lbl_p.pack(side=tk.LEFT)
            p_ent = tk.Entry(p_fr, width=5); p_ent.pack(side=tk.LEFT); p_ent.insert(0, initial_duration)
            def upd(*a):
                if mode.get() == "Simples": p_fr.pack_forget()
                elif mode.get() == "Manter": p_fr.pack(); lbl_p.config(text="Duração (s):")
                else: p_fr.pack(); lbl_p.config(text="Qtd:")
            mode.trace("w", upd); upd()
            def on_k(e):
                if e.keysym not in keys: keys.append(e.keysym)
                ent.delete(0, tk.END); ent.insert(0, "+".join(keys)); return "break"
            ent.bind("<KeyPress>", on_k); ent.focus(); win.user_data = {"m": mode, "k": keys, "p": p_ent}
        def confirm(win):
            d = win.user_data
            if on_confirm: on_confirm(d["m"].get(), d["k"], d["p"].get().strip() or "1")
            return True
        self._open_generic_dialog(title, 300, content, confirm)
    def add_key_event(self):
        self._open_key_dialog("Adicionar Tecla", on_confirm=lambda m, k, d: self.add_event(f"Pressionar Tecla: {'+'.join(k)}" if m=="Simples" else f"Manter pressionada: {'+'.join(k)} - Duração: {d}s" if m=="Manter" else f"Tecla repetida: {'+'.join(k)} - Repetir: {d}x"))
    def edit_key_event(self, label):
        txt = label.cget("text"); m, k, d = "Simples", [], ""
        if " - Duração: " in txt: m="Manter"; k=txt.split(" - Duração: ")[0].replace("Manter pressionada: ", "").split("+"); d=txt.split(" - Duração: ")[1].replace("s","")
        elif " - Repetir: " in txt: m="Repetida"; k=txt.split(" - Repetir: ")[0].replace("Tecla repetida: ", "").split("+"); d=txt.split(" - Repetir: ")[1].replace("x","")
        elif "Pressionar Tecla: " in txt: k=txt.replace("Pressionar Tecla: ", "").split("+")
        def save(mode, keys, dur):
            label.config(text=f"Pressionar Tecla: {'+'.join(keys)}" if mode=="Simples" else f"Manter pressionada: {'+'.join(keys)} - Duração: {dur}s" if mode=="Manter" else f"Tecla repetida: {'+'.join(keys)} - Repetir: {dur}x"); self.save_history()
        self._open_key_dialog("Editar Tecla", m, k, d, save)

    def load_timeline(self):
        def content(win):
            fr = tk.Frame(win, bg="#2b2b2b"); fr.pack(fill=tk.X, pady=10)
            path = tk.StringVar()
            tk.Entry(fr, textvariable=path).pack(side=tk.LEFT, fill=tk.X, expand=True)
            tk.Button(fr, text="File", command=lambda: path.set(filedialog.askopenfilename())).pack(side=tk.RIGHT)
            ign = tk.BooleanVar()
            tk.Checkbutton(win, text="Ignorar linhas vazias", variable=ign).pack()
            win.user_data = {"p": path, "i": ign}
        def confirm(win):
            p = win.user_data["p"].get(); i = win.user_data["i"].get()
            try:
                with open(p, "r", encoding="utf-8") as f: l = f.read().splitlines()
                items = [x.strip() for x in l if (x.strip() if i else True)]
                fp = os.path.abspath(p)
                self.loaded_lists[fp] = items; self.loaded_index[fp] = 0; self.list_settings[fp] = i
                if not any(f"Lista: {fp}" in e["label"].cget("text") for e in self.events): self.add_event(f"Lista: {fp}")
                self.save_history()
                return f"Carregado {len(items)} itens."
            except Exception as e: messagebox.showerror("Erro", str(e), parent=self.root); return False
        self._open_generic_dialog("Lista", 200, content, confirm)
    def edit_list_event(self, label): self.load_timeline()

    def add_wait_event(self):
        def c(win): tk.Label(win, text="Segundos:").pack(); e = tk.Entry(win); e.pack(); win.user_data=e
        def ok(win): self.add_event(f"Esperar {win.user_data.get()} segundos"); return True
        self._open_generic_dialog("Espera", 150, c, ok)
    def edit_wait_event(self, l): 
        self._open_generic_dialog("Espera", 150, lambda w: (tk.Label(w,text="S:").pack(), e:=tk.Entry(w), e.pack(), e.insert(0, re.search(r"(\d+\.?\d*)", l.cget("text")).group(1)), setattr(w,"user_data",e)), lambda w: (l.config(text=f"Esperar {w.user_data.get()} segundos"), self.save_history(), True)[2])

    def add_clear_event(self): self.add_event("Apagar Campo")

    # --- EXECUÇÃO ---
    def execute_with_loops(self):
        win = tk.Toplevel(self.root); self.center_window(win, 300, 150)
        tk.Label(win, text="Repetições", bg="#2b2b2b", fg="#A0A0A0", font=("Segoe UI", 11)).pack(pady=(20, 5))
        e = tk.Entry(win, justify="center", font=("Segoe UI", 30, "bold"), bg="#2b2b2b", fg=self.colors["accent"], bd=0, width=5)
        e.pack(pady=5); e.insert(0, "1"); tk.Frame(win, bg=self.colors["accent"], height=2, width=100).pack()
        e.focus(); e.select_range(0, tk.END)
        res = {"n": None}
        def ok(ev=None): 
            if e.get().isdigit(): res["n"] = int(e.get()); win.destroy()
        win.bind("<Return>", ok); tk.Button(win, text="Go", command=ok).pack()
        self.root.wait_window(win)
        if res["n"]: self.prepare_and_start(res["n"])

    def prepare_and_start(self, loops):
        self.stop_requested, self.executing = False, True
        self.start_visual_countdown([], loops)

    def start_visual_countdown(self, f, loops):
        cw = tk.Toplevel(self.root); cw.overrideredirect(True); cw.attributes("-topmost", True); self.center_window(cw, 300, 150)
        num = tk.Label(cw, text="3", font=("", 48)); num.pack(expand=True)
        threading.Thread(target=self._monitor_shake, daemon=True).start()
        def tm(c):
            if self.stop_requested: cw.destroy(); return
            num.config(text=str(c))
            if c>0: cw.after(1000, tm, c-1)
            else: cw.destroy(); threading.Thread(target=self._worker, args=(loops,)).start()
        tm(3)

    def _monitor_shake(self):
        last = pyautogui.position(); score = 0; lx, ly = 0, 0
        while self.executing and not self.stop_requested:
            time.sleep(0.05); curr = pyautogui.position()
            dx, dy = curr.x - last.x, curr.y - last.y
            move = False
            if abs(dx) > 100:
                if (1 if dx>0 else -1) != lx and lx != 0: score+=1; move=True
                lx = 1 if dx>0 else -1
            if abs(dy) > 100:
                if (1 if dy>0 else -1) != ly and ly != 0: score+=1; move=True
                ly = 1 if dy>0 else -1
            if not move and score > 0: score = max(0, score - 0.1)
            last = curr
            if score >= 4: self.stop_execution(); break

    def stop_execution(self):
        if not self.stop_requested: self.stop_requested = True; self._show_message("Parado", "Parado pelo usuário.")

    def _show_message(self, t, m):
        if not self.message_shown: self.message_shown = True; self.root.after(0, lambda: messagebox.showinfo(t, m))

    def _worker(self, loops):
        self._load_required_lists(self.events)
        for i in range(loops):
            if self.stop_requested: break
            for k in self.loaded_index: self.loaded_index[k]=0
            self._exec_recursive(self.events)
            if i < loops-1: time.sleep(0.5)
        self.executing = False
        if not self.stop_requested: self._show_message("Fim", "Concluído.")

    def _load_required_lists(self, items):
        for it in items:
            if it["type"]=="group": self._load_required_lists(it["children"])
            elif "Lista:" in it["text"]:
                p = it["text"].split("Lista:")[1].strip()
                if os.path.exists(p) and p not in self.loaded_lists:
                    with open(p,"r", encoding="utf-8") as f: self.loaded_lists[p] = [x.strip() for x in f.read().splitlines()]
                    self.loaded_index[p]=0

    def _exec_recursive(self, items):
        for it in items:
            if self.stop_requested: return
            if it["ignore"]: continue
            if it["type"] == "group": self._exec_recursive(it["children"])
            else: self._execute_event_action(it)

    def _execute_event_action(self, item):
        txt = self._clean_text(item["label"].cget("text") if item.get("label") else item["text"])
        if " em (" in txt:
            m = re.search(r"\((\d+),\s*(\d+)\)", txt); x, y = int(m.group(1)), int(m.group(2))
            if "Pressionar" in txt:
                d = float(re.search(r"Duração: (\d+\.?\d*)", txt).group(1))
                pyautogui.mouseDown(x,y); time.sleep(d); pyautogui.mouseUp(x,y)
            elif "repetido" in txt:
                d = float(re.search(r"Repetir por: (\d+\.?\d*)", txt).group(1)); e = time.time()+d
                while time.time()<e and not self.stop_requested: pyautogui.click(x,y); time.sleep(0.1)
            else: pyautogui.click(x, y)
        elif "Digitar:" in txt:
            t = item["label"].full_text if hasattr(item["label"], "full_text") else txt.replace("Digitar:", "").strip()
            self.root.clipboard_clear(); self.root.clipboard_append(t); self.root.update(); pyautogui.hotkey("ctrl", "v")
        elif "Tecla" in txt:
            if "Manter" in txt:
                p = txt.split(" - "); k = [normalize_key(x) for x in p[0].replace("Manter pressionada: ", "").split("+")]
                d = float(p[1].replace("Duração: ", "").replace("s","")); e = time.time()+d
                while time.time()<e and not self.stop_requested: pyautogui.hotkey(*k); time.sleep(0.05)
            elif "repetida" in txt:
                p = txt.split(" - "); k = [normalize_key(x) for x in p[0].replace("Tecla repetida: ", "").split("+")]
                c = int(p[1].replace("Repetir: ", "").replace("x","")); 
                for _ in range(c): 
                     if self.stop_requested: break
                     pyautogui.hotkey(*k); time.sleep(0.05)
            else:
                k = [normalize_key(x) for x in txt.replace("Pressionar Tecla: ", "").split("+")]
                pyautogui.hotkey(*k)
        elif "Esperar" in txt:
            time.sleep(float(re.search(r"(\d+\.?\d*)", txt).group(1)))
        elif "Apagar" in txt: pyautogui.hotkey("ctrl", "a"); pyautogui.press("backspace")
        elif "Lista:" in txt:
            p = txt.split("Lista:")[1].strip()
            if p in self.loaded_lists and self.loaded_index[p] < len(self.loaded_lists[p]):
                 self.root.clipboard_clear(); self.root.clipboard_append(self.loaded_lists[p][self.loaded_index[p]]); self.root.update()
                 pyautogui.hotkey("ctrl", "v"); self.loaded_index[p]+=1
        time.sleep(0.2)

if __name__ == "__main__":
    root = tk.Tk(); root.withdraw()
    app = MacroApp(root)
    root.bind("<Delete>", lambda e: app.delete_selected_events())
    
    splash = tk.Toplevel(root); splash.overrideredirect(True); splash.configure(bg="#2b2b2b")
    w, h = 350, 260; sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    splash.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
    try: img = tk.PhotoImage(file=resource_path("logo.png")); lbl_icon = tk.Label(splash, image=img, bg="#2b2b2b"); lbl_icon.image = img; lbl_icon.pack(pady=(15,0))
    except:
        try: tk.Label(splash, text="🖱️", font=("", 60), bg="#2b2b2b", fg="white").pack(pady=(15,0))
        except: pass
    tk.Label(splash, text=app.APP_NAME, font=("", 18, "bold"), bg="#2b2b2b", fg="white").pack()
    tk.Label(splash, text=app.APP_VERSION, font=("", 10), bg="#2b2b2b", fg="#aaa").pack()
    tk.Label(splash, text=f"Created by: {app.APP_AUTHOR}", font=("", 9), bg="#2b2b2b", fg="#808080").pack(pady=(5, 0))
    tk.Label(splash, text="Carregando...", font=("", 8, "italic"), bg="#2b2b2b", fg="#666").pack(side=tk.BOTTOM, pady=10)
    splash.update(); root.after(2000, lambda: (splash.destroy(), root.deiconify())); root.mainloop()