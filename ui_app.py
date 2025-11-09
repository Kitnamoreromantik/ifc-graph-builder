"""
To run:
uv run ui_app.py

To build executable:

pyinstaller --onefile --windowed \
  --name "IFC2Graph" \
  --icon "assets/app_icon.icns" \
  --add-data "assets:assets" \
  --add-data "allowed_ifc_types.json:." \
  ui_app.py

"""

import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel
import threading
import logging
from pathlib import Path
import subprocess
import sys
import json

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
        "IfcProject",
        "IfcSite",
        "IfcBuilding",
        "IfcBuildingStorey",
        "IfcSpace",
        "IfcZone",
        "IfcRelAggregates",
        "IfcRelContainedInSpatialStructure",
        "IfcRelSpaceBoundary",
    ],
    "Архитектурные и конструктивные элементы": [
        "IfcWall",
        "IfcWallStandardCase",
        "IfcSlab",
        "IfcRoof",
        "IfcDoor",
        "IfcWindow",
        "IfcColumn",
        "IfcBeam",
        "IfcStair",
        "IfcRailing",
        "IfcOpeningElement",
        "IfcCovering",
        "IfcBuildingElementProxy",
        "IfcFurnishingElement",
        "IfcSystemFurnitureElement",
        "IfcDistributionElement",
        "IfcFlowTerminal",
        "IfcBuildingElement",
    ],
    "Количество и свойства": [
        "IfcElementQuantity",
        "IfcQuantityArea",
        "IfcQuantityVolume",
        "IfcQuantityLength",
        "IfcRelDefinesByProperties",
        "IfcRelDefinesByType",
    ],
    "Материалы и классификации": [
        "IfcMaterial",
        "IfcMaterialLayer",
        "IfcMaterialLayerSet",
        "IfcMaterialConstituentSet",
        "IfcRelAssociatesMaterial",
        "IfcRelAssociatesClassification",
        "IfcClassificationReference",
    ],
    "Положение и геометрия": [
        "IfcProductDefinitionShape",
        "IfcShapeRepresentation",
        "IfcLocalPlacement",
        "IfcAxis2Placement3D",
        "IfcDirection",
        "IfcCartesianPoint",
    ],
}

# Flatten list for global dictionary creation
IFC_ENTITIES = [e for group in IFC_GROUPS.values() for e in group]

# =============================
# Main window initialization
# =============================
root = tk.Tk()

# Icon setup:
#-------------------------------------------
import platform
import tkinter as tk
from pathlib import Path

ICON_DIR = Path(__file__).parent / "assets"
icon_path_ico = ICON_DIR / "app_icon.ico"
icon_path_icns = ICON_DIR / "app_icon.icns"
icon_path_png = ICON_DIR / "app_icon.png"

system_name = platform.system()

try:
    if system_name == "Windows" and icon_path_ico.exists():
        root.iconbitmap(default=str(icon_path_ico))

    elif system_name == "Darwin":  # macOS
        # Tkinter cannot load .icns — use .png instead
        if icon_path_png.exists():
            root.iconphoto(True, tk.PhotoImage(file=str(icon_path_png)))

        # # Optional: set Dock icon via AppKit if pyobjc available
        # try:
        #     import AppKit
        #     if icon_path_icns.exists():
        #         app = AppKit.NSApplication.sharedApplication()
        #         app.setApplicationIconImage_(
        #             AppKit.NSImage.alloc().initByReferencingFile_(str(icon_path_icns))
        #         )
        # except Exception as e:
        #     print(f"⚠️ Dock icon not set: {e}")

    else:
        # Linux or fallback: try PNG
        if icon_path_png.exists():
            root.iconphoto(True, tk.PhotoImage(file=str(icon_path_png)))

except Exception as e:
    print(f"⚠️ Could not set app icon: {e}")


root.title("IFC → JSON")
root.geometry("680x300")
root.resizable(False, False)

# Now root exists — safe to create BooleanVars
selected_entities = {e: tk.BooleanVar(master=root, value=True) for e in IFC_ENTITIES}

# Global variable for output directory
output_dir_path = None

# =============================
# Helper Functions
# =============================
def notify_ui(fn, *args, **kwargs):
    """Safely trigger UI updates from a background thread."""
    root.after(0, lambda: fn(*args, **kwargs))


def run_conversion(ifc_path):
    """Run the main converter in background."""
    try:
        chosen = [e for e, v in selected_entities.items() if v.get()]
        with open(ALLOWED_IFC_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(chosen), f, indent=2, ensure_ascii=False)

        # Build command with optional output dir
        cmd = [sys.executable, str(MAIN_SCRIPT), str(ifc_path)]

        # Add output dir if selected
        if output_dir_path:
            cmd.append(output_dir_path)

        # Add recursion depth as argument
        depth_value = recursion_depth_var.get().strip()
        if depth_value.lower() == "none":
            cmd.append("None")
        else:
            cmd.append(depth_value)
            
        # -----------------------------
        subprocess.run(cmd, check=True)
        # -----------------------------

        notify_ui(messagebox.showinfo, "Success", f"Конвертация завершена:\n{ifc_path}")
        notify_ui(status_label.config, text="Готово ✅", fg="green")
    except subprocess.CalledProcessError as e:
        notify_ui(messagebox.showerror, "Error", f"❌ Ошибка конвертации\n{e}")
        notify_ui(status_label.config, text="Ошибка ❌", fg="red")
    except Exception as e:
        notify_ui(messagebox.showerror, "Error", str(e))
        notify_ui(status_label.config, text="Ошибка ❌", fg="red")
    finally:
        notify_ui(start_button.config, state=tk.NORMAL)


def select_file():
    """Select IFC file."""
    file_path = filedialog.askopenfilename(
        title="Выбрать IFC файл",
        filetypes=[("IFC files", "*.ifc"), ("All files", "*.*")],
    )
    if file_path:
        status_label.config(text=f"Файл выбран: {file_path}", fg="green")
        # path_label.config(text=file_path, fg="green")
        start_button.config(state=tk.NORMAL)
        start_button.configure(command=lambda: start_conversion(file_path))


def select_output_dir():
    """Select output directory for conversion results."""
    global output_dir_path
    output_dir = filedialog.askdirectory(title="Выбрать папку для сохранения результатов")
    if output_dir:
        output_dir_path = output_dir
        output_label.config(text=f"Папка вывода: {output_dir}", fg="green")


def start_conversion(ifc_path):
    """Start conversion in background."""
    start_button.config(state=tk.DISABLED)
    status_label.config(text="В процессе...", fg="orange")
    threading.Thread(target=run_conversion, args=(ifc_path,), daemon=True).start()

# =============================
# IFC Entity Selection Window
# =============================
def open_ifc_selector():
    win = Toplevel(root)
    win.title("Выбор сущностей для включения в граф")
    win.geometry("400x650")
    win.resizable(False, True)

    frame = tk.Frame(win)
    frame.pack(fill="both", expand=True)
    canvas = tk.Canvas(frame)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar = tk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    scrollbar.pack(side="right", fill="y")
    scroll = tk.Frame(canvas)
    scroll.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Grouped checkboxes
    for group_name, entities in IFC_GROUPS.items():
        tk.Label(scroll, text=group_name, font=("Segoe UI", 10, "bold"), anchor="w").pack(
            fill="x", padx=8, pady=(10, 3)
        )
        for ent in entities:
            tk.Checkbutton(scroll, text=ent, variable=selected_entities[ent], anchor="w").pack(
                fill="x", padx=20
            )

    # Control buttons
    btns = tk.Frame(win)
    btns.pack(pady=10)

    def select_all():
        for v in selected_entities.values():
            v.set(True)

    def deselect_all():
        for v in selected_entities.values():
            v.set(False)

    tk.Button(btns, text="Выбрать все", command=select_all).pack(side="left", padx=5)
    tk.Button(btns, text="Снять все", command=deselect_all).pack(side="left", padx=5)

    def save_selection():
        chosen = [e for e, v in selected_entities.items() if v.get()]
        with open(ALLOWED_IFC_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(chosen), f, indent=2, ensure_ascii=False)
        messagebox.showinfo(
            "Сохранено",
            f"Выбрано {len(chosen)} типов IFC-сущностей",
        )
        win.destroy()

    tk.Button(win, text="Сохранить выбор", command=save_selection).pack(pady=10)

# =============================
# Main GUI
# =============================
menubar = tk.Menu(root)
settings_menu = tk.Menu(menubar, tearoff=0)
settings_menu.add_command(label="Выбор IFC сущностей...", command=open_ifc_selector)
menubar.add_cascade(label="Настройки", menu=settings_menu)
root.config(menu=menubar)

tk.Label(
    root,
    text="Конвертация .IFC файла в JSON для графовой БД и схемы IFC-графа",
).pack(pady=5)

select_button = tk.Button(root, text="Выбрать IFC файл", command=select_file)
select_button.pack(pady=5)

status_label = tk.Label(root, text="Файл не выбран", fg="gray")
status_label.pack(pady=5)

# path_label = tk.Label(
#     root, text="", fg="gray", wraplength=500, justify="center", anchor="center"
# )
# path_label.pack(padx=10, pady=5, fill="x")

output_button = tk.Button(root, text="Выбрать папку вывода", command=select_output_dir)
output_button.pack(pady=5)

output_label = tk.Label(root, text="Папка вывода не выбрана", fg="gray")
output_label.pack(pady=2)

# =============================
# Recursion depth control
# =============================
depth_label = tk.Label(root, text="Макс. глубина поиска при парсинге графа:")
depth_label.pack(pady=(10, 2))

recursion_depth_var = tk.StringVar(value="1")  # use StringVar to allow 'None'
depth_spin = tk.Spinbox(root, from_=0, to=10, width=3, textvariable=recursion_depth_var)
depth_spin.pack()

tk.Label(root, text="Введите целое число или 'None' (без кавычек) для бесконечной глубины.", fg="gray", font=("Segoe UI", 8)).pack()


start_button = tk.Button(root, text="Начать конвертацию", state=tk.DISABLED)
start_button.pack(pady=5)

root.mainloop()
