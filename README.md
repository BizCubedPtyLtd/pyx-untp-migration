# pyx-untp-migration

# 📘 Pyx UNTP Migration Tool

.....

## 📂 Folder Structure

....

# 🚀 Setup & Usage

1. Clone the repository /pyx-apps/ in Ubuntu 24.04
2. Install Python Extensions:
    - Python Debugger
    - Python
    - Pylance
    - Python Environment venv
    - pip install flask in venve

## CLI usage: untp_migrator.py

Run migrations from the terminal:

python3 untp_migrator.py \
  -m mapping_file_path/mapping.json \
  -i input_file_path/input.json \
  -o output_file_path/out.json


Options

-m, --mapping: Path to the mapping rules JSON file.

-i, --input: Path to the input JSON file to be transformed.

-o, --output: Path where the transformed output JSON will be written.

--strict (optional, if enabled in your wrapper): Fail if a move source path is missing (instead of skipping).

Example:

python3 untp_migrator.py -m examples/mapping.json -i examples/input.json -o out.json

## Web UI usage: app.py

Launch the local website:

python3 app.py


What happens:

A local server starts on http://127.0.0.1:<port>/

Your default browser opens automatically

Upload mapping.json and input.json, click Transform

The transformed JSON appears in the output area

Click Download to save the output

Stop the server with:

Ctrl + C



7. Run the tool:
   - To transform app-config.json:
   ```bash
   python3 00_Script/main_transformer.py
   ```

   - To transform individual credential:
   ```bash
   python3 00_Script/testing_indiv_credential.py
   ```
---

## 🚀 Testing

To test the credentials:
1. Place the upgraded app-config.json to the upgraded server.
2. If you would like to change the name of the app-config.json for testing purposes, update the `<app-config-name>` in package.json:
```bash
  "scripts": {
    "copy-config": "cp <app-config-name>.json packages/mock-app/src/constants/app-config.json && cp <app-config-name>.json packages/components/src/constants/app-config.json",
```
2. Run the below commands:
   ```bash
   yarn build
   yarn start
   ```
3. Ensure credentials are issued successfully.

## 📂 Input & Output Examples

- **App-config transformation**  
  ```
  01_Data/app-config/RBTP/app-config.json
  → 01_Data/app-config/RBTP/transformed-app-config-v0.6.0.json
  ```

- **Single credential transformation**  
  ```
  01_Data/app-config/RBTP/sample-credential.json
  → 01_Data/app-config/RBTP/transformed-<credential_type>-sample-credential-v0.6.0.json
  ```

---

## ✅ Notes
- This code is primarily designed to transform credentials from v0.5.0 to v0.6.0. To migrate future releases, separate modules need to be created and parameters need to be configured.