def edit_click_event(self, item):
    """
    Abre uma janela para editar um evento de clique.
    O evento pode ser:
      - "Simples": exibe apenas "Clique Simples em (x, y)"
      - "Pressionar": exibe "Pressionar por tempo em (x, y) - Duração: Xs"
      - "Repetido": exibe "Clique repetido em (x, y) - Repetir por: Xs"
    """
    current = item["label"].cget("text")
    # Detecta a opção e parâmetro (se existir)
    if " - Duração:" in current:
        option = "Pressionar"
        try:
            coords_part, param_part = current.split(" - Duração:")
            coords = coords_part.split(" em ", 1)[1].strip()  # parte depois do " em "
            param = param_part.strip().rstrip("s")
        except Exception:
            option = "Pressionar"
            coords = "(0, 0)"
            param = "1.0"
    elif " - Repetir por:" in current:
        option = "Repetido"
        try:
            coords_part, param_part = current.split(" - Repetir por:")
            coords = coords_part.split(" em ", 1)[1].strip()
            param = param_part.strip().rstrip("s")
        except Exception:
            option = "Repetido"
            coords = "(0, 0)"
            param = "1.0"
    else:
        option = "Simples"
        if " em " in current:
            coords = current.split(" em ", 1)[1].strip()
        else:
            coords = "(0, 0)"
        param = ""
    
    win = tk.Toplevel(self.root)
    win.title("Editar Clique")
    self.center_window(win, 400, 250)
    win.attributes("-topmost", True)
    win.configure(bg="#282828")
    
    lbl = tk.Label(win, text="Mova o mouse e aperte ENTER", padx=20, pady=10, bg="#282828", fg="white")
    lbl.pack(fill=tk.X)
    
    option_frame = tk.Frame(win, bg="#282828")
    option_frame.pack(fill=tk.X, padx=20, pady=5)
    click_option = tk.StringVar(value=option)
    tk.Radiobutton(option_frame, text="Simples", variable=click_option, value="Simples",
                   bg="#282828", fg="white", selectcolor="#444444").pack(side=tk.LEFT, padx=5)
    tk.Radiobutton(option_frame, text="Pressionar", variable=click_option, value="Pressionar",
                   bg="#282828", fg="white", selectcolor="#444444").pack(side=tk.LEFT, padx=5)
    tk.Radiobutton(option_frame, text="Repetido", variable=click_option, value="Repetido",
                   bg="#282828", fg="white", selectcolor="#444444").pack(side=tk.LEFT, padx=5)
    
    param_frame = tk.Frame(win, bg="#282828")
    param_label = tk.Label(param_frame, text="", bg="#282828", fg="white")
    param_label.pack(side=tk.LEFT)
    param_entry = tk.Entry(param_frame)
    param_entry.pack(side=tk.LEFT, padx=5)
    # Se já houver parâmetro, insere
    if param:
        param_entry.insert(0, param)
    else:
        param_entry.insert(0, "1.0")
    param_frame.pack_forget()
    
    def update_param_visibility(*args):
        opt_val = click_option.get()
        if opt_val == "Simples":
            param_frame.pack_forget()
        elif opt_val == "Pressionar":
            param_label.config(text="Duração (s):")
            param_frame.pack(fill=tk.X, padx=20, pady=5)
        elif opt_val == "Repetido":
            param_label.config(text="Repetir por (s):")
            param_frame.pack(fill=tk.X, padx=20, pady=5)
    click_option.trace("w", update_param_visibility)
    update_param_visibility()
    
    def update_position():
        x = self.root.winfo_pointerx()
        y = self.root.winfo_pointery()
        lbl.config(text=f"Mova o mouse e aperte ENTER\nPosição atual: ({x}, {y})")
        win.after(50, update_position)
    update_position()
    
    def on_enter(e):
        x = self.root.winfo_pointerx()
        y = self.root.winfo_pointery()
        opt_val = click_option.get()
        param_val = param_entry.get().strip() or "1.0"
        win.destroy()
        if opt_val == "Simples":
            new_text = f"Clique Simples em ({x}, {y})"
        elif opt_val == "Pressionar":
            new_text = f"Pressionar por tempo em ({x}, {y}) - Duração: {param_val}s"
        elif opt_val == "Repetido":
            new_text = f"Clique repetido em ({x}, {y}) - Repetir por: {param_val}s"
        item["text"] = new_text
        item["label"].config(text=new_text)
    win.bind("<Return>", on_enter)
    win.focus_set()


def edit_key_event(self, event_label):
    current_text = event_label.cget("text")
    # Supondo os seguintes formatos:
    # "Pressionar Tecla: A+B" (simples)
    # "Manter pressionada: A+B - Duração: 1.0s" (manter)
    # "Tecla repetida: A+B - Repetir por: 2.5s" (repetido)
    if " - Duração:" in current_text:
        option = "Manter"
        try:
            parts = current_text.split(" - Duração:")
            keys_part = parts[0]
            keys = keys_part.replace("Manter pressionada:", "").strip().split("+")
            param = parts[1].strip().rstrip("s")
        except Exception:
            option = "Manter"
            keys = []
            param = "1.0"
    elif " - Repetir por:" in current_text:
        option = "Repetido"
        try:
            parts = current_text.split(" - Repetir por:")
            keys_part = parts[0]
            keys = keys_part.replace("Tecla repetida:", "").strip().split("+")
            param = parts[1].strip().rstrip("s")
        except Exception:
            option = "Repetido"
            keys = []
            param = "1.0"
    else:
        option = "Simples"
        prefix = "Pressionar Tecla:"
        if current_text.startswith(prefix):
            keys = current_text[len(prefix):].strip().split("+")
        else:
            keys = []
        param = ""
    
    win = tk.Toplevel(self.root)
    win.title("Editar Tecla")
    self.center_window(win, 400, 250)
    win.attributes("-topmost", True)
    win.configure(bg="#282828")
    
    instr_label = tk.Label(win, text="Pressione a(s) tecla(s) desejada(s) e aperte ENTER para confirmar",
                            padx=20, pady=10, bg="#282828", fg="white")
    instr_label.pack(fill=tk.X)
    
    option_frame = tk.Frame(win, bg="#282828")
    option_frame.pack(fill=tk.X, padx=20, pady=5)
    key_option = tk.StringVar(value=option)
    tk.Radiobutton(option_frame, text="Simples", variable=key_option, value="Simples",
                   bg="#282828", fg="white", selectcolor="#444444").pack(side=tk.LEFT, padx=5)
    tk.Radiobutton(option_frame, text="Manter", variable=key_option, value="Manter",
                   bg="#282828", fg="white", selectcolor="#444444").pack(side=tk.LEFT, padx=5)
    tk.Radiobutton(option_frame, text="Repetida", variable=key_option, value="Repetido",
                   bg="#282828", fg="white", selectcolor="#444444").pack(side=tk.LEFT, padx=5)
    
    param_frame = tk.Frame(win, bg="#282828")
    param_label = tk.Label(param_frame, text="", bg="#282828", fg="white")
    param_label.pack(side=tk.LEFT)
    param_entry = tk.Entry(param_frame)
    param_entry.pack(side=tk.LEFT, padx=5)
    if param:
        param_entry.insert(0, param)
    else:
        param_entry.insert(0, "1.0")
    param_frame.pack_forget()
    
    def update_key_param(*args):
        opt_val = key_option.get()
        if opt_val == "Simples":
            param_frame.pack_forget()
        elif opt_val == "Manter":
            param_label.config(text="Duração (s):")
            param_frame.pack(fill=tk.X, padx=20, pady=5)
        elif opt_val == "Repetido":
            param_label.config(text="Repetir por (s):")
            param_frame.pack(fill=tk.X, padx=20, pady=5)
    key_option.trace("w", update_key_param)
    update_key_param()
    
    combo_label = tk.Label(win, text="Combinação: " + "+".join(keys), padx=20, pady=5, bg="#282828", fg="white")
    combo_label.pack()
    key_combination = keys[:]  # copia da lista
    
    def on_key(e):
        if e.keysym == "Return":
            return
        if e.keysym not in key_combination:
            key_combination.append(e.keysym)
        combo_label.config(text="Combinação: " + "+".join(key_combination))
    win.bind("<Key>", on_key)
    
    clear_button = tk.Button(win, text="Limpar", command=lambda: (key_combination.clear(), combo_label.config(text="Combinação: ")),
                             bg="#535353", fg="white", relief=tk.FLAT, bd=0, width=10, height=1)
    clear_button.pack(pady=5)
    
    def save_keys(e=None):
        opt_val = key_option.get()
        param_val = param_entry.get().strip() or "1.0"
        if key_combination:
            if opt_val == "Simples":
                new_text = f"Pressionar Tecla: {'+'.join(key_combination)}"
            elif opt_val == "Manter":
                new_text = f"Manter pressionada: {'+'.join(key_combination)} - Duração: {param_val}s"
            elif opt_val == "Repetido":
                new_text = f"Tecla repetida: {'+'.join(key_combination)} - Repetir por: {param_val}s"
            event_label.config(text=new_text)
        else:
            event_label.config(text=f"Pressionar Tecla: {'+'.join(keys)}")
        win.destroy()
    win.bind("<Return>", save_keys)
    ok_button = tk.Button(win, text="OK", command=save_keys,
                          bg="#535353", fg="white", font=("Segoe UI", 12),
                          width=10, height=1, relief=tk.FLAT, bd=0)
    ok_button.pack(pady=5)
    win.focus_set()
