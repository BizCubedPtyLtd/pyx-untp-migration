# pyx-untp-migration

# 📘 Pyx UNTP Migration Tool

This project takes 0.5.0 credentials in app-config.json across projects and transforms them into the required 0.6.0 credential format based on [V0.6.0 Migration Guide](https://uncefact.github.io/tests-untp/docs/next/migration-guides/v0.6.0/)

There are 2 types of code that are produced:
1. main_transformer.py: reads full app-config.json and outputs all the transformed credentials within app-config.json
2. testing_indiv_credential.py: reads a single credential and outputs the transformed credential

## 📂 Folder Structure
```
pyx-untp-migration/
├── 00_Script/                  # main python scripts & transformation modules (main_transformer.py)
├── 01_Data/app-config          # stores app-config.json for different Pyx projects
├── 02_Documentation/           # contains project documentations
└── 03_Test_UNTP-Playground/    # stores successful test files in tests-untp playground
```

## 🚀 Setup & Usage

1. Clone the repository /pyx-apps/ in Ubuntu 24.04
2. Install Python Extensions:
    - Python Debugger
    - Python
    - Pylance
    - Python Environment

3. Create and activate a Python virtual environment (recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Place your files in `01_Data/app-config/<project_name>/`, e.g.:
   - To transform app-config.json:
   ```
   01_Data/app-config/BCMine/app-config.json               
   01_Data/app-config/RegenFarmers/app-config.json  
   ```
   - To transform individual credential:
   ```bash
   01_Data/app-config/BCMine/sample-credential.json
   ```

6. Update the parameters
   - To transform app-config.json:
   ```bash
   input_folder_name = "01_Data/app-config"
   brand_name = 'RBTP'
   file_name = "app-config.json"
   version = '0.6.0'

   ```

   - To transform individual credential:
   ```bash
   input_folder_name = "01_Data/app-config"
   brand_name = 'RBTP'
   file_name = "sample-credential.json"
   testing_folder = 'DIA'
   version = '0.6.0'
   ```


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