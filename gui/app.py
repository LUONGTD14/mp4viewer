import os
import tkinter as tk
from tkinter import ttk, filedialog
from typing import List, Dict, Tuple, Optional

from core.parser import parse_file
from core.models import Box, ContainerBox

# Theme Colors (Light Theme)
BG_PRIMARY = "#f4f5f6"      # Very light gray / off-white background
BG_SECONDARY = "#ffffff"    # Pure white for main panels, tree, and inputs
BG_TERTIARY = "#e4e5e6"     # Slightly darker gray for hover, selected rows
TEXT_PRIMARY = "#1e1e2e"    # Dark charcoal for primary text
TEXT_SECONDARY = "#4c4f69"  # Medium gray for labels and details
TEXT_MUTED = "#9ca0b0"      # Light muted gray for borders and placeholders
ACCENT_BLUE = "#1e66f5"     # Vibrant blue for accents/titles/headers
ACCENT_MAUVE = "#8839ef"    # Mauve accent
COLOR_RED = "#d20f39"       # Bright red for errors
COLOR_GREEN = "#40a02b"     # Green for success
COLOR_YELLOW = "#df8e1d"    # Yellow for alerts

class MP4ViewerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Aura MP4 & MOV Box Viewer")
        self.root.configure(bg=BG_PRIMARY)
        
        # Set full screen width and height coordinates first
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.root.geometry(f"{screen_w}x{screen_h}+0+0")
        
        # Trigger native maximized state
        try:
            self.root.state("zoomed")
        except Exception:
            try:
                self.root.wm_attributes("-zoomed", True)
            except Exception:
                pass
        
        # State variables
        self.current_filepath: Optional[str] = None
        self.current_filesize: int = 0
        self.root_boxes: List[Box] = []
        self.tree_item_to_box: Dict[str, Box] = {}
        self.box_to_tree_item: Dict[Box, str] = {}
        self.layout_segments: List[Tuple[int, int, str]] = [] # list of (x_start, x_end, tree_item_id)
        self.hex_edit_mode = False
        self.current_inspected_box: Optional[Box] = None
        
        # Initialize UI Components
        self.setup_styles()
        self.build_ui()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        # Configure standard ttk widget styles for Dark Mode
        style.configure(".", background=BG_PRIMARY, foreground=TEXT_PRIMARY, font=("Outfit", 10))
        style.configure("TFrame", background=BG_PRIMARY)
        
        # Button
        style.configure("TButton", 
                        background=BG_SECONDARY, 
                        foreground=TEXT_PRIMARY, 
                        borderwidth=1, 
                        bordercolor=TEXT_MUTED,
                        padding=6, 
                        relief="flat")
        style.map("TButton",
                  background=[("active", ACCENT_BLUE), ("pressed", BG_TERTIARY)],
                  foreground=[("active", "white")])
                  
        # Label
        style.configure("TLabel", background=BG_PRIMARY, foreground=TEXT_PRIMARY)
        style.configure("Title.TLabel", font=("Outfit", 15, "bold"), foreground=ACCENT_BLUE)
        style.configure("Status.TLabel", font=("Outfit", 10, "italic"), foreground=TEXT_SECONDARY)
        
        # Treeview
        style.configure("Treeview", 
                        background=BG_SECONDARY, 
                        fieldbackground=BG_SECONDARY, 
                        foreground=TEXT_PRIMARY, 
                        rowheight=24,
                        font=("Outfit", 10),
                        borderwidth=0)
        style.map("Treeview", 
                  background=[("selected", BG_TERTIARY)], 
                  foreground=[("selected", ACCENT_BLUE)])
                  
        style.configure("Treeview.Heading", 
                        background=BG_PRIMARY, 
                        foreground=TEXT_PRIMARY, 
                        font=("Outfit", 10, "bold"),
                        borderwidth=1,
                        bordercolor=BG_TERTIARY)
                        
        # PanedWindow
        style.configure("Heading.TLabel", font=("Outfit", 11, "bold"), foreground=ACCENT_BLUE)

    def build_ui(self):
        # 1. Top Panel: Title and File loading
        top_frame = ttk.Frame(self.root, padding=12)
        top_frame.pack(fill=tk.X, side=tk.TOP)
        
        # Title and Tagline
        title_sub_frame = ttk.Frame(top_frame)
        title_sub_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        title_lbl = ttk.Label(title_sub_frame, text="Aura MP4 & MOV Visualizer", style="Title.TLabel")
        title_lbl.pack(anchor=tk.W)
        
        self.status_lbl = ttk.Label(title_sub_frame, text="Chờ mở tệp tin...", style="Status.TLabel")
        self.status_lbl.pack(anchor=tk.W)
        
        # Actions Sub Frame
        actions_frame = ttk.Frame(top_frame)
        actions_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.file_path_lbl = ttk.Label(actions_frame, text="Chưa chọn file", font=("Outfit", 10), foreground=TEXT_SECONDARY, wraplength=400)
        self.file_path_lbl.pack(side=tk.LEFT, padx=15)
        
        open_btn = ttk.Button(actions_frame, text="Mở tệp MP4/MOV", command=self.open_file)
        open_btn.pack(side=tk.RIGHT)
        
        self.save_btn = ttk.Button(actions_frame, text="Lưu thành tệp mới", command=self.save_file, state=tk.DISABLED)
        self.save_btn.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Divider
        divider = ttk.Separator(self.root, orient="horizontal")
        divider.pack(fill=tk.X, padx=12, pady=2)
        
        # 2. Main Body Paned Window (Left Tree, Right Info)
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)
        
        # 2a. Left Frame: Tree View
        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=1)
        
        tree_header_frame = ttk.Frame(left_frame)
        tree_header_frame.pack(fill=tk.X, pady=(0, 6))
        
        tree_title = ttk.Label(tree_header_frame, text="Cấu trúc Box (Hierarchy)", style="Heading.TLabel")
        tree_title.pack(side=tk.LEFT)
        
        # Tree scrollbar & Widget
        tree_scroll = ttk.Scrollbar(left_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree = ttk.Treeview(left_frame, columns=("size"), yscrollcommand=tree_scroll.set, show="tree headings")
        self.tree.heading("#0", text="Box / Atom Name", anchor=tk.W)
        self.tree.heading("size", text="Kích thước (Bytes)", anchor=tk.W)
        self.tree.column("#0", stretch=True, width=220)
        self.tree.column("size", stretch=False, width=120)
        self.tree.pack(fill=tk.BOTH, expand=True)
        tree_scroll.config(command=self.tree.yview)
        
        # Select binding
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        
        # 2b. Right Frame: Split into Inspector and Hex view
        right_pane = ttk.PanedWindow(main_pane, orient=tk.VERTICAL)
        main_pane.add(right_pane, weight=2)
        
        # Inspector panel
        inspector_frame = ttk.Frame(right_pane)
        right_pane.add(inspector_frame, weight=1)
        
        ins_lbl = ttk.Label(inspector_frame, text="Box Inspector (Chi tiết)", style="Heading.TLabel")
        ins_lbl.pack(anchor=tk.W, pady=(0, 6))
        
        ins_scroll = ttk.Scrollbar(inspector_frame)
        ins_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.inspector_text = tk.Text(inspector_frame, 
                                      bg=BG_SECONDARY, 
                                      fg=TEXT_PRIMARY, 
                                      insertbackground=TEXT_PRIMARY,
                                      selectbackground="#e2e8f0",
                                      selectforeground=TEXT_PRIMARY,
                                      wrap=tk.WORD, 
                                      yscrollcommand=ins_scroll.set,
                                      font=("Outfit", 10),
                                      bd=0, 
                                      padx=10, 
                                      pady=10)
        self.inspector_text.pack(fill=tk.BOTH, expand=True)
        ins_scroll.config(command=self.inspector_text.yview)
        
        # Configure formatting tags for inspector text
        self.inspector_text.tag_configure("header", font=("Outfit", 11, "bold"), foreground=ACCENT_BLUE)
        self.inspector_text.tag_configure("key", font=("Outfit", 10, "bold"), foreground=ACCENT_MAUVE)
        self.inspector_text.tag_configure("val", font=("Space Mono", 10), foreground=COLOR_GREEN)
        self.inspector_text.tag_configure("error", font=("Outfit", 10, "italic"), foreground=COLOR_RED)
        
        # Hex viewer panel
        hex_frame = ttk.Frame(right_pane)
        right_pane.add(hex_frame, weight=1)
        
        hex_header_frame = ttk.Frame(hex_frame)
        hex_header_frame.pack(fill=tk.X, pady=(6, 6))
        
        hex_lbl = ttk.Label(hex_header_frame, text="Hex Preview (Payload)", style="Heading.TLabel")
        hex_lbl.pack(side=tk.LEFT)
        
        self.edit_hex_btn = ttk.Button(hex_header_frame, text="✏️ Sửa Hex Payload", command=self.toggle_hex_edit_mode, state=tk.DISABLED)
        self.edit_hex_btn.pack(side=tk.RIGHT)
        
        hex_scroll = ttk.Scrollbar(hex_frame)
        hex_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.hex_text = tk.Text(hex_frame, 
                                bg=BG_TERTIARY, 
                                fg=TEXT_PRIMARY, 
                                selectbackground="#e2e8f0",
                                selectforeground=TEXT_PRIMARY,
                                wrap=tk.NONE, 
                                yscrollcommand=hex_scroll.set,
                                font=("Space Mono", 10),
                                bd=0, 
                                padx=10, 
                                pady=10)
        self.hex_text.pack(fill=tk.BOTH, expand=True)
        hex_scroll.config(command=self.hex_text.yview)
        
        # Configure formatting tags for hex text
        self.hex_text.tag_configure("offset", foreground=ACCENT_BLUE)
        self.hex_text.tag_configure("hex", foreground=TEXT_PRIMARY)
        self.hex_text.tag_configure("ascii", foreground=COLOR_GREEN)
        
        # 3. Bottom Panel: Canvas Visual Map
        bottom_frame = ttk.Frame(self.root, padding=10)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=12, pady=(0, 10))
        
        map_lbl = ttk.Label(bottom_frame, text="Sơ đồ phân bổ dung lượng file (Root-Level Boxes) - Click để chọn box", style="Heading.TLabel")
        map_lbl.pack(anchor=tk.W, pady=(0, 4))
        
        self.canvas = tk.Canvas(bottom_frame, height=45, bg=BG_TERTIARY, highlightthickness=1, highlightbackground=BG_SECONDARY)
        self.canvas.pack(fill=tk.X, expand=True)
        self.canvas.bind("<Configure>", self.draw_layout_map)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

    def open_file(self):
        filetypes = (
            ("Video Files", "*.mp4 *.mov *.m4a *.mkv *.webm"),
            ("All Files", "*.*")
        )
        filepath = filedialog.askopenfilename(title="Chọn tệp tin Media (MP4/MOV/MKV/WebM)", filetypes=filetypes)
        if not filepath:
            return
            
        self.current_filepath = filepath
        self.current_filesize = os.path.getsize(filepath)
        self.file_path_lbl.config(text=os.path.basename(filepath))
        self.status_lbl.config(text="Đang phân tích tệp tin nhị phân...")
        self.root.update_idletasks()
        
        try:
            # Parse structure
            self.root_boxes = parse_file(filepath)
            
            # Clear UI states
            self.tree_item_to_box.clear()
            self.box_to_tree_item.clear()
            
            # Clear treeview items
            for item in self.tree.get_children():
                self.tree.delete(item)
                
            # Populate treeview
            for i, box in enumerate(self.root_boxes):
                self.insert_box_to_tree(box, "", f"node-{i}")
                
            # Perform web optimization heuristic check
            self.check_web_optimization()
            
            # Redraw layout map
            self.draw_layout_map()
            
            # Reset inspectors
            self.clear_inspectors()
            
            # Enable save button
            self.save_btn.config(state=tk.NORMAL)
            
        except Exception as e:
            self.status_lbl.config(text=f"Lỗi: {str(e)}", foreground=COLOR_RED)
            self.file_path_lbl.config(text="Phân tích thất bại")
            self.save_btn.config(state=tk.DISABLED)

    def insert_box_to_tree(self, box: Box, parent_item: str, item_id: str):
        # Determine container or leaf text
        has_children = hasattr(box, "children") and bool(box.children)
        icon = "📁 " if (isinstance(box, ContainerBox) or has_children) else "📄 "
        type_hex = box.type_bytes.hex().upper()
        display_name = f"{icon}{box.type_str} [0x{type_hex}]"
        
        # Add to Treeview
        item = self.tree.insert(parent_item, "end", iid=item_id, text=display_name, values=(f"{box.size:,}"))
        
        self.tree_item_to_box[item] = box
        self.box_to_tree_item[box] = item
        
        # Recursively insert children if box has children
        if has_children:
            for c_idx, child in enumerate(box.children):
                self.insert_box_to_tree(child, item, f"{item_id}-{c_idx}")

    def check_web_optimization(self):
        moov_idx = -1
        mdat_idx = -1
        
        for i, box in enumerate(self.root_boxes):
            if box.type_str == "moov":
                moov_idx = i
            if box.type_str == "mdat":
                mdat_idx = i
                
        if self.root_boxes and hasattr(self.root_boxes[0], "element_id"):
            doc_type = "EBML"
            for el in self.root_boxes:
                if el.name == "EBML":
                    for child in el.children:
                        if child.name == "DocType":
                            doc_type = str(child.fields.get("DocType", "EBML")).upper()
            self.status_lbl.config(text=f"Phân tích hoàn tất: Định dạng {doc_type}", foreground=COLOR_GREEN)
            return

        if moov_idx != -1 and mdat_idx != -1:
            if moov_idx < mdat_idx:
                status_text = "Phân tích hoàn tất: Web Optimized (Fast Start)"
                self.status_lbl.config(text=status_text, foreground=COLOR_GREEN)
            else:
                status_text = "Phân tích hoàn tất: Not Web Optimized (moov đặt sau mdat)"
                self.status_lbl.config(text=status_text, foreground=COLOR_YELLOW)
        else:
            self.status_lbl.config(text="Phân tích hoàn tất", foreground=COLOR_GREEN)

    def clear_inspectors(self):
        self.inspector_text.config(state=tk.NORMAL)
        self.inspector_text.delete("1.0", tk.END)
        self.inspector_text.insert(tk.END, "Chọn một box trong cây cấu trúc để xem chi tiết thông số metadata.", "error")
        self.inspector_text.config(state=tk.DISABLED)
        
        self.hex_text.config(state=tk.NORMAL)
        self.hex_text.delete("1.0", tk.END)
        self.hex_text.insert(tk.END, "Dữ liệu Hex payload sẽ hiển thị tại đây.")
        self.hex_text.config(state=tk.DISABLED)

    def on_tree_select(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            return
            
        item_id = selected_items[0]
        box = self.tree_item_to_box.get(item_id)
        if not box:
            return
            
        # Reset edit mode
        self.hex_edit_mode = False
        self.edit_hex_btn.config(text="✏️ Sửa Hex Payload")
        if box.payload_size > 0:
            self.edit_hex_btn.config(state=tk.NORMAL)
        else:
            self.edit_hex_btn.config(state=tk.DISABLED)
            
        self.current_inspected_box = box
        self.inspect_box(box)
        self.load_hex_preview(box)

    def inspect_box(self, box: Box):
        self.inspector_text.config(state=tk.NORMAL)
        self.inspector_text.delete("1.0", tk.END)
        
        # General Fields
        file_pct = (box.size / self.current_filesize) * 100 if self.current_filesize > 0 else 0
        type_hex = box.type_bytes.hex().upper()
        
        self.inspector_text.insert(tk.END, f"BOX: {box.type_str} [0x{type_hex}]\n", "header")
        self.inspector_text.insert(tk.END, "========================================\n\n")
        
        self.inspector_text.insert(tk.END, "Kích thước (Size): ", "key")
        self.inspector_text.insert(tk.END, f"{box.size:,} Bytes (0x{box.size:X})\n", "val")
        
        self.inspector_text.insert(tk.END, "Byte Offset: ", "key")
        self.inspector_text.insert(tk.END, f"0x{box.offset:08X} ({box.offset})\n", "val")
        
        self.inspector_text.insert(tk.END, "Payload Offset: ", "key")
        self.inspector_text.insert(tk.END, f"0x{box.payload_offset:08X}\n", "val")
        
        self.inspector_text.insert(tk.END, "Dung lượng Payload: ", "key")
        self.inspector_text.insert(tk.END, f"{box.payload_size:,} Bytes (0x{box.payload_size:X})\n", "val")
        
        self.inspector_text.insert(tk.END, "Phần trăm dung lượng file: ", "key")
        self.inspector_text.insert(tk.END, f"{file_pct:.4f} %\n", "val")
        
        if box.uuid:
            self.inspector_text.insert(tk.END, "Custom UUID: ", "key")
            self.inspector_text.insert(tk.END, f"{box.uuid.hex().upper()}\n", "val")
            
        self.inspector_text.insert(tk.END, "\n")
        
        # Specific Box fields
        if box.fields:
            self.inspector_text.insert(tk.END, "CẤU TRÚC METADATA / FIELDS:\n", "header")
            self.inspector_text.insert(tk.END, "----------------------------------------\n")
            
            for k, v in box.fields.items():
                friendly_k = k.replace("_", " ").title()
                
                # Check if this field is editable
                if k in box.editable_fields:
                    self.inspector_text.insert(tk.END, f"  ✏️ {friendly_k}: ", "key")
                    
                    # Create Entry and Hex Label
                    entry = ttk.Entry(self.inspector_text, width=15, font=("Space Mono", 10))
                    entry.insert(0, str(box.editable_fields[k]["value"]))
                    
                    hex_lbl = ttk.Label(self.inspector_text, text="", font=("Space Mono", 9), background=BG_SECONDARY)
                    
                    # Bind edit event
                    entry.bind("<KeyRelease>", lambda e, b=box, fn=k, ent=entry, lbl=hex_lbl: self.on_field_edited(b, fn, ent, lbl))
                    entry.bind("<FocusOut>", lambda e, b=box, fn=k, ent=entry, lbl=hex_lbl: self.on_field_edited(b, fn, ent, lbl))
                    
                    # Embed widgets
                    self.inspector_text.window_create(tk.END, window=entry)
                    self.inspector_text.window_create(tk.END, window=hex_lbl)
                    self.inspector_text.insert(tk.END, "\n")
                    
                    # Initial hex label update
                    self.on_field_edited(box, k, entry, hex_lbl)
                else:
                    self.inspector_text.insert(tk.END, f"  {friendly_k}: ", "key")
                    
                    # Format value
                    if isinstance(v, int) and not isinstance(v, bool):
                        v_str = f"{v:,} (0x{v:X})"
                    elif isinstance(v, list):
                        formatted_list = []
                        for item in v:
                            if isinstance(item, int):
                                formatted_list.append(f"{item:,} (0x{item:X})")
                            else:
                                formatted_list.append(item)
                        v_str = str(formatted_list)
                    elif isinstance(v, dict):
                        formatted_dict = {}
                        for dk, dv in v.items():
                            if isinstance(dv, int) and not isinstance(dv, bool):
                                formatted_dict[dk] = f"{dv:,} (0x{dv:X})"
                            else:
                                formatted_dict[dk] = dv
                        import json
                        v_str = json.dumps(formatted_dict, indent=4)
                    else:
                        v_str = str(v)
                        
                    self.inspector_text.insert(tk.END, f"{v_str}\n", "val")
        else:
            self.inspector_text.insert(tk.END, "Không chứa thông số fields được phân tích đặc thù. Sử dụng Hex View để xem dữ liệu nhị phân thô.", "error")
            
        self.inspector_text.config(state=tk.DISABLED)

    def on_field_edited(self, box: Box, field_name: str, entry: ttk.Entry, hex_lbl: ttk.Label):
        val_str = entry.get().strip()
        field_info = box.editable_fields[field_name]
        t = field_info["type"]
        
        try:
            if not val_str:
                return
                
            # Parse and validate the value based on field type
            if t == "fixed16_16" or t == "fixed8_8":
                val = float(val_str)
            else:
                val = int(val_str, 0) # support hex (0x...) or dec
                
            # Update in-memory value
            field_info["value"] = val
            
            # Also update box.fields so it reflects in the parsed data
            box.fields[field_name] = val
            
            # Update the live hex label next to the entry
            if t == "fixed16_16":
                raw_hex = int(val * 65536) & 0xFFFFFFFF
                hex_lbl.config(text=f" (0x{raw_hex:08X})", foreground=COLOR_GREEN)
            elif t == "fixed8_8":
                raw_hex = int(val * 256) & 0xFFFF
                hex_lbl.config(text=f" (0x{raw_hex:04X})", foreground=COLOR_GREEN)
            elif t == "full_range_bit":
                hex_lbl.config(text=" (0x80)" if val else " (0x00)", foreground=COLOR_GREEN)
            else:
                # uint16, uint32, uint64, int16, int32
                mask = 0xFFFFFFFF
                if t in ("uint16", "int16"): mask = 0xFFFF
                elif t == "uint64": mask = 0xFFFFFFFFFFFFFFFF
                raw_hex = int(val) & mask
                hex_lbl.config(text=f" (0x{raw_hex:X})", foreground=COLOR_GREEN)
                
            # Redraw canvas layout if track_id or width/height changed in root moov box
            if field_name in ("track_id", "width", "height") and box.type_str in ("mvhd", "tkhd"):
                self.draw_layout_map(None)
                
        except Exception:
            hex_lbl.config(text=" (Lỗi định dạng)", foreground=COLOR_RED)

    def save_file(self):
        if not self.current_filepath or not self.root_boxes:
            return
            
        filetypes = (
            ("Video Files", "*.mp4 *.mov *.m4a *.mkv *.webm"),
            ("All Files", "*.*")
        )
        save_path = filedialog.asksaveasfilename(
            title="Lưu tệp tin mới với các chỉnh sửa",
            filetypes=filetypes,
            defaultextension=os.path.splitext(self.current_filepath)[1],
            initialfile="edited_" + os.path.basename(self.current_filepath)
        )
        if not save_path:
            return
            
        self.status_lbl.config(text="Đang áp dụng thay đổi và lưu tệp tin...", foreground=ACCENT_BLUE)
        self.root.update_idletasks()
        
        try:
            from core.writer import save_modified_file
            save_modified_file(save_path, self.current_filepath, self.root_boxes)
            self.status_lbl.config(text=f"Đã lưu tệp tin mới thành công tại: {os.path.basename(save_path)}", foreground=COLOR_GREEN)
        except Exception as e:
            self.status_lbl.config(text=f"Lỗi khi lưu tệp tin: {str(e)}", foreground=COLOR_RED)

    def load_hex_preview(self, box: Box):
        self.hex_text.config(state=tk.NORMAL)
        self.hex_text.delete("1.0", tk.END)
        
        if box.payload_size <= 0:
            self.hex_text.insert(tk.END, "Box này không chứa payload dữ liệu.")
            self.hex_text.config(state=tk.DISABLED)
            return
            
        # Read payload slice
        read_size = min(box.payload_size, 256)
        try:
            if hasattr(box, "custom_payload_bytes") and box.custom_payload_bytes is not None:
                data = box.custom_payload_bytes[:read_size]
            else:
                with open(self.current_filepath, "rb") as f:
                    f.seek(box.payload_offset)
                    data = f.read(read_size)
                
            self.hex_text.insert(tk.END, f"Hiển thị {read_size} byte đầu của payload (Tổng size: {box.payload_size:,} bytes):\n\n")
            
            for i in range(0, len(data), 16):
                chunk = data[i:i+16]
                
                # Offset part
                offset_str = f"0x{box.payload_offset + i:08X}  "
                self.hex_text.insert(tk.END, offset_str, "offset")
                
                # Hex part
                hex_part = " ".join(f"{b:02X}" for b in chunk)
                if len(chunk) < 16:
                    hex_part += " " * (3 * (16 - len(chunk)))
                self.hex_text.insert(tk.END, hex_part + "  |  ", "hex")
                
                # ASCII part
                ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
                self.hex_text.insert(tk.END, ascii_part + "\n", "ascii")
                
        except Exception as e:
            self.hex_text.insert(tk.END, f"Lỗi đọc nhị phân: {str(e)}", "offset")
            
        self.hex_text.config(state=tk.DISABLED)

    def toggle_hex_edit_mode(self):
        box = self.current_inspected_box
        if not box or box.payload_size <= 0:
            return
            
        if not self.hex_edit_mode:
            # Entering Edit Mode
            self.hex_edit_mode = True
            self.edit_hex_btn.config(text="💾 Lưu Hex Payload (Áp dụng)")
            
            self.hex_text.config(state=tk.NORMAL)
            self.hex_text.delete("1.0", tk.END)
            
            # Get the payload bytes
            if hasattr(box, "custom_payload_bytes") and box.custom_payload_bytes is not None:
                payload_bytes = box.custom_payload_bytes
            else:
                try:
                    with open(self.current_filepath, "rb") as f:
                        f.seek(box.payload_offset)
                        payload_bytes = f.read(box.payload_size)
                except Exception:
                    payload_bytes = b""
                    
            # Render as space-separated hex bytes
            hex_spaced = " ".join(f"{b:02X}" for b in payload_bytes)
            self.hex_text.insert(tk.END, hex_spaced)
            
        else:
            # Saving the Hex bytes
            raw_text = self.hex_text.get("1.0", tk.END).strip().replace("\n", " ").replace("\r", " ")
            try:
                # Remove spaces and get clean hex string
                clean_hex = "".join(c for c in raw_text if c.isalnum())
                new_bytes = bytes.fromhex(clean_hex)
                
                # Verify size match
                if len(new_bytes) != box.payload_size:
                    raise ValueError(f"Kích thước dữ liệu Hex sửa đổi ({len(new_bytes)} bytes) không khớp với kích thước payload gốc ({box.payload_size} bytes).")
                    
                # Save in-memory
                box.custom_payload_bytes = new_bytes
                
                self.hex_edit_mode = False
                self.edit_hex_btn.config(text="✏️ Sửa Hex Payload")
                self.load_hex_preview(box) # reload formatted view
                self.status_lbl.config(text=f"Đã cập nhật dữ liệu Hex của box '{box.type_str}' thành công!", foreground=COLOR_GREEN)
                
            except Exception as e:
                import tkinter.messagebox as messagebox
                messagebox.showerror("Lỗi sửa Hex", str(e))

    def draw_layout_map(self, event=None):
        self.canvas.delete("all")
        self.layout_segments.clear()
        
        if not self.root_boxes or self.current_filesize <= 0:
            # Draw placeholder message
            self.canvas.create_text(
                self.canvas.winfo_width() / 2, 22, 
                text="Chưa có dữ liệu phân tích tệp tin.", 
                fill=TEXT_MUTED, font=("Outfit", 10)
            )
            return
            
        c_width = self.canvas.winfo_width()
        c_height = self.canvas.winfo_height()
        
        last_offset = 0
        
        # Color mapping helper
        def get_box_color(box_type: str) -> str:
            if box_type == "ftyp": return ACCENT_BLUE
            if box_type == "moov": return ACCENT_MAUVE
            if box_type == "mdat": return COLOR_RED
            if box_type in ("free", "skip"): return TEXT_MUTED
            return "#ccd0da" # Light gray for other boxes
            
        # Compile segments to draw
        segments = []
        for box in self.root_boxes:
            if box.offset > last_offset:
                # Gap segment
                gap_size = box.offset - last_offset
                segments.append({
                    "type": "gap",
                    "size": gap_size,
                    "offset": last_offset,
                    "tree_item": None
                })
            
            tree_item = self.box_to_tree_item.get(box)
            segments.append({
                "type": box.type_str,
                "size": box.size,
                "offset": box.offset,
                "tree_item": tree_item
            })
            last_offset = box.offset + box.size
            
        if last_offset < self.current_filesize:
            gap_size = self.current_filesize - last_offset
            segments.append({
                "type": "gap",
                "size": gap_size,
                "offset": last_offset,
                "tree_item": None
            })
            
        # Draw on Canvas
        x_cursor = 0
        for seg in segments:
            pct = seg["size"] / self.current_filesize
            seg_w = max(pct * c_width, 2.0) # at least 2 pixels wide
            
            x_start = x_cursor
            x_end = x_start + seg_w
            x_cursor = x_end
            
            # Save segment click area if associated with a tree node
            if seg["tree_item"]:
                self.layout_segments.append((int(x_start), int(x_end), seg["tree_item"]))
                
            color = get_box_color(seg["type"])
            # Draw segment block
            self.canvas.create_rectangle(
                x_start, 0, x_end, c_height, 
                fill=color, outline=BG_TERTIARY, width=1
            )
            
            # Draw text label inside segment if large enough (e.g. > 40px)
            if seg_w > 40:
                lbl = seg["type"] if seg["type"] != "gap" else ""
                self.canvas.create_text(
                    (x_start + x_end) / 2, c_height / 2, 
                    text=lbl, fill="white" if color in (ACCENT_BLUE, ACCENT_MAUVE, COLOR_RED) else TEXT_PRIMARY,
                    font=("Outfit", 9, "bold")
                )

    def on_canvas_click(self, event):
        click_x = event.x
        for x_start, x_end, item_id in self.layout_segments:
            if x_start <= click_x <= x_end:
                # Select the item in Treeview
                self.tree.selection_set(item_id)
                self.tree.see(item_id)
                break

def main():
    root = tk.Tk()
    app = MP4ViewerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
