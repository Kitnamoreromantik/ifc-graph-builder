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
from ttkbootstrap.dialogs import Messagebox
from tkinter import filedialog, messagebox, Toplevel
from pathlib import Path
import threading
import logging
import json
import platform

# Import converter entry point directly
from src.main import run as run_ifc_converter

INTERFACE_LANG = "Eng" # "Rus"

# =============================
# Paths & Logging
# =============================
MAIN_SCRIPT = (Path(__file__).parent / "src" / "main.py").resolve()
ALLOWED_IFC_FILE = Path("allowed_ifc_types.json")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

# =============================
# IFC GROUPS
# =============================
if INTERFACE_LANG == 'Eng':
    IFC_GROUPS = {
        "Spatial structures": [
            "IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace",
            "IfcZone", "IfcRelAggregates", "IfcRelContainedInSpatialStructure", "IfcRelSpaceBoundary",
        ],
        "Construction elements": [
            "IfcWall", "IfcWallStandardCase", "IfcSlab", "IfcRoof", "IfcDoor", "IfcWindow",
            "IfcColumn", "IfcBeam", "IfcStair", "IfcRailing", "IfcOpeningElement",
            "IfcCovering", "IfcBuildingElementProxy", "IfcFurnishingElement",
            "IfcSystemFurnitureElement", "IfcDistributionElement", "IfcFlowTerminal",
            "IfcBuildingElement",
        ],
        "Quantity and properties": [
            "IfcElementQuantity", "IfcQuantityArea", "IfcQuantityVolume", "IfcQuantityLength",
            "IfcRelDefinesByProperties", "IfcRelDefinesByType",
        ],
        "Materials and classifications": [
            "IfcMaterial", "IfcMaterialLayer", "IfcMaterialLayerSet", "IfcMaterialConstituentSet",
            "IfcRelAssociatesMaterial", "IfcRelAssociatesClassification", "IfcClassificationReference",
        ],
        "Geometry": [
            "IfcProductDefinitionShape", "IfcShapeRepresentation", "IfcLocalPlacement",
            "IfcAxis2Placement3D", "IfcDirection", "IfcCartesianPoint",
        ],
    }
else:
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
root.geometry("900x500")
root.resizable(True, True)

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
        summary = run_ifc_converter(Path(ifc_path), Path(output_dir_path) if output_dir_path else None, depth)

        # Show log info in popup (shortened)
        # short_summary = "\n".join(summary.splitlines()[:10])  # first few lines only
        short_summary = summary
        # notify_ui(
        #     messagebox.showinfo,
        #     "Success",
        #     f"Конвертация завершена!\n\n{short_summary}\n\nПолный отчёт: conversion_summary.txt"
        # )

        notify_ui(
            lambda: Messagebox.show_info(
                message=summary,
                title="Success",
                alert=True,
                width=700
            )
        )

        notify_ui(status_label.config, text="Готово ✅" if INTERFACE_LANG == "Rus" else "Ready ✅", foreground="green")
    except Exception as e:
        logging.exception(e)
        notify_ui(messagebox.showerror, "Error", str(e))
        notify_ui(status_label.config, text="Ошибка ❌" if INTERFACE_LANG == "Rus" else "Error ❌", foreground="red")
    finally:
        notify_ui(start_button.config, state=NORMAL)

def select_file():
    file_path = filedialog.askopenfilename(title="Выбрать IFC файл" if INTERFACE_LANG == "Rus" else "Select IFC file", filetypes=[("IFC files", "*.ifc"), ("All files", "*.*")])
    if file_path:
        status_label.config(text=f"Файл выбран: {file_path}", foreground="green")
        start_button.config(state=NORMAL)
        start_button.configure(command=lambda: start_conversion(file_path))

def select_output_dir():
    global output_dir_path
    output_dir = filedialog.askdirectory(title="Выбрать папку для сохранения результатов" if INTERFACE_LANG == "Rus" else "Select output folder")
    if output_dir:
        output_dir_path = output_dir
        output_label.config(text=f"Папка вывода: {output_dir}" if INTERFACE_LANG == "Rus" else f"Output folder: {output_dir}", foreground="green")

def start_conversion(ifc_path):
    start_button.config(state=DISABLED)
    status_label.config(text="В процессе..." if INTERFACE_LANG == "Rus" else "In progress...", foreground="#E67E22")
    threading.Thread(target=run_conversion, args=(ifc_path,), daemon=True).start()

# =============================
# IFC Entity Selection Window
# =============================
def open_ifc_selector():
    win = ttk.Toplevel(root)
    if INTERFACE_LANG == 'Rus':
        win.title("Выбор сущностей для включения в граф")
    else:
        win.title("Select IFC entities to include into the graph")
    win.geometry("550x950")
    win.resizable(True, True)

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
        text="Выбрать все" if INTERFACE_LANG == 'Rus' else "Select all",
        bootstyle="success-outline",
        command=lambda: [v.set(True) for v in selected_entities.values()]
    ).pack(side="left", padx=5)

    ttk.Button(
        btn_frame,
        text="Снять все" if INTERFACE_LANG == 'Rus' else "Deselect all",
        bootstyle="secondary-outline",
        command=lambda: [v.set(False) for v in selected_entities.values()]
    ).pack(side="left", padx=5)

    # ↓ slightly raised and same green tone
    ttk.Button(
        btn_frame,
        text="Сохранить выбор" if INTERFACE_LANG == 'Rus' else "Save choice",
        bootstyle="success",     # green solid style
        command=lambda: save_selection(win)
    ).pack(side="left", padx=10)

    def save_selection(win):
        chosen = [e for e, v in selected_entities.items() if v.get()]
        with open(ALLOWED_IFC_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(chosen), f, indent=2, ensure_ascii=False)

        if INTERFACE_LANG == 'Rus': 
            messagebox.showinfo("Сохранено", f"Выбрано {len(chosen)} типов IFC-сущностей")
        else:
            messagebox.showinfo("Saved", f"Selected {len(chosen)} types of IFC-entities")
        win.destroy()

# =============================
# Main GUI Layout
# =============================
menubar = ttk.Menu(root)
settings_menu = ttk.Menu(menubar, tearoff=0)
settings_menu.add_command(label="Выбор IFC сущностей..." if INTERFACE_LANG == 'Rus' else "Select IFC entities...", command=open_ifc_selector)
menubar.add_cascade(label="Настройки" if INTERFACE_LANG == 'Rus' else "Configs", menu=settings_menu)
help_menu = ttk.Menu(menubar, tearoff=0)

def show_instructions():
    if INTERFACE_LANG == 'Rus':
        instructions = (
            "1. Нажмите «Выбрать IFC файл» и укажите исходный файл *.ifc (IFC4)\n"
            "2. Укажите папку вывода результатов\n"
            "3. При необходимости откройте «Настройки» → «Выбор IFC сущностей» \n(Для фильтрации ненужных типов. Список предварительный.)\n"
            "4. Установите глубину поиска n (в граф будут включены соседи сущностей n-го порядка)\n"
            "5. Нажмите «Начать конвертацию» и дождитесь завершения\n\n"
            "Результаты, которые сохранятся в выбранной целевой папке:\n"
            "   • conversion_summary.txt — статистика конвертации.\n"
            "   • nodes.json — список узлов IFC-графа\n"
            "   • edges.json — список связей между узлами\n"
            "   • graph_ifc.json — объединенный граф (nodes + edges)\n"
            "   • ifc_graph.html — HTML-визуализация графа (для визуальной инспекции)\n"
            "   • ifc_nodes_schema_llm.txt — структура свойств узлов (для LLM-анализа)\n"
            "   • ifc_relationships_schema_llm.txt — структура отношений (для LLM-анализа)\n\n"
            " Если в графе более 500 узлов, визуализация ifc_graph.html не создается\n"
            " graph_ifc.json — предназначен для загрузки в Memgraph/Neo4j и дальнейшего анализа\n"
            " В качестве тестовых данных можно использовать SampleHouse4.ifc файл (одноэтажный дом)"
        )
    else:
        instructions = (
        "1. Click “Select IFC file” and choose the source .ifc file (IFC4)\n"
        "2. Specify the output folder\n"
        "3. If needed, open “Settings” → “Select IFC entities”\n"
        "   (for filtering unnecessary types. The list is preliminary.)\n"
        "4. Set the search depth n (neighbors of n-th order will be included into the graph)\n"
        "5. Click “Start conversion” and wait until it completes\n\n"
        "The results saved into the selected output folder:\n"
        "  • conversion_summary.txt — conversion statistics\n"
        "  • nodes.json — list of IFC-graph nodes\n"
        "  • edges.json — list of relationships between nodes\n"
        "  • graph_ifc.json — combined graph (nodes + edges)\n"
        "  • ifc_graph.html — HTML visualization of the graph (for inspection)\n"
        "  • ifc_nodes_schema_llm.txt — node schema (for LLM analysis)\n"
        "  • ifc_relationships_schema_llm.txt — relationship schema (for LLM analysis)\n\n"
        "If the graph contains more than 500 nodes, ifc_graph.html is not generated\n"
        "graph_ifc.json is intended for loading into Memgraph/Neo4j for further analysis\n"
        "As sample data, you may use SampleHouse4.ifc (single-story house)\n"
    )

    # Use ttkbootstrap Messagebox (auto-themed)
    from ttkbootstrap.dialogs import Messagebox
    Messagebox.show_info(
        title="Инструкция" if INTERFACE_LANG == 'Rus' else "Instructions",
        message=instructions,
        width=900,
        alert=False
    )

help_menu.add_command(label="Показать инструкцию" if INTERFACE_LANG == 'Rus' else "Show instructions", command=show_instructions)
menubar.add_cascade(label="Инструкция"  if INTERFACE_LANG == 'Rus' else "Instructions", menu=help_menu)

root.config(menu=menubar)

ttk.Label(root, text="Конвертация IFC файла в JSON для графовой БД и схемы IFC-графа" if INTERFACE_LANG == 'Rus' else "Converting IFC to JSON for Graph DBs (Memgraph/Neo4j)", font=("Segoe UI", 10, "bold")).pack(pady=6)

select_button = ttk.Button(root, text="Выбрать IFC файл" if INTERFACE_LANG == 'Rus' else "Select IFC file", bootstyle="primary", command=select_file)
select_button.pack(pady=5)

status_label = ttk.Label(root, text="Файл не выбран" if INTERFACE_LANG == 'Rus' else "File is not selected", foreground="gray")
status_label.pack(pady=5)

output_button = ttk.Button(root, text="Выбрать папку вывода" if INTERFACE_LANG == 'Rus' else "Select output folder", bootstyle="info", command=select_output_dir)
output_button.pack(pady=5)

output_label = ttk.Label(root, text="Папка вывода не выбрана" if INTERFACE_LANG == 'Rus' else "Output folder is not selected", foreground="gray")
output_label.pack(pady=2)

depth_label = ttk.Label(root, text="Макс. глубина поиска при парсинге графа:" if INTERFACE_LANG == 'Rus' else "Max IFC parsing depth:")
depth_label.pack(pady=(10, 2))

depth_spin = ttk.Spinbox(root, from_=0, to=10, width=5, textvariable=recursion_depth_var, bootstyle="info")
depth_spin.pack(pady=(0, 5))

ttk.Label(root, text="Введите целое число или 'None' (без кавычек) для бесконечной глубины." if INTERFACE_LANG == 'Rus' else "Input integer or 'None' for infinite depth.", font=("Segoe UI", 8), foreground="gray").pack(pady=(0, 4))

start_button = ttk.Button(root, text="Начать конвертацию" if INTERFACE_LANG == 'Rus' else "Start convertation", state=DISABLED, bootstyle="success")
start_button.pack(pady=5)

root.mainloop()
