import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import time
import re
import pyautogui

class MacroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Automação por Timeline")
        self.root.geometry("900x400")
        
        # Variáveis de controle da execução
        self.executing = False
        self.stop_requested = False
        self.interrupt_reason = None  # Armazena a razão da interrupção

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
        
        # Frame com scrollbar vertical
        timeline_container = tk.Frame(root)
        timeline_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.canvas = tk.Canvas(timeline_container, bg="white")
        self.scrollbar = tk.Scrollbar(timeline_container, orient=tk.VERTICAL, command=self.canvas.yview)
        
        self.scrollable_frame = tk.Frame(self.canvas, bg="white", width=900)
        self.scrollable_frame.bind(
            "<Configure>", lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw", width=900)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind do scroll do mouse
        self.canvas.bind_all("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-1>", self.deselect_event)
        
        # Lista de eventos
        self.events = []
        self.selected_event = None

    # --- Funções de manipulação dos eventos da timeline ---
    def add_event(self, event_text):
        event_label = tk.Label(self.scrollable_frame, text=event_text, bg="lightgray", padx=10, pady=5, relief=tk.RIDGE)
        event_label.pack(fill=tk.X, pady=2, expand=True)
        event_label.bind("<Button-1>", self.select_event)
        event_label.bind("<B1-Motion>", self.drag_event)
        event_label.bind("<Enter>", lambda e: event_label.config(bg="gray"))
        event_label.bind("<Leave>", lambda e: event_label.config(bg="lightgray" if event_label != self.selected_event else "darkgray"))
        self.events.append(event_label)
    
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
    
    # --- Funções para capturar eventos individuais ---
    def capture_mouse_click(self):
        capture_window = tk.Toplevel(self.root)
        capture_window.title("Capturar Clique")
        capture_window.geometry("400x120")
        capture_window.attributes("-topmost", True)
        
        label = tk.Label(capture_window, text="Mova o mouse até a posição desejada e aperte ENTER", padx=20, pady=10)
        label.pack(expand=True, fill=tk.BOTH)
        
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
            self.add_event(f"Clique em ({x}, {y})")
        
        capture_window.bind("<Return>", on_enter)
        capture_window.focus_set()
    
    def add_text_event(self):
        text_window = tk.Toplevel(self.root)
        text_window.title("Adicionar Texto")
        text_window.geometry("400x150")
        text_window.attributes("-topmost", True)
        
        label = tk.Label(text_window, text="Digite o texto desejado e aperte ENTER ou clique em OK", padx=20, pady=10)
        label.pack(expand=True, fill=tk.BOTH)
        
        text_entry = tk.Entry(text_window, width=40)
        text_entry.pack(pady=5)
        text_entry.focus_set()
        
        def process_text(event=None):
            texto = text_entry.get()
            if texto.strip():
                self.add_event(f"Digitar: {texto}")
            text_window.destroy()
        
        text_entry.bind("<Return>", process_text)
        ok_button = tk.Button(text_window, text="OK", command=process_text)
        ok_button.pack(pady=5)
    
    def add_key_event(self):
        key_window = tk.Toplevel(self.root)
        key_window.title("Adicionar Tecla")
        key_window.geometry("400x150")
        key_window.attributes("-topmost", True)
        
        instruction_label = tk.Label(key_window, text="Pressione uma tecla", padx=20, pady=10)
        instruction_label.pack(expand=True, fill=tk.BOTH)
        
        pressed_key = {"key": None}
        
        def on_key_press(event):
            pressed_key["key"] = event.keysym
            instruction_label.config(text=f"Tecla pressionada: {event.keysym}\nClique em OK para confirmar")
        
        key_window.bind("<Key>", on_key_press)
        ok_button = tk.Button(key_window, text="OK", command=lambda: confirm_key())
        ok_button.pack(pady=5)
        
        def confirm_key():
            if pressed_key["key"]:
                self.add_event(f"Pressionar Tecla: {pressed_key['key']}")
            key_window.destroy()
    
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
        
        def process_time(event=None):
            tempo = time_entry.get()
            if tempo.strip():
                self.add_event(f"Esperar {tempo} segundos")
            wait_window.destroy()
        
        time_entry.bind("<Return>", process_time)
        ok_button = tk.Button(wait_window, text="OK", command=process_time)
        ok_button.pack(pady=5)
    
    def add_clear_event(self):
        # Por enquanto, apenas adiciona o evento "Apagar Campo" à timeline.
        self.add_event("Apagar Campo")
    
    def load_timeline(self):
        messagebox.showinfo("Carregar", "Carregar timeline de um arquivo TXT.")
    
    def import_timeline(self):
        messagebox.showinfo("Importar", "Importar timeline.")
    
    def export_timeline(self):
        messagebox.showinfo("Exportar", "Exportar timeline para arquivo.")
    
    # --- Execução da macro com interrupção ---
    def execute_timeline(self):
        if self.executing:
            messagebox.showwarning("Atenção", "Macro já está em execução!")
            return

        self.stop_requested = False
        self.interrupt_reason = None
        self.executing = True

        # Inicia a execução em uma thread separada
        exec_thread = threading.Thread(target=self._run_macro)
        exec_thread.start()
        
        # Inicia uma thread para monitorar sacudidas do mouse
        shake_thread = threading.Thread(target=self._monitor_mouse_shake)
        shake_thread.daemon = True
        shake_thread.start()
    
    def _run_macro(self):
        for event_label in self.events:
            if self.stop_requested:
                break

            text = event_label.cget("text")
            if text.startswith("Clique em"):
                match = re.search(r"\((\d+),\s*(\d+)\)", text)
                if match:
                    x = int(match.group(1))
                    y = int(match.group(2))
                    pyautogui.click(x, y)
            elif text.startswith("Digitar:"):
                typed_text = text[len("Digitar:"):].strip()
                pyautogui.write(typed_text)
            elif text.startswith("Pressionar Tecla:"):
                key = text[len("Pressionar Tecla:"):].strip()
                pyautogui.press(key)
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
        
        self.executing = False
        # Se a macro não foi interrompida, exibe mensagem de finalização.
        if not self.stop_requested:
            self._show_message("Finalizado", "A macro foi executada com sucesso.")
    
    def _monitor_mouse_shake(self):
        last_x = pyautogui.position().x
        shake_count = 0
        while self.executing and not self.stop_requested:
            time.sleep(0.1)
            current_x = pyautogui.position().x
            diff = current_x - last_x
            if abs(diff) > 100:  # limiar para movimento brusco
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
        self.root.after(0, lambda: messagebox.showinfo(title, message))

if __name__ == "__main__":
    root = tk.Tk()
    app = MacroApp(root)
    root.bind("<Delete>", app.delete_selected_event)
    root.mainloop()
