import requests
from requests_pkcs12 import Pkcs12Adapter
import xml.etree.ElementTree as ET
import base64
import os
from datetime import datetime

# Configurações do certificado e empresa
CERT_PATH = "certificado.pfx"
CERT_PASS = "senha_do_certificado"
CNPJ = "12345678000195"
URL_DFE = "https://www1.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx"

# Período desejado (exemplo: Julho/2023)
DATA_INICIAL = datetime(2023, 7, 1)
DATA_FINAL   = datetime(2023, 7, 31)

# Pasta de saída
PASTA_SAIDA = "notas_xml"
os.makedirs(PASTA_SAIDA, exist_ok=True)

# Requisição inicial (pelo último NSU = vai varrer todas notas disponíveis)
xml_request = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <nfeDistDFeInteresse xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">
      <nfeDadosMsg>
        <distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
          <tpAmb>1</tpAmb>        <!-- 1 = Produção / 2 = Homologação -->
          <cUFAutor>35</cUFAutor> <!-- UF da empresa (35 = SP) -->
          <CNPJ>{CNPJ}</CNPJ>
          <distNSU>
            <ultNSU>000000000000000</ultNSU>
          </distNSU>
        </distDFeInt>
      </nfeDadosMsg>
    </nfeDistDFeInteresse>
  </soap:Body>
</soap:Envelope>"""

headers = {
    "Content-Type": "text/xml; charset=utf-8",
    "SOAPAction": "http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe/nfeDistDFeInteresse"
}

# Sessão com certificado digital
session = requests.Session()
session.mount("https://", Pkcs12Adapter(pkcs12_filename=CERT_PATH, pkcs12_password=CERT_PASS))

print("🔎 Buscando notas no período:", DATA_INICIAL.date(), "até", DATA_FINAL.date())

# Faz requisição
response = session.post(URL_DFE, data=xml_request.encode("utf-8"), headers=headers)
root = ET.fromstring(response.text)

qtd_salvas = 0

# Extrai as notas
for docZip in root.findall(".//{http://www.portalfiscal.inf.br/nfe}docZip"):
    conteudo_xml = base64.b64decode(docZip.text).decode("utf-8")

    try:
        xml_nfe = ET.fromstring(conteudo_xml)

        # Busca data de emissão
        dhEmi = xml_nfe.find(".//{http://www.portalfiscal.inf.br/nfe}dhEmi")
        if dhEmi is not None:
            data_emissao = datetime.fromisoformat(dhEmi.text.replace("Z", "+00:00"))

            # Filtra pelo período
            if DATA_INICIAL <= data_emissao <= DATA_FINAL:
                chave = xml_nfe.find(".//{http://www.portalfiscal.inf.br/nfe}infNFe").attrib.get("Id", "NFeSemChave")
                arquivo = os.path.join(PASTA_SAIDA, f"{chave}.xml")

                with open(arquivo, "w", encoding="utf-8") as f:
                    f.write(conteudo_xml)

                qtd_salvas += 1
                print(f"✅ NFe salva: {arquivo} (Data emissão: {data_emissao.date()})")

    except Exception as e:
        print("⚠️ Erro ao processar XML:", e)

print(f"\n📂 Processo concluído! {qtd_salvas} notas salvas em '{PASTA_SAIDA}'")
