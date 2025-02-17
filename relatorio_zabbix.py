import requests
import smtplib
import ssl
from email.message import EmailMessage
from fpdf import FPDF
import matplotlib.pyplot as plt
from datetime import datetime

# ---------------------- CONFIGURAÇÕES ----------------------
ZABBIX_URL = 'https://localhost/zabbix/api_jsonrpc.php'
ZABBIX_USER = 'api'
ZABBIX_PASSWORD = 'suasenha'
EMAIL_REMETENTE = 'zabbix@localhost.com'
SENHA = 'suasenha'
EMAIL_DESTINATARIOS = ['user@localrost.com']  # Lista de e-mails
GROUP_ID = 94  # ID do grupo específico

# ---------------------- AUTENTICAÇÃO ----------------------
def autenticar():
    payload = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {
            "user": ZABBIX_USER,
            "password": ZABBIX_PASSWORD
        },
        "id": 1,
        "auth": None
    }
    headers = {'Content-Type': 'application/json'}
    response = requests.post(ZABBIX_URL, json=payload, headers=headers)
    return response.json()['result']

# ---------------------- COLETA DE TRIGGERS SEVERIDADE ALTA ----------------------
def listar_triggers_por_grupo(token, group_id):
    payload = {
        "jsonrpc": "2.0",
        "method": "trigger.get",
        "params": {
            "groupids": group_id,
            "output": ["triggerid", "description", "priority", "lastchange"],
            "selectHosts": ["host"],
            "filter": {
                "value": 1  # Apenas triggers ativas
            },
            "sortfield": "priority",
            "sortorder": "DESC"
        },
        "auth": token,
        "id": 2
    }
    headers = {'Content-Type': 'application/json'}
    response = requests.post(ZABBIX_URL, json=payload, headers=headers)
    triggers = response.json().get('result', [])

    # Filtrar apenas triggers de prioridade alta (4) e substituir {HOST.NAME}
    triggers_alta = [
        {
            "host": trigger['hosts'][0]['host'],
            "description": trigger['description'].replace('{HOST.NAME}', trigger['hosts'][0]['host']),
            "priority": trigger['priority'],
            "lastchange": datetime.fromtimestamp(int(trigger['lastchange'])).strftime('%Y-%m-%d %H:%M:%S')
        }
        for trigger in triggers if trigger['priority'] == '4'
    ]

    return triggers_alta

# ---------------------- GERAR PDF ----------------------
def gerar_relatorio_triggers(triggers):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", style='B', size=16)
    pdf.cell(200, 10, txt="Relatório de Triggers de Severidade Alta", ln=True, align='C')
    pdf.ln(10)

    # Definição da tabela
    pdf.set_font("Arial", style='B', size=12)
    pdf.set_fill_color(200, 200, 200)  # Cinza claro para cabeçalho
    pdf.cell(60, 10, "Host", border=1, align='C', fill=True)
    pdf.cell(80, 10, "Trigger", border=1, align='C', fill=True)
    pdf.cell(50, 10, "Alerta desde", border=1, align='C', fill=True)
    pdf.ln()

    pdf.set_font("Arial", size=10)
    for trigger in triggers:
        pdf.cell(60, 10, trigger['host'], border=1, align='C')
        pdf.cell(80, 10, trigger['description'], border=1, align='C')
        pdf.cell(50, 10, trigger['lastchange'], border=1, align='C')
        pdf.ln()

    pdf.output("relatorio_triggers.pdf")
    print("Relatório de triggers gerado com sucesso!")
# ---------------------- GERAR GRÁFICO ----------------------
def gerar_grafico_triggers(triggers):
    hosts = [f"{trigger['host']}\n{trigger['lastchange']}" for trigger in triggers]
    incidencias = [1 for _ in triggers]  # Cada trigger conta como uma ocorrência

    plt.figure(figsize=(10, 6))
    plt.barh(hosts, incidencias, color='orange')
    plt.xlabel("Número de Triggers")
    plt.ylabel("Hosts")
    plt.title("Hosts com Triggers de Severidade Alta")
    plt.tight_layout()

    for index, value in enumerate(incidencias):
        plt.text(value, index, str(value))

    plt.savefig("grafico_triggers.png")
    plt.close()

# ---------------------- ENVIAR E-MAIL ----------------------
def enviar_email_pdf_e_grafico(arquivo_pdf, arquivo_grafico):
    mensagem = EmailMessage()
    mensagem['Subject'] = 'Relatório de Triggers de Severidade Alta'
    mensagem['From'] = EMAIL_REMETENTE
    mensagem['To'] = ', '.join(EMAIL_DESTINATARIOS)
    mensagem.set_content('Segue em anexo o relatório das triggers de severidade alta e o gráfico correspondente.')

    # Anexar o PDF
    with open(arquivo_pdf, 'rb') as f:
        pdf_data = f.read()
        mensagem.add_attachment(pdf_data, maintype='application', subtype='pdf', filename=arquivo_pdf)

    # Anexar o gráfico
    with open(arquivo_grafico, 'rb') as f:
        grafico_data = f.read()
        mensagem.add_attachment(grafico_data, maintype='image', subtype='png', filename=arquivo_grafico)

    # Enviar o e-mail
    contexto = ssl.create_default_context()
    with smtplib.SMTP_SSL('mail-bre-03.linktelcorp.com', 465, context=contexto) as servidor:
        servidor.login(EMAIL_REMETENTE, SENHA)
        servidor.send_message(mensagem)
        print('E-mail enviado com sucesso para:', ', '.join(EMAIL_DESTINATARIOS))

# ---------------------- EXECUÇÃO ----------------------
if __name__ == "__main__":
    token = autenticar()
    triggers = listar_triggers_por_grupo(token, GROUP_ID)

    gerar_relatorio_triggers(triggers)
    gerar_grafico_triggers(triggers)

    enviar_email_pdf_e_grafico("relatorio_triggers.pdf", "grafico_triggers.png")
