import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import shutil
import logging
import threading
import urllib.request
import json
import requests  # Aggiunto per effettuare richieste HTTP
import re  # Aggiunto per parsing del contenuto HTML
import os  # Aggiunto per operazioni di sistema

# Configurazione del logging
logging.basicConfig(filename="app.log", level=logging.ERROR,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def is_connected():
    """Verifica la connessione a Internet tentando di accedere a un URL noto."""
    try:
        urllib.request.urlopen('https://www.google.com', timeout=5)
        return True
    except Exception as e:
        logging.error(f"Errore nella verifica della connessione: {e}")
        return False


def get_system_python():
    """Trova l'interprete Python di sistema."""
    python_executable = shutil.which("python") or shutil.which("python3")
    if not python_executable:
        # Utilizzo di un'istanza temporanea di Tkinter per mostrare il messaggio di errore
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Errore", "Interprete Python non trovato nel sistema.")
        root.destroy()
        sys.exit(1)
    logging.info(f"Interprete Python trovato: {python_executable}")
    return python_executable


SYSTEM_PYTHON = get_system_python()


class InstallLibraryDialog(tk.Toplevel):
    """Finestra di dialogo personalizzata per l'installazione delle librerie."""

    def __init__(self, parent, title="Installa Libreria"):
        super().__init__(parent)
        self.parent = parent
        self.title(title)
        self.geometry("400x150")  # Dimensioni della finestra
        self.resizable(False, False)
        self.library_name = None  # Variabile per memorizzare il nome della libreria

        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.grab_set()  # Modalità di dialogo

    def create_widgets(self):
        """Crea i widget della finestra di dialogo."""
        label = tk.Label(self, text="Inserisci il nome della libreria da installare:")
        label.pack(pady=10)

        self.entry = tk.Entry(self, width=50)
        self.entry.pack(pady=5)
        self.entry.focus_set()

        # Aggiungi menu contestuale al campo di input
        self.add_context_menu(self.entry)

        button_frame = tk.Frame(self)
        button_frame.pack(pady=10)

        ok_button = tk.Button(button_frame, text="OK", width=10, command=self.on_ok)
        ok_button.pack(side=tk.LEFT, padx=5)

        cancel_button = tk.Button(button_frame, text="Annulla", width=10, command=self.on_cancel)
        cancel_button.pack(side=tk.LEFT, padx=5)

        # Bind delle scorciatoie da tastiera
        self.bind("<Return>", lambda event: self.on_ok())
        self.bind("<Escape>", lambda event: self.on_cancel())

    def add_context_menu(self, widget):
        """Aggiunge un menu contestuale (copy, paste, cut) al widget specificato."""
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Taglia", command=lambda: cut_text(widget))
        menu.add_command(label="Copia", command=lambda: copy_text(widget))
        menu.add_command(label="Incolla", command=lambda: paste_text(widget))

        def show_menu(event):
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        widget.bind("<Button-3>", show_menu)  # Click destro del mouse

    def on_ok(self):
        """Gestisce l'evento di pressione del pulsante OK."""
        library_name = self.entry.get().strip()
        if library_name:
            self.library_name = library_name
            self.destroy()
        else:
            messagebox.showerror("Errore", "Il nome della libreria non può essere vuoto.", parent=self)

    def on_cancel(self):
        """Gestisce l'evento di chiusura della finestra di dialogo."""
        self.library_name = None
        self.destroy()


class UpdatePythonDialog(tk.Toplevel):
    """Finestra di dialogo personalizzata per aggiornare Python."""
    
    def __init__(self, parent, current_version, latest_version, download_url):
        super().__init__(parent)
        self.parent = parent
        self.title("Aggiorna Python")
        self.geometry("500x200")
        self.resizable(False, False)
        self.latest_version = latest_version
        self.download_url = download_url
        self.installer_path = os.path.join(os.path.expanduser("~"), f"python-{latest_version}-installer.exe")  # Percorso predefinito
        
        self.create_widgets()
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)
        self.grab_set()
    
    def create_widgets(self):
        """Crea i widget della finestra di dialogo."""
        info_label = tk.Label(self, text=f"È disponibile una nuova versione di Python: {self.latest_version}", font=("Arial", 12))
        info_label.pack(pady=10)
    
        action_frame = tk.Frame(self)
        action_frame.pack(pady=10)
    
        download_button = tk.Button(action_frame, text="Scarica e Installa", command=self.download_and_install)
        download_button.pack(side=tk.LEFT, padx=10)
    
        cancel_button = tk.Button(action_frame, text="Annulla", command=self.on_cancel)
        cancel_button.pack(side=tk.LEFT, padx=10)
    
    def download_and_install(self):
        """Scarica e avvia l'installer di Python."""
        # Mostra una finestra di progressione
        progress = tk.Toplevel(self)
        progress.title("Scaricamento in corso...")
        progress.geometry("300x100")
        progress.resizable(False, False)
        progress_label = tk.Label(progress, text="Scaricamento...")
        progress_label.pack(pady=20)
        progress_bar = ttk.Progressbar(progress, orient="horizontal", length=250, mode="indeterminate")
        progress_bar.pack(pady=10)
        progress_bar.start(10)

        def download_task():
            success = download_python_installer(self.latest_version, self.installer_path)
            progress_bar.stop()
            if success:
                progress_label.config(text="Download completato!")
                progress.after(1000, lambda: progress.destroy())
                # Avvia l'installer
                run_installer(self.installer_path)
                self.destroy()
            else:
                progress_label.config(text="Download fallito!")
                progress_bar['value'] = 0
                messagebox.showerror("Errore", "Impossibile scaricare l'installer di Python.", parent=self)
                progress.after(2000, lambda: progress.destroy())

        threading.Thread(target=download_task).start()

    def on_cancel(self):
        """Chiude la finestra di dialogo."""
        self.destroy()


def update_pip(callback=None, disable_buttons=None, enable_buttons=None):
    """Aggiorna pip all'ultima versione."""
    def task():
        if disable_buttons:
            disable_buttons()
        try:
            result = subprocess.run(
                [SYSTEM_PYTHON, "-m", "pip", "install", "--upgrade", "pip"],
                check=True, capture_output=True, text=True)
            logging.info("pip aggiornato con successo.")
            if callback:
                callback(success=True, message="pip aggiornato con successo.")
        except subprocess.CalledProcessError as e:
            logging.error(f"Errore durante l'aggiornamento di pip: {e.stderr}")
            if callback:
                callback(success=False, message=f"Errore durante l'aggiornamento di pip:\n{e.stderr}")
        except Exception as e:
            logging.error(f"Errore generico durante l'aggiornamento di pip: {e}")
            if callback:
                callback(success=False, message=f"Errore durante l'aggiornamento di pip: {e}")
        finally:
            if enable_buttons:
                enable_buttons()

    threading.Thread(target=task).start()


def fetch_installed_libraries_with_latest(callback, disable_buttons=None, enable_buttons=None):
    """Ritorna una lista di tuple con nome, versione installata e ultima versione delle librerie."""
    def task():
        if disable_buttons:
            disable_buttons()
        try:
            if not is_connected():
                messagebox.showerror("Errore", "Connessione a Internet non disponibile.")
                return

            # Ottieni tutte le librerie installate
            installed_result = subprocess.run(
                [SYSTEM_PYTHON, "-m", "pip", "list", "--format=freeze"],
                capture_output=True, text=True, check=True)

            # Ottieni le librerie obsolete in formato JSON
            outdated_result = subprocess.run(
                [SYSTEM_PYTHON, "-m", "pip", "list", "--outdated", "--format=json"],
                capture_output=True, text=True, check=True)

            # Parsing delle librerie installate
            installed_libraries = {}
            for line in installed_result.stdout.strip().splitlines():
                if '==' in line:
                    name, version = line.split("==")
                    installed_libraries[name.lower()] = version

            # Parsing delle librerie obsolete
            outdated_libraries = {}
            outdated_data = json.loads(outdated_result.stdout)
            for package in outdated_data:
                name = package['name'].lower()
                latest_version = package['latest_version']
                outdated_libraries[name] = latest_version

            # Combina le informazioni
            libraries = []
            for name, version in installed_libraries.items():
                latest_version = outdated_libraries.get(name, version)
                libraries.append((name, version, latest_version))

            if callback:
                callback(libraries=libraries)
        except subprocess.CalledProcessError as e:
            logging.error(f"Errore subprocess durante il recupero delle librerie: {e}")
            logging.error(f"Stdout: {e.stdout}")
            logging.error(f"Stderr: {e.stderr}")
            messagebox.showerror("Errore", f"Errore durante il recupero delle librerie:\n{e.stderr}")
        except json.JSONDecodeError as e:
            logging.error(f"Errore di parsing JSON: {e}")
            messagebox.showerror("Errore", f"Errore durante il parsing dei dati:\n{e}")
        except Exception as e:
            logging.error(f"Errore generico durante il recupero delle librerie: {e}")
            messagebox.showerror("Errore", f"Errore durante il recupero delle librerie: {e}")
        finally:
            if enable_buttons:
                enable_buttons()

    threading.Thread(target=task).start()


def fetch_library_description(library_name, callback, disable_buttons=None, enable_buttons=None):
    """Recupera la descrizione della libreria dal comando pip show."""
    def task():
        if disable_buttons:
            disable_buttons()
        try:
            if not is_connected():
                callback(description="Connessione a Internet non disponibile.")
                return

            result = subprocess.run(
                [SYSTEM_PYTHON, "-m", "pip", "show", library_name],
                capture_output=True, text=True, check=True)
            if result.stdout:
                details = result.stdout.strip()
                callback(description=details)
            else:
                callback(description="Nessuna descrizione disponibile per questa libreria.")
        except subprocess.CalledProcessError as e:
            logging.error(f"Errore subprocess durante il recupero della descrizione di {library_name}: {e}")
            logging.error(f"Stdout: {e.stdout}")
            logging.error(f"Stderr: {e.stderr}")
            callback(description=f"Nessuna descrizione disponibile o libreria non trovata.\n{e.stderr}")
        except Exception as e:
            logging.error(f"Errore generico durante il recupero della descrizione di {library_name}: {e}")
            callback(description=f"Errore durante il recupero della descrizione: {e}")
        finally:
            if enable_buttons:
                enable_buttons()

    threading.Thread(target=task).start()


def update_library(library_name, callback=None, disable_buttons=None, enable_buttons=None):
    """Aggiorna una libreria specifica."""
    def task():
        if disable_buttons:
            disable_buttons()
        try:
            subprocess.run(
                [SYSTEM_PYTHON, "-m", "pip", "install", "--upgrade", library_name],
                check=True, capture_output=True, text=True)
            logging.info(f"Libreria {library_name} aggiornata con successo.")
            if callback:
                callback(success=True, message=f"Libreria {library_name} aggiornata con successo.")
        except subprocess.CalledProcessError as e:
            logging.error(f"Errore subprocess durante l'aggiornamento di {library_name}: {e.stderr}")
            if callback:
                callback(success=False, message=f"Errore durante l'aggiornamento della libreria {library_name}:\n{e.stderr}")
        except Exception as e:
            logging.error(f"Errore generico durante l'aggiornamento di {library_name}: {e}")
            if callback:
                callback(success=False, message=f"Errore durante l'aggiornamento della libreria {library_name}: {e}")
        finally:
            if enable_buttons:
                enable_buttons()

    threading.Thread(target=task).start()


def uninstall_library(library_name, callback=None, disable_buttons=None, enable_buttons=None):
    """Disinstalla una libreria specifica."""
    def task():
        if disable_buttons:
            disable_buttons()
        try:
            # Evita di disinstallare pip, setuptools o wheel
            if library_name.lower() in ["pip", "setuptools", "wheel"]:
                messagebox.showerror("Errore", f"Non è possibile disinstallare la libreria '{library_name}'.")
                return

            subprocess.run(
                [SYSTEM_PYTHON, "-m", "pip", "uninstall", "-y", library_name],
                check=True, capture_output=True, text=True)
            logging.info(f"Libreria {library_name} disinstallata con successo.")
            if callback:
                callback(success=True, message=f"Libreria {library_name} disinstallata con successo.")
        except subprocess.CalledProcessError as e:
            logging.error(f"Errore subprocess durante la disinstallazione di {library_name}: {e.stderr}")
            if callback:
                callback(success=False, message=f"Errore durante la disinstallazione della libreria {library_name}:\n{e.stderr}")
        except Exception as e:
            logging.error(f"Errore generico durante la disinstallazione di {library_name}: {e}")
            if callback:
                callback(success=False, message=f"Errore durante la disinstallazione della libreria {library_name}: {e}")
        finally:
            if enable_buttons:
                enable_buttons()

    threading.Thread(target=task).start()


def install_library(callback=None, disable_buttons=None, enable_buttons=None):
    """Installa una nuova libreria specificata dall'utente."""
    def task(library_name):
        if disable_buttons:
            disable_buttons()
        try:
            subprocess.run(
                [SYSTEM_PYTHON, "-m", "pip", "install", library_name],
                check=True, capture_output=True, text=True)
            logging.info(f"Libreria {library_name} installata con successo.")
            if callback:
                callback(success=True, message=f"Libreria {library_name} installata con successo.")
        except subprocess.CalledProcessError as e:
            logging.error(f"Errore subprocess durante l'installazione di {library_name}: {e.stderr}")
            if callback:
                callback(success=False, message=f"Errore durante l'installazione della libreria {library_name}:\n{e.stderr}")
        except Exception as e:
            logging.error(f"Errore generico durante l'installazione di {library_name}: {e}")
            if callback:
                callback(success=False, message=f"Errore durante l'installazione della libreria: {e}")
        finally:
            if enable_buttons:
                enable_buttons()

    # Creazione della finestra di dialogo personalizzata
    dialog = InstallLibraryDialog(parent=None, title="Installa Libreria")
    dialog.wait_window()  # Attende la chiusura della finestra di dialogo
    library_name = dialog.library_name
    if library_name:
        threading.Thread(target=task, args=(library_name,)).start()


def show_library_details(library_name):
    """Mostra una finestra modale con i dettagli della libreria."""
    details_window = tk.Toplevel()
    details_window.title(f"Dettagli di {library_name}")
    details_window.geometry("550x400")  # Aumentato di 50px in larghezza
    details_window.resizable(False, False)

    text = tk.Text(details_window, wrap=tk.WORD)
    text.pack(fill=tk.BOTH, expand=True)

    # Aggiungi menu contestuale per copia e incolla
    add_context_menu(text)

    def set_description(description):
        text.insert(tk.END, description)

    fetch_library_description(library_name, set_description)


def add_context_menu(widget):
    """Aggiunge un menu contestuale (copy, paste, cut) al widget specificato."""
    menu = tk.Menu(widget, tearoff=0)
    menu.add_command(label="Taglia", command=lambda: cut_text(widget))
    menu.add_command(label="Copia", command=lambda: copy_text(widget))
    menu.add_command(label="Incolla", command=lambda: paste_text(widget))

    def show_menu(event):
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    widget.bind("<Button-3>", show_menu)  # Click destro del mouse


def copy_text(widget):
    """Copia il testo selezionato nel widget."""
    try:
        selected_text = widget.selection_get()
        widget.clipboard_clear()
        widget.clipboard_append(selected_text)
    except tk.TclError:
        pass  # Nessun testo selezionato


def paste_text(widget):
    """Incolla il testo dagli appunti nel widget."""
    try:
        clipboard_text = widget.clipboard_get()
        widget.insert(tk.INSERT, clipboard_text)
    except tk.TclError:
        pass  # Nessun testo negli appunti


def cut_text(widget):
    """Taglia il testo selezionato nel widget."""
    try:
        selected_text = widget.selection_get()
        widget.clipboard_clear()
        widget.clipboard_append(selected_text)
        widget.delete("sel.first", "sel.last")
    except tk.TclError:
        pass  # Nessun testo selezionato


def update_python_installed():
    """Funzione placeholder se necessario."""
    pass  # Da implementare se vuoi verificare se Python è aggiornato dopo l'installazione


def create_gui():
    """Crea l'interfaccia grafica per la gestione delle librerie."""
    root = tk.Tk()
    root.title("Gestione Librerie Python")

    # Imposta dimensioni minime e geometria iniziale (aumentata di 50px in larghezza)
    root.minsize(1000, 650)
    root.geometry("1000x650")  # Inizializza la finestra con la nuova larghezza

    frame = tk.Frame(root)
    frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    tree = ttk.Treeview(frame, columns=("Libreria", "Versione Installata", "Ultima Versione"), show="headings", height=20)
    tree.heading("Libreria", text="Libreria")
    tree.heading("Versione Installata", text="Versione Installata")
    tree.heading("Ultima Versione", text="Ultima Versione")
    tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

    tree.tag_configure("red", foreground="red")
    tree.tag_configure("black", foreground="black")
    tree.tag_configure("loading", foreground="blue")

    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.pack(fill=tk.Y, side=tk.RIGHT)

    button_frame = tk.Frame(root)
    button_frame.pack(fill=tk.X, padx=10, pady=10)

    # Definizione dei pulsanti
    update_button = tk.Button(button_frame, text="Aggiorna Libreria", bg="lightblue", fg="black")
    update_button.pack(side=tk.LEFT, padx=5)

    uninstall_button = tk.Button(button_frame, text="Disinstalla Libreria", bg="salmon", fg="black")
    uninstall_button.pack(side=tk.LEFT, padx=5)

    install_button = tk.Button(button_frame, text="Installa Libreria", bg="lightgreen", fg="black")
    install_button.pack(side=tk.LEFT, padx=5)

    refresh_button = tk.Button(button_frame, text="Aggiorna Elenco", bg="lightgray", fg="black")
    refresh_button.pack(side=tk.LEFT, padx=5)

    update_pip_button = tk.Button(button_frame, text="Aggiorna pip", bg="orange", fg="black")
    update_pip_button.pack(side=tk.LEFT, padx=5)

    update_python_button = tk.Button(button_frame, text="Aggiorna Python", bg="purple", fg="white")
    update_python_button.pack(side=tk.LEFT, padx=5)

    exit_button = tk.Button(button_frame, text="Esci", command=root.quit, bg="red", fg="white")
    exit_button.pack(side=tk.RIGHT, padx=5)

    copyright_label = tk.Label(root, text="© NuAnda Seo Consulting", fg="black", anchor="e")
    copyright_label.pack(fill=tk.X, pady=5, side=tk.BOTTOM, anchor="e")

    # Funzioni per gestire le azioni dei pulsanti
    def on_update(tree_widget):
        selected_item = tree_widget.selection()
        if selected_item:
            library_name = tree_widget.item(selected_item[0], "values")[0]
            disable_specific_buttons(['update'])
            update_library(
                library_name,
                callback=lambda success, message: show_callback_message(success, message, enable_buttons=lambda: enable_specific_buttons(['update'])),
                disable_buttons=lambda: disable_specific_buttons(['update']),
                enable_buttons=lambda: enable_specific_buttons(['update'])
            )

    def on_uninstall(tree_widget):
        selected_item = tree_widget.selection()
        if selected_item:
            library_name = tree_widget.item(selected_item[0], "values")[0]
            confirm = messagebox.askyesno("Conferma Disinstallazione", f"Sei sicuro di voler disinstallare '{library_name}'?")
            if confirm:
                disable_specific_buttons(['uninstall'])
                uninstall_library(
                    library_name,
                    callback=lambda success, message: show_callback_message(success, message, enable_buttons=lambda: enable_specific_buttons(['uninstall'])),
                    disable_buttons=lambda: disable_specific_buttons(['uninstall']),
                    enable_buttons=lambda: enable_specific_buttons(['uninstall'])
                )

    def on_install(callback):
        install_button.config(state=tk.DISABLED)  # Disabilita solo il pulsante install
        install_library(
            callback=lambda success, message: show_callback_message(success, message, enable_buttons=lambda: enable_specific_buttons(['install'])),
            disable_buttons=lambda: disable_specific_buttons(['install']),
            enable_buttons=lambda: enable_specific_buttons(['install'])
        )

    def on_refresh(tree_widget):
        populate_treeview(tree_widget)

    def on_update_pip(root_window):
        disable_specific_buttons(['update_pip'])
        update_pip(
            callback=lambda success, message: show_callback_message(success, message, enable_buttons=lambda: enable_specific_buttons(['update_pip'])),
            disable_buttons=lambda: disable_specific_buttons(['update_pip']),
            enable_buttons=lambda: enable_specific_buttons(['update_pip'])
        )

    def on_update_python():
        """Gestisce l'aggiornamento di Python."""
        current_version = get_current_python_version()
        latest_version = get_latest_python_version()
        
        if latest_version:
            if is_newer_version(current_version, latest_version):
                # Determina l'URL dell'installer in base al sistema operativo
                if os.name == 'nt':  # Windows
                    download_url = f"https://www.python.org/ftp/python/{latest_version}/python-{latest_version}-amd64.exe"
                elif sys.platform == 'darwin':  # macOS
                    download_url = f"https://www.python.org/ftp/python/{latest_version}/python-{latest_version}-macosx10.9.pkg"
                else:  # Linux o altri
                    # Su Linux, l'aggiornamento di Python è generalmente gestito tramite il gestore di pacchetti
                    messagebox.showinfo("Aggiornamento Python", "Per aggiornare Python su Linux, utilizza il tuo gestore di pacchetti.", parent=root)
                    return
                
                # Crea e mostra la finestra di dialogo per l'aggiornamento
                dialog = UpdatePythonDialog(root, current_version, latest_version, download_url)
            else:
                messagebox.showinfo("Python Aggiornato", "Hai già l'ultima versione di Python installata.", parent=root)
        else:
            messagebox.showerror("Errore", "Impossibile determinare l'ultima versione di Python.", parent=root)

    def show_callback_message(success, message, enable_buttons=None):
        """Mostra un messaggio di callback e aggiorna la Treeview."""
        if success:
            messagebox.showinfo("Successo", message, parent=root)
        else:
            messagebox.showerror("Errore", message, parent=root)
        # Deseleziona eventuali selezioni
        tree.selection_remove(tree.selection())
        # Refresh della Treeview
        populate_treeview(tree)
        # Re-enable buttons
        if enable_buttons:
            enable_buttons()

    def refresh_treeview():
        populate_treeview(tree)

    def populate_treeview(tree_widget):
        # Pulisci l'albero
        tree_widget.delete(*tree_widget.get_children())

        # Mostra un indicatore di caricamento
        loading_item = tree_widget.insert("", "end", values=("Caricamento...", "", ""), tags=("loading",))

        def callback(libraries=None):
            # Rimuovi l'indicatore di caricamento
            tree_widget.delete(loading_item)
            if libraries is not None:
                for library, installed_version, latest_version in libraries:
                    color = "red" if installed_version != latest_version else "black"
                    tree_widget.insert("", "end", values=(library, installed_version, latest_version), tags=(color,))

        fetch_installed_libraries_with_latest(callback, disable_buttons=None, enable_buttons=None)

    def on_double_click(event):
        item = tree.selection()
        if item:
            library_name = tree.item(item[0], "values")[0]
            show_library_details(library_name)

    tree.bind("<Double-1>", on_double_click)

    # Funzioni per disabilitare e abilitare pulsanti specifici
    def disable_specific_buttons(buttons):
        for btn in buttons:
            if btn == 'update':
                update_button.config(state=tk.DISABLED)
            elif btn == 'uninstall':
                uninstall_button.config(state=tk.DISABLED)
            elif btn == 'install':
                install_button.config(state=tk.DISABLED)
            elif btn == 'refresh':
                refresh_button.config(state=tk.DISABLED)
            elif btn == 'update_pip':
                update_pip_button.config(state=tk.DISABLED)
            elif btn == 'update_python':
                update_python_button.config(state=tk.DISABLED)

    def enable_specific_buttons(buttons):
        for btn in buttons:
            if btn == 'update':
                update_button.config(state=tk.NORMAL)
            elif btn == 'uninstall':
                uninstall_button.config(state=tk.NORMAL)
            elif btn == 'install':
                install_button.config(state=tk.NORMAL)
            elif btn == 'refresh':
                refresh_button.config(state=tk.NORMAL)
            elif btn == 'update_pip':
                update_pip_button.config(state=tk.NORMAL)
            elif btn == 'update_python':
                update_python_button.config(state=tk.NORMAL)

    # Assegna le funzioni ai pulsanti
    update_button.config(command=lambda: on_update(tree))
    uninstall_button.config(command=lambda: on_uninstall(tree))
    install_button.config(command=lambda: on_install(callback=refresh_treeview))
    refresh_button.config(command=lambda: on_refresh(tree))
    update_pip_button.config(command=lambda: on_update_pip(root))
    update_python_button.config(command=lambda: on_update_python())

    # Aggiungi menu contestuale alla Treeview per la copia
    add_treeview_context_menu(tree)

    # Bind delle scorciatoie da tastiera per copia e incolla
    root.bind_all("<Control-c>", lambda event: copy_selection(tree))
    root.bind_all("<Control-v>", lambda event: paste_selection(tree))
    root.bind_all("<Control-C>", lambda event: copy_selection(tree))
    root.bind_all("<Control-V>", lambda event: paste_selection(tree))

    populate_treeview(tree)

    root.mainloop()


def add_treeview_context_menu(tree_widget):
    """Aggiunge un menu contestuale alla Treeview per operazioni di copia."""
    menu = tk.Menu(tree_widget, tearoff=0)
    menu.add_command(label="Copia", command=lambda: copy_treeview_selection(tree_widget))

    def show_menu(event):
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    tree_widget.bind("<Button-3>", show_menu)  # Click destro del mouse


def copy_treeview_selection(tree_widget):
    """Copia la selezione corrente della Treeview negli appunti."""
    selected_item = tree_widget.selection()
    if selected_item:
        library_name, installed_version, latest_version = tree_widget.item(selected_item[0], "values")
        copy_text_to_clipboard(f"Libreria: {library_name}\nVersione Installata: {installed_version}\nUltima Versione: {latest_version}")


def copy_text_to_clipboard(text):
    """Copia il testo fornito negli appunti."""
    try:
        root = tk.Tk()
        root.withdraw()  # Nasconde la finestra principale
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()  # Necessario per Windows
        root.destroy()
    except Exception as e:
        logging.error(f"Errore durante la copia negli appunti: {e}")


def copy_selection(tree_widget):
    """Copia la selezione corrente della Treeview se esistente."""
    copy_treeview_selection(tree_widget)


def paste_selection(tree_widget):
    """Funzione placeholder per incollare nella Treeview, se necessario."""
    # La Treeview non supporta direttamente l'incollaggio di dati
    pass


def get_current_python_version():
    """Restituisce la versione corrente di Python in uso."""
    return sys.version.split()[0]


def get_latest_python_version():
    """Recupera l'ultima versione di Python disponibile dal sito ufficiale."""
    try:
        response = requests.get("https://www.python.org/downloads/", timeout=10)
        if response.status_code == 200:
            # Cerca la prima occorrenza di 'Python x.y.z'
            match = re.search(r'Python (\d+\.\d+\.\d+)', response.text)
            if match:
                return match.group(1)
        logging.error(f"Impossibile recuperare l'ultima versione di Python. Status Code: {response.status_code}")
    except Exception as e:
        logging.error(f"Errore durante il recupero dell'ultima versione di Python: {e}")
    return None


def is_newer_version(current_version, latest_version):
    """Determina se la versione 'latest_version' è più recente di 'current_version'."""
    def version_tuple(v):
        return tuple(map(int, (v.split("."))))
    
    return version_tuple(latest_version) > version_tuple(current_version)


def download_python_installer(version, download_path):
    """Scarica l'installer di Python per la versione specificata."""
    try:
        # Costruisci l'URL dell'installer (esempio per Windows 64-bit)
        # Puoi estendere questa funzione per supportare altri sistemi operativi e architetture
        url = f"https://www.python.org/ftp/python/{version}/python-{version}-amd64.exe"
        response = requests.get(url, stream=True, timeout=30)
        if response.status_code == 200:
            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.info(f"Installer scaricato correttamente in {download_path}")
            return True
        else:
            logging.error(f"Impossibile scaricare l'installer di Python. Status Code: {response.status_code}")
    except Exception as e:
        logging.error(f"Errore durante il download dell'installer di Python: {e}")
    return False


def run_installer(installer_path):
    """Esegue l'installer di Python scaricato."""
    try:
        if os.name == 'nt':  # Windows
            subprocess.Popen([installer_path], shell=True)
        elif sys.platform == 'darwin':  # macOS
            subprocess.Popen(['open', installer_path])
        else:  # Linux o altri
            subprocess.Popen(['chmod', '+x', installer_path])
            subprocess.Popen([installer_path])
        logging.info(f"Installer avviato: {installer_path}")
        return True
    except Exception as e:
        logging.error(f"Errore durante l'esecuzione dell'installer: {e}")
    return False


if __name__ == "__main__":
    create_gui()
