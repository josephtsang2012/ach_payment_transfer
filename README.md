# ACH XML Processor

## Purpose
This is one of the 2026 Financial Transformation Initiative (Seq #5 and #6).
The Pentagon ERP system generates XML payment files (ISO 20022 pain.001 format) for HSBC ACH / online banking payments. However, these files **do not contain vendor invoice numbers**. When vendors receive the payment in HSBC, they cannot easily identify which specific invoices are being settled.

This Flask web application + Python script solves the issue by:
- Querying the database to retrieve the corresponding vendor invoice numbers (`VINV_NO`).
- Inserting the invoice numbers into the XML (bounded between `<RmtInf><Ustrd>` tags and updating relevant ID fields).
- Producing a revised XML file ready for upload to HSBC.

---

## Quick Notes
- Although the main script is named `HK_non_trade.py`, it also supports trade data and can potentially be extended to the US region. The filename is kept as-is for convenience.
- For most HSBC cross-border and ACH transfers (e.g., via HSBCnet), the unstructured remittance text field supports up to 140 total characters for USD (high value), with each specific tag or line generally not exceeding 35 characters for HKD (low value).

### Project Structure
1. `app.py` – Flask web server
2. `index.html` – Web UI
3. `HK_non_trade.py` – Core XML processing & DB logic
4. `run.bat` – Launcher script
5. `.env` – Database credentials (do not commit to Git)

### Bank/ ISO format changes
We should pay close attention to changes of bank or ISO requirements. See latest: [Bank changes](Bank%20changes/). 
In case our current ACH xml is not compatible with the new requirement, we would need to contact Pentagon engineers/ HSBC IT for support, or we can revise the script for further development.

### Further Development
Go to here for the development for HSBC US ACH payment transfer: [Future development](Future%20development/). 
Unlike HK HSBC, US HSBC does not use swift code but routing code for processing, and it might have slightly different ISO standards.
To run locally for testing/development:
```bash
python app.py
```

---

## Architecture & Workflow

### High-Level Flow
Notes: In order for these processes to run, you **must** connect to Topcast network using internet cable. 
1. **Pentagon ERP** is reconfigured so that generated XML files are first placed in temporary folders (`temp_com1`, `temp_com6`, `temp_com8`).
    i.   Nevigate to `PAIN HSBC export file setup` in the Financials' Administration module.
<img width="1429" height="740" alt="1" src="https://github.com/user-attachments/assets/c4ae89ca-5deb-42ed-911e-76c06506428c" />

   
    ii.  Set up the output path, organization identification (has to be set up with the bank first), and counter.
<img width="1308" height="630" alt="2" src="https://github.com/user-attachments/assets/b077e035-2f95-477d-8cfb-59aac6402d50" />


2. User accesses the Flask web app and triggers the process.
<img width="1057" height="691" alt="3" src="https://github.com/user-attachments/assets/f3921919-9f78-403e-9c36-3cdc8d49c5fb" />


3. The script (`HK_non_trade.py`) reads the original XMLs, queries the DB for invoice numbers, modifies the XML, moves the original to backup, and writes the revised XML to the **live** folders. Temporay folders will be cleared.
<img width="808" height="480" alt="1" src="https://github.com/user-attachments/assets/c732d078-79f5-4fd8-87ea-fe1d53616f69" />

   
4. The revised files are then pushed from the company to the HSBC server (via SFTP or portal upload).
5. Once processed by HSBC, the files disappear from the live folder. Original unrevised XMLs are kept in the backup folder. Ideally the payment should appear in the HSBC portal. If there is any unexpected outcome, you may check the incoming messages from HSBC (`ACCP` means Accepted, `REJT` means Rejected).
<img width="838" height="355" alt="2" src="https://github.com/user-attachments/assets/55af9cb4-2b3b-4efa-91ec-48f549f2ae8e" />


### Folder Paths
- **Temp**: `\\top-syslog\BLUETEMP\ACH\temp_comX` (X = 1,6,8)
- **Live**:
  - Company 1 → `\\Top-syslog\BLUETEMP\ACH\`
  - Company 6 → `\\Top-syslog\BLUETEMP\ACH\Live\com-6`
  - Company 8 → `\\Top-syslog\BLUETEMP\ACH\Live\com-8`
- **Backup**: `\\Top-syslog\BLUETEMP\ACH\backup`

### Workflow Diagram
<img width="571" height="462" alt="6" src="https://github.com/user-attachments/assets/7f3b2e04-e2ab-4c66-9142-730fe4bf21d7" />


---
## Hosting

### Production Links
- **Primary (Desktop – more stable)**: http://{Desktop IP}:5000/ (url = f"http://{Desktop IP}:{port}/endpoint?param=5000"; if it changes, go to cmd and type ipconfig, look for "IPv4 Address. . . . . . . . . . . . :")
- **Secondary (VM)**: http://{VM IP}:5000/ (VM IP; similar to above)

**Recommendation**: Use the desktop link whenever possible. The VM has had frequent issues (forced shutdowns, authentication/password reset problems, SQL connection failures, etc.).

---

## Deployment (Windows)

### Firewall Setup (Admin required)
1. Go to **Windows Settings → Privacy & security → Firewall & network protection**
2. Click **Allow an app through Firewall**
3. Click **Change settings**
4. Enable `python.exe` for **Domain, Private, and Public**

### Running the Application
Use the provided `run.bat` (recommended):
```cmd
cd /d "C:\Your\Project\Folder"
run.bat
```
Or run manually
```cmd
cd /d "C:\Your\Project\Folder"
venv\Scripts\python.exe app.py
```
Keep the Command Prompt window open. The web UI will be available at the IP addresses above (internal network only).

---

## Troubleshooting
### 1. WinError 1326: The user name or password is incorrect (\\top-syslog...)
<img width="619" height="581" alt="7" src="https://github.com/user-attachments/assets/7f0e9d88-ba33-423e-affe-bfd6abe434b5" />


Common on the VM.
Fix:
1. Open File Explorer and navigate to \\top-syslog
2. Enter valid network/Pentagon credentials when prompted.
3. Re-run the process.

### Other Common Issues
1. SQL / DB connection problems → verify .env credentials.
2. VM instability → switch to desktop host.
3. Check the console output for detailed tracebacks.
