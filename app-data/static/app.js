const mappingFile = document.getElementById("mappingFile");
const inputFile = document.getElementById("inputFile");
const mappingName = document.getElementById("mappingName");
const inputName = document.getElementById("inputName");
const transformBtn = document.getElementById("transformBtn");
const outputArea = document.getElementById("outputArea");
const downloadBtn = document.getElementById("downloadBtn");
const statusEl = document.getElementById("status");

const dropMapping = document.getElementById("dropMapping");
const dropInput = document.getElementById("dropInput");

function setStatus(msg, isError=false) {
  statusEl.textContent = msg || "";
  statusEl.style.color = isError ? "#b00020" : "#333";
}

function setDownload(url) {
  if (url) {
    downloadBtn.href = url;
    downloadBtn.classList.remove("disabled");
    downloadBtn.setAttribute("aria-disabled", "false");
  } else {
    downloadBtn.href = "#";
    downloadBtn.classList.add("disabled");
    downloadBtn.setAttribute("aria-disabled", "true");
  }
}

function wireFileInput(fileInput, nameEl) {
  fileInput.addEventListener("change", () => {
    nameEl.textContent = fileInput.files?.[0]?.name || "(no file)";
  });
}

wireFileInput(mappingFile, mappingName);
wireFileInput(inputFile, inputName);

function wireDropZone(zoneEl, fileInput, nameEl) {
  zoneEl.addEventListener("dragover", (e) => {
    e.preventDefault();
    zoneEl.classList.add("dragover");
  });

  zoneEl.addEventListener("dragleave", () => {
    zoneEl.classList.remove("dragover");
  });

  zoneEl.addEventListener("drop", (e) => {
    e.preventDefault();
    zoneEl.classList.remove("dragover");
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    const dt = new DataTransfer();
    dt.items.add(file);
    fileInput.files = dt.files;
    nameEl.textContent = file.name;
  });
}

wireDropZone(dropMapping, mappingFile, mappingName);
wireDropZone(dropInput, inputFile, inputName);

transformBtn.addEventListener("click", async () => {
  setStatus("");
  outputArea.value = "";
  setDownload(null);

  if (!mappingFile.files.length || !inputFile.files.length) {
    setStatus("Please upload both mapping.json and input.json.", true);
    return;
  }

  transformBtn.disabled = true;
  setStatus("Transforming...");

  try {
    const form = new FormData();
    form.append("mapping_file", mappingFile.files[0]);
    form.append("input_file", inputFile.files[0]);

    const res = await fetch("/transform", { method: "POST", body: form });
    const data = await res.json().catch(() => ({}));

    if (!res.ok || !data.ok) {
      setStatus(data.error || "Transform failed.", true);
      return;
    }

    outputArea.value = data.output_json || "";
    setDownload(data.download_url || null);
    setStatus("Done.");
  } catch (err) {
    setStatus("Unexpected error: " + err, true);
  } finally {
    transformBtn.disabled = false;
  }
});
