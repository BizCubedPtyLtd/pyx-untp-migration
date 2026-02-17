import json
import os
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from PIL import Image, ImageTk

"""
Controls
Action	How
Draw hotspot	Left click + drag
Delete hotspot	Right click inside it
Undo	Ctrl + Z
Save JSON	Press S
Load existing JSON	Open same file name
"""

DOC_LOOKUP = {
    "DFR": {
        "title": "About DFR",
        "link": "https://docs.rbtp.pyx.io/docs/credential-overviews/digital-facility-record/"
    },
    "DPP": {
        "title": "About DPP",
        "link": "https://docs.rbtp.pyx.io/docs/credential-overviews/digital-product-passport/"
    },
    "DCC": {
        "title": "About DCC",
        "link": "https://docs.rbtp.pyx.io/docs/credential-overviews/digital-conformity-credential/"
    },
    "DTE": {
        "title": "About DTE",
        "link": "https://docs.rbtp.pyx.io/docs/credential-overviews/digital-traceability-event/"
    }
}


class VCMapEditor:
    
    def __init__(self, root):
        self.rectangles = {}   # rect_id -> area
        self.history = []      # ("add", rect_id)
        self.root = root
        self.root.title("VC Map Editor")

        self.image_path = filedialog.askopenfilename(title="Select VC Map Image")
        if not self.image_path:
            exit()

        self.json_path = filedialog.asksaveasfilename(
            title="Select / Create JSON file",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")]
        )

        self.img = Image.open(self.image_path)
        self.tk_img = ImageTk.PhotoImage(self.img)

        self.canvas = tk.Canvas(root, width=self.tk_img.width(), height=self.tk_img.height())
        self.canvas.pack()
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)

        self.start_x = None
        self.start_y = None
        self.rect = None

        self.areas = []
        self.history = []

        self.load_existing_json()
        self.draw_existing_areas()

        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<Button-3>", self.on_right_click)

        root.bind("<Control-z>", self.undo)
        root.bind("s", self.save_json)

    # ---------- Mouse Actions ----------
    def detect_credential_type(self, title: str):
        for key in DOC_LOOKUP.keys():
            if key in title.upper():
                return key
        return None

    def on_mouse_down(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, event.x, event.y,
            outline="red", width=2
        )

    def on_mouse_drag(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_mouse_up(self, event):
        x1, y1, x2, y2 = self.canvas.coords(self.rect)
        coords = f"{int(x1)},{int(y1)},{int(x2)},{int(y2)}"

        title = simpledialog.askstring("Input", "Hotspot title:")
        if not title:
            self.canvas.delete(self.rect)
            return

        #external_href = simpledialog.askstring("Input", "External href:")
        sample_credential = simpledialog.askstring("Input", "Sample credential:")

        cred_type = self.detect_credential_type(title)
        doc_info = DOC_LOOKUP.get(cred_type, {"title": "", "link": ""})

        area = {
            "alt": title,
            "title": title,
            "links": [
                {
                    "type": "internal",
                    "disabled": True,
                    "title": title,
                    "href": "",   # <-- always empty
                    "sample_credential": ""
                },
                {
                    "type": "external",
                    "disabled": False,
                    "title": title,
                    "href": "",
                    "sample_credential": sample_credential
                }
            ],
            "coords": coords,
            "shape": "rect",
            "documentation": {
                "title": doc_info["title"],
                "link": doc_info["link"]
            }
        }

        self.history.append(("add", area))
        self.areas.append(area)

    # ---------- Right Click Delete ----------

    def on_right_click(self, event):
        for area in self.areas:
            x1, y1, x2, y2 = map(int, area["coords"].split(","))
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.canvas.delete(area["_rect_id"])
                self.history.append(("delete", area))
                self.areas.remove(area)
                break

    # def on_right_click(self, event):
    #     # Find the rectangle closest to the click
    #     clicked = self.canvas.find_closest(event.x, event.y)[0]

    #     if clicked in self.rectangles:
    #         area = self.rectangles.pop(clicked)   # remove from mapping
    #         if area in self.areas:
    #             self.areas.remove(area)
    #         self.canvas.delete(clicked)
    #         self.history.append(("delete", clicked, area))


    # ---------- Undo ----------

    def undo(self, event=None):
        if not self.history:
            return

        action, area = self.history.pop()

        if action == "add":
            self.canvas.delete(area["_rect_id"])
            self.areas.remove(area)
        elif action == "delete":
            rect = self.canvas.create_rectangle(
                *map(int, area["coords"].split(",")),
                outline="red", width=2
            )
            area["_rect_id"] = rect
            self.areas.append(area)




    # ---------- JSON Handling ----------

    def load_existing_json(self):
        if not os.path.exists(self.json_path):
            return

        with open(self.json_path, "r") as f:
            data = json.load(f)
            for area in data.get("areas", []):
                self.areas.append(area)

    def draw_existing_areas(self):
        for area in self.areas:
            x1, y1, x2, y2 = map(int, area["coords"].split(","))
            rect = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                outline="blue", width=2
            )
            area["_rect_id"] = rect

    def save_json(self, event=None):
        output = {
            "img": "/" + os.path.basename(self.image_path),
            "title": "VC Map",
            "appConfigName": "VC Map",
            "areas": [
                {k: v for k, v in area.items() if not k.startswith("_")}
                for area in self.areas
            ]
        }

        with open(self.json_path, "w") as f:
            json.dump(output, f, indent=4)

        messagebox.showinfo("Saved", "JSON saved successfully!")

# ---------- Run ----------
root = tk.Tk()
app = VCMapEditor(root)
root.mainloop()
