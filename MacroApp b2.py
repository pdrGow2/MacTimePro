import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
import pyautogui
import keyboard
import time

class TimelineAutomation:
    def __init__(self, root):
        self.root = root
        self.root.title("Automação por Timeline")
        
        self.actions = []  # Lista para armazenar ações
        self.running = False  # Controle de execução
        
        self.frame_controls = tk.Frame(root)
        self.frame_controls.pack(pady=10)
        
        self.btn_add_click = tk.Button(self.frame_controls, text="Capturar Clique", command=self.start_capture_click)
        self.btn_add_click.pack(side=tk.LEFT, padx=5)
        
        self.btn_add_text = tk.Button(self.frame_controls, text="Adicionar Texto", command=self.add_text)
        self.btn_add_text.pack(side=tk.LEFT, padx=5)
        
        self.btn_add_wait = tk.Button(self.frame_controls, text="Adicionar Espera", command=self.add_wait)
        self.btn_add_wait.pack(side=tk.LEFT, padx=5)
        
        self.btn_add_clear = tk.Button(self.frame_controls, text="Apagar Campo", command=self.add_clear)
        self.btn_add_clear.pack(side=tk.LEFT, padx=5)
        
        self.btn_load_txt = tk.Button(self.frame_controls, text="Carregar Lista TXT", command=self.load_txt)
        self.btn_load_txt.pack(side=tk.LEFT, padx=5)
        
        self.btn_execute = tk.Button(self.frame_controls, text="Executar", command=self.execute_actions, bg="green", fg="white")
        self.btn_execute.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = tk.Button(self.frame_controls, text="Parar", command=self.stop_execution, bg="red", fg="white")
        self.btn_stop.pack(side=tk.LEFT, padx=5)
        
        self.timeline = tk.Listbox(root, width=80, height=15)
        self.timeline.pack(pady=10)
        self.timeline.bind("<Delete>", self.remove_selected)
        self.timeline.bind("<ButtonPress-1>", self.start_drag)
        self.timeline.bind("<B1-Motion>", self.drag)
        self.timeline.bind("<ButtonRelease-1>", self.drop)
        
        self.drag_data = {"index": None, "text": None}
    
    def start_capture_click(self):
        messagebox.showinfo("Capturar Posição", "Clique no local desejado para capturar a posição.")
        self.root.after(100, self.capture_click)
    
    def capture_click(self):
        x, y = pyautogui.position()
        self.actions.append(("click", x, y))
        self.timeline.insert(tk.END, f"Clique em ({x}, {y})")
    
    def add_text(self):
        text = simpledialog.askstring("Adicionar Texto", "Digite o texto a ser inserido:")
        if text:
            self.actions.append(("text", text))
            self.timeline.insert(tk.END, f"Digitar: {text}")
    
    def add_wait(self):
        wait_time = simpledialog.askfloat("Adicionar Espera", "Tempo de espera (segundos):", minvalue=0.1)
        if wait_time:
            self.actions.append(("wait", wait_time))
            self.timeline.insert(tk.END, f"Esperar {wait_time} segundos")
    
    def add_clear(self):
        self.actions.append(("clear",))
        self.timeline.insert(tk.END, "Apagar Campo")
    
    def load_txt(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
        if file_path:
            with open(file_path, "r") as file:
                lines = [line.strip() for line in file.readlines() if line.strip()]
                for line in lines:
                    self.actions.append(("text", line))
                    self.timeline.insert(tk.END, f"Digitar: {line}")
            messagebox.showinfo("Carregado", f"{len(lines)} itens adicionados à timeline.")
    
    def remove_selected(self, event=None):
        selected = self.timeline.curselection()
        if selected:
            index = selected[0]
            self.timeline.delete(index)
            del self.actions[index]
    
    def start_drag(self, event):
        index = self.timeline.nearest(event.y)
        self.drag_data["index"] = index
        self.drag_data["text"] = self.timeline.get(index)
    
    def drag(self, event):
        index = self.timeline.nearest(event.y)
        if index != self.drag_data["index"]:
            self.timeline.delete(self.drag_data["index"])
            self.timeline.insert(index, self.drag_data["text"])
            self.drag_data["index"] = index
    
    def drop(self, event):
        index = self.timeline.nearest(event.y)
        if index != self.drag_data["index"]:
            action = self.actions.pop(self.drag_data["index"])
            self.actions.insert(index, action)
        self.drag_data = {"index": None, "text": None}
    
    def execute_actions(self):
        self.running = True
        repeat_count = sum(1 for action in self.actions if action[0] == "text")
        
        for _ in range(repeat_count):
            for action in self.actions:
                if not self.running:
                    break
                
                if keyboard.is_pressed("esc"):
                    self.running = False
                    break
                
                if action[0] == "click":
                    pyautogui.click(action[1], action[2])
                elif action[0] == "text":
                    pyautogui.write(action[1], interval=0.1)
                elif action[0] == "wait":
                    time.sleep(action[1])
                elif action[0] == "clear":
                    pyautogui.hotkey("ctrl", "a")
                    pyautogui.press("backspace")
                
                time.sleep(0.5)
        messagebox.showinfo("Fim", "Execução concluída!")
        
    def stop_execution(self):
        self.running = False
        messagebox.showwarning("Parado", "Execução interrompida.")
        
if __name__ == "__main__":
    root = tk.Tk()
    app = TimelineAutomation(root)
    root.mainloop()
