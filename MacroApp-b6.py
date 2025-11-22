import tkinter as tk
from tkinter import filedialog, messagebox

class MacroApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Automação por Timeline")
        self.root.geometry("900x400")
        
        # Frame dos botões
        button_frame = tk.Frame(root)
        button_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(button_frame, text="Capturar Clique", command=self.add_mouse_event).pack(side=tk.LEFT, padx=2, fill=tk.X, expand=True)
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
        
    def add_event(self, event_type):
        event_label = tk.Label(self.scrollable_frame, text=event_type, bg="lightgray", padx=10, pady=5, relief=tk.RIDGE)
        event_label.pack(fill=tk.X, pady=2, expand=True)
        event_label.bind("<Button-1>", self.select_event)
        event_label.bind("<B1-Motion>", self.drag_event)
        event_label.bind("<Enter>", lambda e: event_label.config(bg="gray"))
        event_label.bind("<Leave>", lambda e: event_label.config(bg="lightgray" if event_label != self.selected_event else "darkgray"))
        self.events.append(event_label)
    
    def select_event(self, event):
        if self.selected_event:
            self.selected_event.config(bg="lightgray")  # Resetar cor do anterior
        self.selected_event = event.widget
        self.selected_event.config(bg="darkgray")  # Mudar cor para indicar seleção
    
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
    
    def add_mouse_event(self):
        self.add_event("Clique em (X, Y)")
    
    def add_text_event(self):
        self.add_event("Digitar: Texto")
    
    def add_key_event(self):
        self.add_event("Pressionar Tecla: X")
    
    def add_wait_event(self):
        self.add_event("Esperar X segundos")
    
    def add_clear_event(self):
        self.add_event("Apagar Campo")
    
    def load_timeline(self):
        messagebox.showinfo("Carregar", "Carregar timeline de um arquivo TXT.")
    
    def import_timeline(self):
        messagebox.showinfo("Importar", "Importar timeline.")
    
    def export_timeline(self):
        messagebox.showinfo("Exportar", "Exportar timeline para arquivo.")
    
    def execute_timeline(self):
        messagebox.showinfo("Executar", "Executando ações da timeline.")
    
    def stop_execution(self):
        messagebox.showinfo("Parar", "Parando execução.")

if __name__ == "__main__":
    root = tk.Tk()
    app = MacroApp(root)
    root.bind("<Delete>", app.delete_selected_event)
    root.mainloop()
