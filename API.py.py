import base64
import gzip
from datetime import datetime 
from lxml import etree
import requests
from requests_pkcs12 import Pkcs12Adapter
import os

#--- Configurações ---
certificado = r"caminho/para/seu_certificado.pfx" # Caminho do certificado PFX
senha = "sua_senha"                               # Senha do certificado
cnpj = "Depois coloca o CNPJ"                     # CNPJ da empresa
mes_desejado = 7                                  # Mês desejado (1 a 12)
ano_desejado = 2025                               # Ano desejado (2025, 2026, ...)

#-- perguntar para salvar---
pasta_destino =input("Digite onde quer salvar as NF-es: ").strip()

#criar a pasta se não existir
if not os.path.exists(pasta_destino):
    os.makedirs(pasta_destino)


url = "https://hom.nfe.fazenda.gov.br/NFeDistribuicaoDFe/NFeDistribuicaoDFe.asmx"

#--- Requisição SOAP ---
xml_requisicao = f"""<?xml version="1.0" encoding="utf-8"?>
<soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xmlns:xsd="http://www.w3.org/2001/XMLSchema"
                 xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
  <soap12:Body>
    <nfeDistDFeInteresse xmlns="http://www.portalfiscal.inf.br/nfe/wsdl/NFeDistribuicaoDFe">
      <distDFeInt xmlns="http://www.portalfiscal.inf.br/nfe" versao="1.01">
        <tpAmb>2</tpAmb> <!-- 2 = Homologação, 1 = Produção -->
        <cUFAutor>35</cUFAutor> <!-- SP = 35 -->
        <CNPJ>{cnpj}</CNPJ>
        <!-- neste exemplo estou usando consulta pela última NSU -->
        <distNSU>
          <ultNSU>000000000000000</ultNSU>
        </distNSU>
      </distDFeInt>
    </nfeDistDFeInteresse>
  </soap12:Body>
</soap12:Envelope>"""

#--- Envio da requisição ---
session = requests.Session()
session.mount(url, Pkcs12Adapter(pkcs12_filename=certificado, pkcs12_password=senha))

hearders = {"Content-Typer": "application/soap+xml; charset=utf-8"}
resposta = session.post(url, data=xml_requisicao.encode('utf-8'), headers=hearders)

if resposta.status_code != 200:
    print(f"Erro na requisição: {resposta.status_code, resposta.text}")
    exit()

    #--- Processar retorno ---
root = etree.fromstring(resposta.content)

# loop pelos documentos retronados
for doczip in root.xphat("//ns:docZip", namespaces={"ns": "http://www.portalfiscal.inf.br/nfe"}):
    conteudo_base64 = doczip.text
    conteudo_xml = gzip.decompress(base64.b64decode(conteudo_base64))

    #Parce do XML da NFe
    root_nfe = etree.fromstring(conteudo_xml)

    # Tentar pegar a data de emissão
    data_emissao_str = root_nfe.xpath('//nfe:dhEmi/text()',
                namespaces={'nfe': 'http://www.portalfiscal.inf.br/nfe'})
    if not data_emissao_str:
        continue #se não achar, pula 

    data_emissao =datetime.fromisoformat(data_emissao_str[0].replace('Z', '+00:00'))

    #filtar pelo mês/ano desejado
    if data_emissao.month == mes_desejado and data_emissao.year ==ano_desejado:
        nome_arquivo = f"nfe_{data_emissao:%Y-%m-%d_%H%M%S}.xml"
        with open(nome_arquivo, "wb") as f:
            f.write(conteudo_xml)
            print(f"Arquivo salvo: {nome_arquivo}")
