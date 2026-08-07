import os
import shutil
import xml.etree.ElementTree as ET
import pandas as pd

from sqlalchemy import create_engine
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

# ========================= CONFIG =========================
INPUT_PATH = r"\\top-syslog\BLUETEMP\ACH\temp_com"
OUTPUT_PATH_COM1 = r"\\top-syslog\BLUETEMP\ACH"
OUTPUT_PATH_OTHER = r"\\top-syslog\BLUETEMP\ACH\Live\com-"
BACKUP_PATH = r"\\top-syslog\BLUETEMP\ACH\backup"
COMPANY_LIST = ['1', '6', '8']

DB_SERVER = os.getenv("DB_SERVER")
DB_DATABASE = os.getenv("DB_DATABASE")
DB_USERNAME = os.getenv("DB_USERNAME")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# XML Namespace
NS = "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
NS_MAP = {"": NS, "xsi": XSI}

ET.register_namespace("", NS)
ET.register_namespace("xsi", XSI)

# ========================= HELPERS =========================
def ns(tag: str) -> str:
    return f"{{{NS}}}{tag}"

def find(element: ET.Element, path: str) -> ET.Element | None:
    return element.find(path, NS_MAP)

def findall(element: ET.Element, path: str) -> list[ET.Element]:
    return element.findall(path, NS_MAP)

def make_element(tag: str, text: str | None = None) -> ET.Element:
    el = ET.Element(ns(tag))
    if text is not None:
        el.text = text
    return el


def move_to_backup(filename: str, ORIGINAL_FILE_PATH: str) -> None:
    """Move original XML to backup folder."""
    if not os.path.exists(BACKUP_PATH):
        os.makedirs(BACKUP_PATH)

    dst = os.path.join(BACKUP_PATH, filename)
    if os.path.exists(dst):
        os.remove(dst)
    shutil.move(ORIGINAL_FILE_PATH, dst)


def get_db_engine():
    """Create and return a reusable DB engine."""
    if not all([DB_SERVER, DB_DATABASE, DB_USERNAME, DB_PASSWORD]):
        raise Exception("Missing database credentials in .env file")
    
    encoded_password = quote_plus(DB_PASSWORD)
    conn_str = (
        f'mssql+pyodbc://{DB_USERNAME}:{encoded_password}@{DB_SERVER}/{DB_DATABASE}'
        '?driver=SQL+Server'
    )
    return create_engine(conn_str)

# Global engine (created once)
engine = get_db_engine()

def get_VINV_NO(CHECK_NO: str, CdtrNm: str) -> list:
    """Query vendor invoice numbers.
    Excludes entries where PAY_USER_DOC contains 'A/P-' (e.g. internal A/P references)."""
    get_inv_query = f"""
        SELECT VENDOR_INV_NO
        FROM VINV_HDR
        WHERE DOC_NO IN (
            SELECT PAY_USER_DOC
            FROM CHECK_LINE
            WHERE CHECK_NO = '{CHECK_NO}'
            AND PAY_USER_DOC NOT LIKE '%A/P-%'
        )
        AND ACCTNO = (
            SELECT DISTINCT ACCTNO
            FROM CHECK_HDR CHD
            WHERE LTRIM(RTRIM(CHD.PAYEE)) LIKE '%{CdtrNm}%'
            AND CHECK_NO = '{CHECK_NO}'
        );
    """

    df = pd.read_sql(get_inv_query, engine)
    return list(df['VENDOR_INV_NO'])


def execute_flow(filename: str, source_tree: ET.ElementTree, currency: str, comp_num: str, ORIGINAL_FILE_PATH: str) -> None:
    """Process single XML file."""
    src = source_tree.getroot()

    # Ensure proper namespace declaration (do this once)
    if 'xsi' not in src.attrib:
        src.set('xmlns:xsi', XSI)
    
    CdtTrfTxInfList = findall(src, "CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf")
    
    for CdtTrfTxInf in CdtTrfTxInfList:
        # Get payment details
        CdtTrfTxInf_PmtId = find(CdtTrfTxInf, "PmtId")             
        if CdtTrfTxInf_PmtId is None:
            raise Exception(f"No PmtId found in {filename}")

        # Get InstrId (more tolerant)
        InstrId = find(CdtTrfTxInf_PmtId, "InstrId")
        if InstrId is None or InstrId.text is None:
            raise Exception(f"No InstrId found in {filename}")
        
        CHECK_NO = InstrId.text.strip()          
        Cdtr_Nm_elem = find(CdtTrfTxInf, "Cdtr/Nm")
        if Cdtr_Nm_elem is None or Cdtr_Nm_elem.text is None:
            raise Exception(f"CHECK_NO or Cdtr_Nm not found in {filename}")

        Cdtr_Nm = Cdtr_Nm_elem.text.strip()

        # Get invoices
        try:
            VINV_NO = get_VINV_NO(CHECK_NO, Cdtr_Nm)
        except Exception as e:
            raise Exception(f"DB query failed for {filename} (CHECK_NO={CHECK_NO}): {e}")
        
        # Add invoice info if found
        if VINV_NO: 
            all_vinv_no_comma_separated = ",".join(map(str, VINV_NO))
            print(f"{filename} | CHECK_NO={CHECK_NO} | Invoices:{all_vinv_no_comma_separated}")

            # Truncation logic
            if currency == 'HKD':
                # HKD has stricter per-transaction limit (35 chars per line)
                if len(all_vinv_no_comma_separated) > 32:
                    all_vinv_no_comma_separated = all_vinv_no_comma_separated[:32] + '...' # Truncate and add ellipsis if impossible to show all
            else:
                # USD / others: higher general limit (140 chars in total)
                if len(all_vinv_no_comma_separated) > 137:
                    all_vinv_no_comma_separated = all_vinv_no_comma_separated[:137] + '...'
                    
            # Add RmtInf
            RmtInf = make_element("RmtInf")
            RmtInf.append(make_element("Ustrd", all_vinv_no_comma_separated))
            CdtTrfTxInf.append(RmtInf)                                              
        
            # Update ID fields based on currency
            if currency == 'USD':
                # Only change the <InstrID> to VINV_NO, leave the EndToEndId as it is (which is currently HSBC receipt no)
                InstrId.text = all_vinv_no_comma_separated
            elif currency == 'HKD':
                # Change the ACH check number in EndtoEnd reference to VINV_NO
                # This will then show VINV_NO in both transaction_ID, payment details for LowValuePayment
                end_to_end_id = find(CdtTrfTxInf_PmtId, "EndToEndId")
                if end_to_end_id is None:
                    raise Exception("No EndToEndId found")
                end_to_end_id.text = all_vinv_no_comma_separated
            else:
                InstrId.text = all_vinv_no_comma_separated

    # Determine output path
    if comp_num == '1':
        PROC_FILE_PATH = os.path.join(OUTPUT_PATH_COM1, filename)
    else:
        PROC_FILE_PATH = os.path.join(OUTPUT_PATH_OTHER + comp_num, filename)

    # Write revised file
    source_tree.write(PROC_FILE_PATH, xml_declaration=True, encoding="UTF-8")
    move_to_backup(filename, ORIGINAL_FILE_PATH)


def clean_xml(xml_dir, comp_num):
    """Process all XML files in a company temp directory."""
    errors = []
    for filename in os.listdir(xml_dir):
        if not filename.lower().endswith('.xml'):
            continue
        ORIGINAL_FILE_PATH = os.path.join(xml_dir, filename)
        try:
            source_tree = ET.parse(ORIGINAL_FILE_PATH)
            src = source_tree.getroot()

            # Raise clear error if currency not found
            ccy_elem = find(src, "CstmrCdtTrfInitn/PmtInf/DbtrAcct/Ccy")
            if ccy_elem is None or ccy_elem.text is None:
                raise Exception(f"Currency (Ccy) element not found in {filename}")
            currency = ccy_elem.text.strip()
            
            execute_flow(filename, source_tree, currency, comp_num, ORIGINAL_FILE_PATH)
            
        except Exception as e:
            errors.append(f"Error processing {filename}: {e}")
    
    if errors:
        raise Exception("\n".join(errors))


def main():
    """Main entry point."""
    print("Starting ACH XML Processor...")
    errors = []
    
    for comp_num in COMPANY_LIST:
        xml_dir = INPUT_PATH + comp_num
        if not os.path.exists(xml_dir):
            print(f"Warning: Directory not found - {xml_dir}")
            continue

        try:
            clean_xml(xml_dir, comp_num)
            print(f"✓ Company {comp_num} processed successfully.")
        except Exception as e:
            errors.append(f"Company {comp_num}: {e}")
    
    if errors:
        raise Exception("\n".join(errors))

    print("✅ All companies processed successfully.")
    
if __name__ == "__main__":
    main()
