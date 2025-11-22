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
        
        # Lista de eventos
        self.events = []
        
    def add_event(self, event_type):
        event_label = tk.Label(self.scrollable_frame, text=event_type, bg="lightgray", padx=10, pady=5, relief=tk.RIDGE)
        event_label.pack(fill=tk.X, pady=2, expand=True)
        self.events.append(event_label)
    
    def _on_mouse_wheel(self, event):
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")
    
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
    root.mainloop()
