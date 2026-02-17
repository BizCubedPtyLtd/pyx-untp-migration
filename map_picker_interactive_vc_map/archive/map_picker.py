import cv2
import json
from tkinter import filedialog, simpledialog, messagebox

# create new env
# cd map_picker_interactive_vc_map
# source venv/bin/activate
# python map_picker.py
INPUT_FILE = input("Enter the path to the image file (with .jpg extension): ")
BRAND_NAME = input("Enter the brand name")
IMAGE_PATH = f"./images/{INPUT_FILE}"
OUTPUT_JSON = f"./output/{INPUT_FILE.replace('.jpg', '.json')}"

areas = []
drawing = False
start_point = None
img = cv2.imread(IMAGE_PATH)
clone = img.copy()


# create main .json
main_json = {
"img": f"/data/{INPUT_FILE}",
"title": f"Interactive Value Chain Map - Collaborative Pilot - Scenario 1 ({BRAND_NAME})",
"appConfigName": ""}

def draw_rectangle(event, x, y, flags, param):
    global drawing, start_point, img, preview_img

    
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

    # Mouse button pressed → start drawing
    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        start_point = (x, y)

    # Mouse moving → show live preview rectangle
    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        preview_img = img.copy()
        cv2.rectangle(preview_img, start_point, (x, y), (0, 255, 0), 2)
        cv2.imshow("Image", preview_img)

    # Mouse released → finalize rectangle
    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        end_point = (x, y)

        x1, y1 = start_point
        x2, y2 = end_point
        coords = f"{x1},{y1},{x2},{y2}"

        print(f"\nCoords: {coords}")

        title = input("Title: ")
        sample_credential = input("Sample Credential URL: ")

        # Determine documentation block based on prefix
        prefix = title.split(" - ")[0]  # e.g. "DTE" from "DTE - Trading Something"
        doc_info = DOC_LOOKUP.get(prefix, {
            "title": "",
            "link": ""
        })

        area = {
            "alt": title,
            "title": title,
            "links": [
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

        areas.append(area)
        
        # Draw final rectangle permanently on main image
        cv2.rectangle(img, start_point, end_point, (0, 255, 0), 2)
        cv2.imshow("Image", img)
        
def save_json():
    main_json["areas"] = areas
    with open(OUTPUT_JSON, "w") as f:
        json.dump(main_json, f, indent=4)
    print(f"\nSaved to {OUTPUT_JSON}")

cv2.imshow("Image", img)
cv2.setMouseCallback("Image", draw_rectangle)

print("Drag rectangles. Press 's' to save, 'q' to quit.")

while True:
    key = cv2.waitKey(1) & 0xFF

    if key == ord("s"):  # save JSON
        save_json()

    elif key == ord("u"):  # undo last rectangle
        if areas:
            areas.pop()
            img = clone.copy()  # reset image to original
            # redraw all remaining rectangles
            for area in areas:
                x1, y1, x2, y2 = map(int, area["coords"].split(","))
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.imshow("Image", img)
            print("Last rectangle undone.")
        else:
            print("No rectangle to undo.")

    elif key == ord("q"):  # quit
        break

cv2.destroyAllWindows()
