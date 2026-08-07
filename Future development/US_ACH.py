# import os
# import xml.etree.ElementTree as ET
# import pandas as pd

# # CONFIG
# INPUT_PATH = r"\\top-syslog\BLUETEMP\ACH\temp2"
# OUTPUT_PATH = r"\\top-syslog\BLUETEMP\ACH\test"
# ACH_BANKS_ACCOUNTS = "ACH_BANK_ACCOUNTS.csv"

# CONFIG = {
#     "default_cdtr_street": "",
#     "default_cdtr_postcode": "",
#     "default_cdtr_town": "",
#     "default_cdtr_subdiv": "",
#     "default_cdtr_country": "US",
    
#     "default_dbtr_street": "2100 S. Reservoir Street",
#     "default_dbtr_postcode": "91766",
#     "default_dbtr_town": "Pomona",
#     "default_dbtr_subdiv": "CA",
#     "default_dbtr_country": "US",
# }

# # ─── Namespace config ────────────────────────────────────────────────
# NS = "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"
# XSI = "http://www.w3.org/2001/XMLSchema-instance"
# NS_MAP = {"": NS, "xsi": XSI}
# ET.register_namespace("", NS)
# ET.register_namespace("xsi", XSI)
# # ─── Helpers ─────────────────────────────────────────────────────────

# def ns(tag: str) -> str:
#     return f"{{{NS}}}{tag}"


# def remove_element(parent: ET.Element, tag: str) -> None:
#     for child in parent.findall(tag, NS_MAP):
#         parent.remove(child)


# def find(element: ET.Element, path: str) -> ET.Element | None:
#     return element.find(path, NS_MAP)


# def findall(element: ET.Element, path: str) -> list[ET.Element]:
#     return element.findall(path, NS_MAP)


# def make_element(tag: str, text: str | None = None) -> ET.Element:
#     el = ET.Element(ns(tag))
#     if text is not None:
#         el.text = text
#     return el

# def _get_ROUTING_NO(ACH_ACCOUNT_NO: str) -> str:
#     df = pd.read_csv(ACH_BANKS_ACCOUNTS)
#     row = df[df['ACH_ACCOUNT_NO'] == ACH_ACCOUNT_NO]
#     return row['ACH_ACCOUNT_NO'].values[0] if not row.empty else ""

# def main():
#     # Ensure output directory exists
#     # os.makedirs(OUTPUT_PATH, exist_ok=True)

#     # Process files in the input directory
#     for filename in os.listdir(INPUT_PATH):
#         source_tree = ET.parse(os.path.join(INPUT_PATH, filename))
#         src = source_tree.getroot()

#         # ------- Dbtr: ensure <TwnNm>, <CtrySubDvsn>, <Ctry> are present -------
#         dbtrs = findall(src, "CstmrCdtTrfInitn/PmtInf/Dbtr")
#         for dbtr in dbtrs:
#             pstl = find(dbtr, "PstlAdr")
#             if pstl is None:
#                 pstl = make_element("PstlAdr")
#                 dbtr.append(pstl)
                
#             strtnm = find(pstl, "StrtNm")
#             if strtnm is None:
#                 pstl.append(make_element("StrtNm", CONFIG["default_dbtr_street"]))
#             elif not strtnm.text:
#                 strtnm.text = CONFIG["default_dbtr_street"] 
                
#             pstcd = find(pstl, "PstCd")
#             if pstcd is None:
#                 pstl.append(make_element("PstCd", CONFIG["default_dbtr_postcode"]))
#             elif not pstcd.text:
#                 pstcd.text = CONFIG["default_dbtr_postcode"]    
                
#             twnnm = find(pstl, "TwnNm")
#             if twnnm is None:
#                 pstl.append(make_element("TwnNm", CONFIG["default_dbtr_town"]))
#             elif not twnnm.text:
#                 twnnm.text = CONFIG["default_dbtr_town"]

#             subdvsn = find(pstl, "CtrySubDvsn")
#             if subdvsn is None:
#                 pstl.append(make_element("CtrySubDvsn", CONFIG["default_dbtr_subdiv"]))
#             elif not subdvsn.text:
#                 subdvsn.text = CONFIG["default_dbtr_subdiv"]

#             ctry = find(pstl, "Ctry")
#             if ctry is None:
#                 pstl.append(make_element("Ctry", CONFIG["default_dbtr_country"]))
#             elif not ctry.text:
#                 ctry.text = CONFIG["default_dbtr_country"]
                
#         # ------- DbtrAgt: ensure <Ctry> in <FinInstnId/PstlAdr> are present -------
#         dbtr_agts_FinInstnId = findall(src, "CstmrCdtTrfInitn/PmtInf/DbtrAgt/FinInstnId")
#         for dbtr_agt in dbtr_agts_FinInstnId:
#             pstl = find(dbtr_agt, "PstlAdr")
#             if pstl is None:
#                 pstl = make_element("PstlAdr")
#                 dbtr_agt.append(pstl)
#             ctry = find(pstl, "Ctry")
#             if ctry is None:
#                 pstl.append(make_element("Ctry", CONFIG["default_dbtr_country"]))
#             elif not ctry.text:
#                 ctry.text = CONFIG["default_dbtr_country"]

#         # ------- Get ACH account NO to find routing NO first ----------
#         # <CdtrAcct>
#         #   <Id>
#         #     <Othr>
#         #       <Id>317105887</Id>
#         #     </Othr>
#         #   </Id>
#         # </CdtrAcct>
#         CdtrAcct = find(src, "CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/CdtrAcct/Id/Othr/Id")
#         if CdtrAcct is None:
#             CdtrAcct = find(src, "CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/CdtrAcct/Id")
#             print (f"File {filename} does not contain CdtrAcct/Id/Othr/Id. Trying CdtrAcct/Id instead.")
#             if CdtrAcct is None:
#                 print(f"File {filename} does not contain CdtrAcct/Id. Skipping.")
#                 continue

#         if not CdtrAcct.text:
#             print(f"File {filename} has an empty CdtrAcct element. Skipping.")
#             continue

#         ROUTING_NO = _get_ROUTING_NO(CdtrAcct.text)
#         if not ROUTING_NO:
#             print(f"File {filename} has CdtrAcctId {CdtrAcct.text} which does not have a corresponding ROUTING NO in the CSV. Skipping.")
#             continue
        
#         cdtragt = findall(src, "CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/CdtrAgt")
        
#         """
#         <CdtrAgt>
#             <FinInstnId>
#                 <BIC>PNCCUS33</BIC>
#                 <Nm>PNC BANK, N.A.</Nm>
#                 <PstlAdr>
#                     <Ctry>US</Ctry>
#                 </PstlAdr>
#             </FinInstnId>
#         </CdtrAgt>
#         """
        

#         if not cdtragt:
#             print(f"File {filename} does not contain any CdtrAgt elements. Skipping.")
#             continue
            
#         for agt in cdtragt:
#             cdtr_agt_fi = find(agt, "FinInstnId")
#             if cdtr_agt_fi is None:
#                 print(f"CdtrAgt in file {filename} does not contain FinInstnId. Skipping.")
#                 continue
#             bic = find(cdtr_agt_fi, "BIC")
#             if bic is not None:
                
#                 # build routing NO
#                 clr = make_element("ClrSysMmbId")
#                 mmb = make_element("MmbId")
#                 mmb.text = ROUTING_NO
#                 clr.append(mmb)

#                 idx = list(cdtr_agt_fi).index(bic)
#                 cdtr_agt_fi.remove(bic)
#                 cdtr_agt_fi.insert(idx, clr)

#             remove_element(cdtr_agt_fi, ns("Nm"))
            
#         # --- Cdtr Adress ----
#         cdtrs = findall(src, "CstmrCdtTrfInitn/PmtInf/CdtTrfTxInf/Cdtr")

#         for cdtr in cdtrs:
#             pstl = find(cdtr, "PstlAdr")
#             # If the address is empty (self-closing tag), populate if we have data
#             if pstl is None:
#                 pstl = make_element("PstlAdr")
#                 cdtr.append(pstl)
#                 pstl.append(make_element("Ctry", CONFIG["default_cdtr_country"]))
#             else:
#                 ctry = find(pstl, "Ctry")
#                 if ctry is None:
#                     pstl.append(make_element("Ctry", CONFIG["default_cdtr_country"]))
#                 elif not ctry.text:
#                     ctry.text = CONFIG["default_cdtr_country"]
            
#         src.set('xmlns:xsi', XSI)
#         source_tree.write(os.path.join(OUTPUT_PATH, filename), xml_declaration=True, encoding="UTF-8")

# if __name__ == "__main__":
#     main()
