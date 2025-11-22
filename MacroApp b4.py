import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
import pyautogui
import keyboard
import time
import json

class TimelineAutomation:
    def __init__(self, root):
        self.root = root
        self.root.title("Automação por Timeline")
        
        self.actions = []  
        self.running = False  
        self.text_lines = []  
        
        self.frame_controls = tk.Frame(root)
        self.frame_controls.pack(pady=10)
        
        self.btn_add_click = tk.Button(self.frame_controls, text="Capturar Clique", command=self.start_capture_click)
        self.btn_add_click.pack(side=tk.LEFT, padx=5)
        
        self.btn_add_text = tk.Button(self.frame_controls, text="Adicionar Texto", command=self.add_text)
        self.btn_add_text.pack(side=tk.LEFT, padx=5)
        
        self.btn_add_key = tk.Button(self.frame_controls, text="Adicionar Tecla", command=self.add_key)
        self.btn_add_key.pack(side=tk.LEFT, padx=5)
        
        self.btn_add_wait = tk.Button(self.frame_controls, text="Adicionar Espera", command=self.add_wait)
        self.btn_add_wait.pack(side=tk.LEFT, padx=5)
        
        self.btn_add_clear = tk.Button(self.frame_controls, text="Apagar Campo", command=self.add_clear)
        self.btn_add_clear.pack(side=tk.LEFT, padx=5)
        
        self.btn_load_txt = tk.Button(self.frame_controls, text="Carregar Lista TXT", command=self.load_txt)
        self.btn_load_txt.pack(side=tk.LEFT, padx=5)
        
        self.btn_import = tk.Button(self.frame_controls, text="Importar Timeline", command=self.import_timeline, bg="blue", fg="white")
        self.btn_import.pack(side=tk.LEFT, padx=5)
        
        self.btn_export = tk.Button(self.frame_controls, text="Exportar Timeline", command=self.export_timeline, bg="purple", fg="white")
        self.btn_export.pack(side=tk.LEFT, padx=5)
        
        self.btn_execute = tk.Button(self.frame_controls, text="Executar", command=self.execute_actions, bg="green", fg="white")
        self.btn_execute.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = tk.Button(self.frame_controls, text="Parar", command=self.stop_execution, bg="red", fg="white")
        self.btn_stop.pack(side=tk.LEFT, padx=5)
        
        self.timeline = tk.Listbox(root, width=80, height=15)
        self.timeline.pack(pady=10)
        self.timeline.bind("<Delete>", self.remove_selected)
        
        self.selected_file = None  

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

    def add_key(self):
        key = simpledialog.askstring("Adicionar Tecla", "Digite a tecla a ser pressionada:")
        if key:
            self.actions.append(("key", key))
            self.timeline.insert(tk.END, f"Pressionar Tecla: {key}")
    
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
                self.text_lines = [line.strip() for line in file.readlines() if line.strip()]
            
            if self.text_lines:
                self.selected_file = file_path.split("/")[-1]
                self.actions.append(("file", self.text_lines))
                self.timeline.insert(tk.END, f"Arquivo TXT: {self.selected_file}")
                messagebox.showinfo("Carregado", f"Arquivo '{self.selected_file}' carregado com {len(self.text_lines)} linhas.")
    
    def remove_selected(self, event=None):
        selected = self.timeline.curselection()
        if selected:
            index = selected[0]
            self.timeline.delete(index)
            del self.actions[index]
    
    def execute_actions(self):
        self.running = True
        
        while self.running:
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
                elif action[0] == "key":
                    pyautogui.press(action[1])
                elif action[0] == "wait":
                    time.sleep(action[1])
                elif action[0] == "clear":
                    pyautogui.hotkey("ctrl", "a")
                    pyautogui.press("backspace")
                elif action[0] == "file":
                    for line in action[1]:
                        pyautogui.write(line, interval=0.1)
                        time.sleep(0.5)

        messagebox.showinfo("Fim", "Execução concluída!")

    def stop_execution(self):
        self.running = False
        messagebox.showwarning("Parado", "Execução interrompida.")

    def export_timeline(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, "w") as file:
                json.dump(self.actions, file)
            messagebox.showinfo("Exportado", "Timeline salva com sucesso!")

    def import_timeline(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if file_path:
            with open(file_path, "r") as file:
                self.actions = json.load(file)
            
            self.timeline.delete(0, tk.END)
            for action in self.actions:
                if action[0] == "click":
                    self.timeline.insert(tk.END, f"Clique em ({action[1]}, {action[2]})")
                elif action[0] == "text":
                    self.timeline.insert(tk.END, f"Digitar: {action[1]}")
                elif action[0] == "key":
                    self.timeline.insert(tk.END, f"Pressionar Tecla: {action[1]}")
                elif action[0] == "wait":
                    self.timeline.insert(tk.END, f"Esperar {action[1]} segundos")
                elif action[0] == "clear":
                    self.timeline.insert(tk.END, "Apagar Campo")
                elif action[0] == "file":
                    self.timeline.insert(tk.END, "Arquivo TXT importado")

            messagebox.showinfo("Importado", "Timeline carregada com sucesso!")

if __name__ == "__main__":
    root = tk.Tk()
    app = TimelineAutomation(root)
    root.mainloop()
