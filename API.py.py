import requests
from requests_pkcs12 import Pkcs12Adapter
import xml.etree.ElementTree as ET
import base64
import os
from datetime import datetime

# ===================== CONFIGURAÇÕES =====================

CERT_PATH = r'C:\Users\bruno.sousa\Desktop\certificado.pfx\PRO_SAUDE_ASSOCIACAO_BENEFICENTE_DE_ASSISTENCIA_S_24232886000167_17163983676899473001.pfx'
CERT_PASS = '123456'  
CNPJ ="24232886002020"

URL_DFE = "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx"

# Período de filtro
DATA_INICIAL = datetime(2023, 7, 1)
DATA_FINAL = datetime(2023, 7, 31)

# Pastas
PASTA_SAIDA = "notas_xml"
PASTA_NFE = os.path.join(PASTA_SAIDA, "nfe")
os.makedirs(PASTA_NFE, exist_ok=True)

# ===================== MONTAR XML DE CONSULTA =====================

headers = {
    "Content-Type": "text/xml; charset=utf-8",
    "SOAPAction": "http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe/nfeDistDFeInteresse"
}

soap_body = f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <nfeDistDFeInteresse xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">
      <nfeDadosMsg>
        <distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
          <tpAmb>1</tpAmb>
          <cUFAutor>41</cUFAutor> <!-- 41 = PR (Paraná). Altere se for outro estado -->
          <CNPJ>{CNPJ}</CNPJ>
          <distNSU>
            <ultNSU>000000000000000</ultNSU>
          </distNSU>
        </distDFeInt>
      </nfeDadosMsg>
    </nfeDistDFeInteresse>
  </soap12:Body>
</soap12:Envelope>
"""

# ===================== ENVIAR REQUISIÇÃO =====================

session = requests.Session()
session.mount("https://", Pkcs12Adapter(pkcs12_filename=CERT_PATH, pkcs12_password=CERT_PASS))

print("⏳ Consultando SEFAZ...")
response = session.post(URL_DFE, data=soap_body.encode("utf-8"), headers=headers)

if response.status_code != 200:
    print("❌ Erro ao consultar SEFAZ:", response.status_code)
    print(response.text)
    exit()

# ===================== PROCESSAR RESPOSTA =====================

root = ET.fromstring(response.content)

total_salvas = 0

for doc_zip in root.findall(".//{http://www.portalfiscal.inf.br/nfe}docZip"):
    nsu = doc_zip.attrib.get("NSU", "sem_nsu")
    tipo = doc_zip.attrib.get("schema", "outros")
    conteudo = base64.b64decode(doc_zip.text)

    # Apenas NFe
    if "nfeproc" in tipo.lower():
        try:
            xml_root = ET.fromstring(conteudo)
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

            # Tenta pegar a data de emissão
            dhEmi = xml_root.find(".//nfe:dhEmi", ns)
            if dhEmi is None:
                continue

            data_emissao = datetime.fromisoformat(dhEmi.text[:19])

            if DATA_INICIAL <= data_emissao <= DATA_FINAL:
                # Salvar o XML
                caminho_xml = os.path.join(PASTA_NFE, f"{nsu}.xml")
                with open(caminho_xml, "wb") as f:
                    f.write(conteudo)
                print(f"📄 NF-e salva: {caminho_xml}")
                total_salvas += 1

        except Exception as e:
            print(f"⚠️ Erro ao processar NSU {nsu}: {e}")

print(f"\n✅ Consulta finalizada. {total_salvas} NF-e(s) salvas no período de {DATA_INICIAL.date()} a {DATA_FINAL.date()}.")