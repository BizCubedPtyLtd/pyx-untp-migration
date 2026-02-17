import cv2
import json
import os

# create new env
# cd map_picker_interactive_vc_map
# source venv/bin/activate
# python map_picker.py
# code created in collaboration with Karina, ChatGPT & Grok
# ────────────────────────────────────────────────
#  Configuration
# ────────────────────────────────────────────────

INPUT_FILE = input("Enter the image file name (with .jpg): ").strip()
BRAND_NAME = input("Enter the brand name: ").strip()

IMAGE_PATH = f"./images/{INPUT_FILE}"
OUTPUT_JSON = f"./output/{INPUT_FILE.replace('.jpg', '.json')}"

DOC_LOOKUP = {
    "DFR": {"title": "About DFR", "link": "https://docs.rbtp.pyx.io/docs/credential-overviews/digital-facility-record/"},
    "DPP": {"title": "About DPP", "link": "https://docs.rbtp.pyx.io/docs/credential-overviews/digital-product-passport/"},
    "DCC": {"title": "About DCC", "link": "https://docs.rbtp.pyx.io/docs/credential-overviews/digital-conformity-credential/"},
    "DTE": {"title": "About DTE", "link": "https://docs.rbtp.pyx.io/docs/credential-overviews/digital-traceability-event/"},
}

# ────────────────────────────────────────────────
#  Global state
# ────────────────────────────────────────────────

drawing = False
start_point = None
current_mode = "draw"   # draw / delete / modify

areas = []
img_original = None
img = None

main_json = {
    "img": f"/data/{INPUT_FILE}",
    "title": f"Interactive Value Chain Map - Collaborative Pilot - Scenario 1 ({BRAND_NAME})",
    "appConfigName": "",
    "areas": []
}

# ────────────────────────────────────────────────
def load_existing_json():
    global areas, main_json
    if os.path.exists(OUTPUT_JSON):
        try:
            with open(OUTPUT_JSON, 'r') as f:
                data = json.load(f)
                main_json.update(data)  # keep title/img etc
                areas = data.get("areas", [])
            print(f"→ Loaded {len(areas)} existing areas from {OUTPUT_JSON}")
        except Exception as e:
            print(f"Error loading JSON: {e}")
    else:
        print("→ No existing JSON found, starting fresh.")

def draw_all_rectangles():
    global img
    img = img_original.copy()
    for area in areas:
        try:
            x1, y1, x2, y2 = map(int, area["coords"].split(","))
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            # Optional: small label
            cv2.putText(img, area["title"][:12], (x1+5, y1+20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0,255,0), 1)
        except:
            pass

def point_in_rect(x, y, area):
    try:
        x1,y1,x2,y2 = map(int, area["coords"].split(","))
        return x1 <= x <= x2 and y1 <= y <= y2
    except:
        return False

def find_area_at_point(x, y):
    for i, area in enumerate(areas):
        if point_in_rect(x, y, area):
            return i, area
    return None, None

# ────────────────────────────────────────────────
def draw_rectangle(event, x, y, flags, param):
    global drawing, start_point, img, current_mode

    if current_mode == "draw":
        if event == cv2.EVENT_LBUTTONDOWN:
            drawing = True
            start_point = (x, y)

        elif event == cv2.EVENT_MOUSEMOVE and drawing:
            preview = img.copy()
            cv2.rectangle(preview, start_point, (x, y), (0, 200, 255), 2)
            cv2.imshow("Map Picker", preview)

        elif event == cv2.EVENT_LBUTTONUP:
            drawing = False
            if start_point == (x, y):
                return  # too small / click

            x1, y1 = min(start_point[0], x), min(start_point[1], y)
            x2, y2 = max(start_point[0], x), max(start_point[1], y)
            coords = f"{x1},{y1},{x2},{y2}"

            title = input("Title (e.g. always start with DFR, DPP, DCC, DTE): ").strip()
            sample_cred = input("Sample Credential URL: ").strip()

            prefix = title.split(" - ")[0].strip()
            doc_info = DOC_LOOKUP.get(prefix, {"title": "", "link": ""})

            area = {
                "alt": title,
                "title": title,
                "links": [{
                    "type": "external",
                    "disabled": False,
                    "title": title,
                    "href": "",
                    "sample_credential": sample_cred
                }],
                "coords": coords,
                "shape": "rect",
                "documentation": {
                    "title": doc_info["title"],
                    "link": doc_info["link"]
                }
            }

            areas.append(area)
            draw_all_rectangles()
            cv2.imshow("Map Picker", img)
            print(f"  Added → {title}")

    elif current_mode == "delete":
        if event == cv2.EVENT_LBUTTONDOWN:
            idx, area = find_area_at_point(x, y)
            if idx is not None:
                print(f"Deleting: {area['title']}")
                areas.pop(idx)
                draw_all_rectangles()
                cv2.imshow("Map Picker", img)

    elif current_mode == "modify":
        if event == cv2.EVENT_LBUTTONDOWN:
            idx, area = find_area_at_point(x, y)
            if idx is not None:
                print(f"\nModifying: {area['title']}")
                new_title = input(f"New title (enter to keep): ").strip() or area["title"]
                new_cred  = input(f"New sample credential (enter to keep): ").strip() or area["links"][0]["sample_credential"]

                if new_title != area["title"]:
                    area["title"] = new_title
                    area["alt"] = new_title
                    area["links"][0]["title"] = new_title

                    prefix = new_title.split(" - ")[0].strip()
                    doc = DOC_LOOKUP.get(prefix, {"title": "", "link": ""})
                    area["documentation"] = doc

                if new_cred:
                    area["links"][0]["sample_credential"] = new_cred

                draw_all_rectangles()
                cv2.imshow("Map Picker", img)
                print("  Updated.")

# ────────────────────────────────────────────────
def save_json():
    main_json["areas"] = areas
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(main_json, f, indent=2)
    print(f"\nSaved → {OUTPUT_JSON} ({len(areas)} areas)")

# ────────────────────────────────────────────────
#  MAIN
# ────────────────────────────────────────────────

if not os.path.exists(IMAGE_PATH):
    print(f"Image not found: {IMAGE_PATH}")
    exit(1)

img_original = cv2.imread(IMAGE_PATH)
if img_original is None:
    print("Failed to load image")
    exit(1)

load_existing_json()
draw_all_rectangles()

cv2.namedWindow("Map Picker")
cv2.imshow("Map Picker", img)
cv2.setMouseCallback("Map Picker", draw_rectangle)

print("""
Controls:
  Drag        → draw new rectangle (mode: draw)
  d           → delete mode (click inside rect to delete)
  m           → modify mode (click rect → edit title & credential)
  n           → back to normal draw mode
  u           → undo (remove last added rectangle)
  s           → save JSON
  q           → quit
""")

changed = len(areas) > 0

while True:
    key = cv2.waitKey(1) & 0xFF

    if key == ord('q'):
        if changed and areas:
            ans = input("Save changes before quitting? [Y/n] ").lower()
            if ans in ('', 'y', 'yes'):
                save_json()
        break

    elif key == ord('s'):
        save_json()
        changed = False

    elif key == ord('u'):
        if areas:
            removed = areas.pop()
            print(f"Undid: {removed.get('title','')}")
            draw_all_rectangles()
            cv2.imshow("Map Picker", img)
            changed = True
        else:
            print("Nothing to undo.")

    elif key == ord('d'):
        current_mode = "delete"
        print("→ Delete mode (click rectangle to remove)")

    elif key == ord('m'):
        current_mode = "modify"
        print("→ Modify mode (click rectangle to edit title & credential)")

    elif key == ord('n'):
        current_mode = "draw"
        print("→ Draw mode")

    # elif key == ord('r'):
    #     draw_all_rectangles()
    #     cv2.imshow("Map Picker", img)
    #     print("View refreshed")

cv2.destroyAllWindows()
print("Done.")