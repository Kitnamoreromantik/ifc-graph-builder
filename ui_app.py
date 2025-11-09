r"""
To run:
uv run ui_app.py

To build executable for Win (in Win dev machine):

1. Install all the needed dependencies:
python -m pip install -r requirements.txt
2. Found ifc4.exp schema and put to C:\Users\demo-airi\AppData\Local\Programs\Python\Python312\Lib\site-packages\ifcopenshell\express
3. Run in powershell (terminal):
pyinstaller --onefile --windowed `
  --name "IFC2Graph" `
  --icon "assets\app_icon.ico" `
  --hidden-import networkx `
  --hidden-import ifcopenshell `
  --hidden-import ifcopenshell.util.element `
  --add-data "assets;assets" `
  --add-data "allowed_ifc_types.json;." `
  --add-data "C:\Users\demo-airi\AppData\Local\Programs\Python\Python312\Lib\site-packages\ifcopenshell\express;ifcopenshell/express" `
  --add-data "C:\Users\demo-airi\AppData\Local\Programs\Python\Python312\Lib\site-packages\pyvis\templates;pyvis/templates" `
  ui_app.py
4. Find .exe in dist folder
"""

import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox, Toplevel
from pathlib import Path
import threading
import logging
import json
import platform
import sys
import subprocess

# Import converter entry point directly
from src.main import run as run_ifc_converter

# =============================
# Paths & Logging
# =============================
MAIN_SCRIPT = (Path(__file__).parent / "src" / "main.py").resolve()
ALLOWED_IFC_FILE = Path("allowed_ifc_types.json")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# =============================
# IFC GROUPS
# =============================
IFC_GROUPS = {
    "Пространственная структура": [
        "IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace",
        "IfcZone", "IfcRelAggregates", "IfcRelContainedInSpatialStructure", "IfcRelSpaceBoundary",
    ],
    "Архитектурные и конструктивные элементы": [
        "IfcWall", "IfcWallStandardCase", "IfcSlab", "IfcRoof", "IfcDoor", "IfcWindow",
        "IfcColumn", "IfcBeam", "IfcStair", "IfcRailing", "IfcOpeningElement",
        "IfcCovering", "IfcBuildingElementProxy", "IfcFurnishingElement",
        "IfcSystemFurnitureElement", "IfcDistributionElement", "IfcFlowTerminal",
        "IfcBuildingElement",
    ],
    "Количество и свойства": [
        "IfcElementQuantity", "IfcQuantityArea", "IfcQuantityVolume", "IfcQuantityLength",
        "IfcRelDefinesByProperties", "IfcRelDefinesByType",
    ],
    "Материалы и классификации": [
        "IfcMaterial", "IfcMaterialLayer", "IfcMaterialLayerSet", "IfcMaterialConstituentSet",
        "IfcRelAssociatesMaterial", "IfcRelAssociatesClassification", "IfcClassificationReference",
    ],
    "Положение и геометрия": [
        "IfcProductDefinitionShape", "IfcShapeRepresentation", "IfcLocalPlacement",
        "IfcAxis2Placement3D", "IfcDirection", "IfcCartesianPoint",
    ],
}

# Flatten list for global dictionary creation
IFC_ENTITIES = [e for group in IFC_GROUPS.values() for e in group]

# =============================
# Main window initialization
# =============================
root = ttk.Window(themename="flatly")  # modern Bootstrap-like theme
root.title("IFC → JSON")
root.geometry("640x320")
root.resizable(False, False)

# --- Icon setup ---
ICON_DIR = Path(__file__).parent / "assets"
icon_path_ico = ICON_DIR / "app_icon.ico"
icon_path_png = ICON_DIR / "app_icon.png"
system_name = platform.system()

try:
    if system_name == "Windows" and icon_path_ico.exists():
        root.iconbitmap(default=str(icon_path_ico))
    elif icon_path_png.exists():
        root.iconphoto(True, ttk.PhotoImage(file=str(icon_path_png)))
except Exception as e:
    print(f"⚠️ Could not set app icon: {e}")

# Variables
selected_entities = {e: ttk.BooleanVar(value=True) for e in IFC_ENTITIES}
output_dir_path = None
recursion_depth_var = ttk.StringVar(value="1")

# =============================
# Helper Functions
# =============================
def notify_ui(fn, *args, **kwargs):
    root.after(0, lambda: fn(*args, **kwargs))

def run_conversion(ifc_path):
    try:
        chosen = [e for e, v in selected_entities.items() if v.get()]
        with open(ALLOWED_IFC_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(chosen), f, indent=2, ensure_ascii=False)

        depth_value = recursion_depth_var.get().strip()
        depth = None if depth_value.lower() == "none" else int(depth_value)
        run_ifc_converter(Path(ifc_path), Path(output_dir_path) if output_dir_path else None, depth)

        notify_ui(messagebox.showinfo, "Success", f"Конвертация завершена:\n{ifc_path}")
        notify_ui(status_label.config, text="Готово ✅", foreground="green")
    except Exception as e:
        logging.exception(e)
        notify_ui(messagebox.showerror, "Error", str(e))
        notify_ui(status_label.config, text="Ошибка ❌", foreground="red")
    finally:
        notify_ui(start_button.config, state=NORMAL)

def select_file():
    file_path = filedialog.askopenfilename(title="Выбрать IFC файл", filetypes=[("IFC files", "*.ifc"), ("All files", "*.*")])
    if file_path:
        status_label.config(text=f"Файл выбран: {file_path}", foreground="green")
        start_button.config(state=NORMAL)
        start_button.configure(command=lambda: start_conversion(file_path))

def select_output_dir():
    global output_dir_path
    output_dir = filedialog.askdirectory(title="Выбрать папку для сохранения результатов")
    if output_dir:
        output_dir_path = output_dir
        output_label.config(text=f"Папка вывода: {output_dir}", foreground="green")

def start_conversion(ifc_path):
    start_button.config(state=DISABLED)
    status_label.config(text="В процессе...", foreground="#E67E22")
    threading.Thread(target=run_conversion, args=(ifc_path,), daemon=True).start()

# =============================
# IFC Entity Selection Window
# =============================
def open_ifc_selector():
    win = ttk.Toplevel(root)
    win.title("Выбор сущностей для включения в граф")
    win.geometry("420x620")
    win.resizable(False, True)

    frame = ttk.Frame(win, padding=10)
    frame.pack(fill="both", expand=True)

    canvas = ttk.Canvas(frame)
    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    scroll = ttk.Frame(canvas)
    scroll.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    for group_name, entities in IFC_GROUPS.items():
        ttk.Label(scroll, text=group_name, font=("Segoe UI", 10, "bold")).pack(fill="x", pady=(8, 2))
        for ent in entities:
            ttk.Checkbutton(scroll, text=ent, variable=selected_entities[ent], bootstyle="round-toggle").pack(anchor="w", padx=18)

    btn_frame = ttk.Frame(win, padding=5)
    btn_frame.pack(pady=(10, 4))  # smaller bottom padding

    ttk.Button(
        btn_frame,
        text="Выбрать все",
        bootstyle="success-outline",
        command=lambda: [v.set(True) for v in selected_entities.values()]
    ).pack(side="left", padx=5)

    ttk.Button(
        btn_frame,
        text="Снять все",
        bootstyle="secondary-outline",
        command=lambda: [v.set(False) for v in selected_entities.values()]
    ).pack(side="left", padx=5)

    # ↓ slightly raised and same green tone
    ttk.Button(
        btn_frame,
        text="Сохранить выбор",
        bootstyle="success",     # green solid style
        command=lambda: save_selection(win)
    ).pack(side="left", padx=10)

    def save_selection(win):
        chosen = [e for e, v in selected_entities.items() if v.get()]
        with open(ALLOWED_IFC_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(chosen), f, indent=2, ensure_ascii=False)
        messagebox.showinfo("Сохранено", f"Выбрано {len(chosen)} типов IFC-сущностей")
        win.destroy()

# =============================
# Main GUI Layout
# =============================
menubar = ttk.Menu(root)
settings_menu = ttk.Menu(menubar, tearoff=0)
settings_menu.add_command(label="Выбор IFC сущностей...", command=open_ifc_selector)
menubar.add_cascade(label="Настройки", menu=settings_menu)
root.config(menu=menubar)

ttk.Label(root, text="Конвертация IFC файла в JSON для графовой БД и схемы IFC-графа", font=("Segoe UI", 10, "bold")).pack(pady=6)

select_button = ttk.Button(root, text="Выбрать IFC файл", bootstyle="primary", command=select_file)
select_button.pack(pady=5)

status_label = ttk.Label(root, text="Файл не выбран", foreground="gray")
status_label.pack(pady=5)

output_button = ttk.Button(root, text="Выбрать папку вывода", bootstyle="info", command=select_output_dir)
output_button.pack(pady=5)

output_label = ttk.Label(root, text="Папка вывода не выбрана", foreground="gray")
output_label.pack(pady=2)

depth_label = ttk.Label(root, text="Макс. глубина поиска при парсинге графа:")
depth_label.pack(pady=(10, 2))

depth_spin = ttk.Spinbox(root, from_=0, to=10, width=5, textvariable=recursion_depth_var, bootstyle="info")
depth_spin.pack(pady=(0, 5))

ttk.Label(root, text="Введите целое число или 'None' (без кавычек) для бесконечной глубины.", font=("Segoe UI", 8), foreground="gray").pack(pady=(0, 4))

start_button = ttk.Button(root, text="Начать конвертацию", state=DISABLED, bootstyle="success")
start_button.pack(pady=5)

root.mainloop()
