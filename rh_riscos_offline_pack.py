"""Pacote local autocontido de código e cópia inicial do mapa, sem credenciais."""
import io,json,zipfile
from pathlib import Path

def pacote_offline(registros):
    root=Path(__file__).resolve().parent
    files=['seguranca_offline.py','rh_riscos.py','rh_riscos_local.py','rh_riscos_offline_pack.py','rh_riscos_monitor.py','rh_riscos_export.py','rh_riscos_excel.py']
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for name in files:z.write(root/name,name)
        for name in ('monitor_font.b64','monitor_font_bold.b64','riscos_excel_template.b64'):
            if (root/'assets'/name).exists():z.write(root/'assets'/name,'assets/'+name)
        z.writestr('base_inicial.json',json.dumps(registros,ensure_ascii=False,indent=2))
        z.writestr('requirements.txt','streamlit>=1.42,<2\npandas>=2.2,<4\naltair>=5,<7\nreportlab>=4,<5\nopenpyxl>=3.1,<4\npillow>=11,<14\nrequests>=2.32,<3\n')
        z.writestr('INICIAR_WINDOWS.bat','@echo off\r\ncd /d "%~dp0"\r\nif not exist .venv\\Scripts\\python.exe py -3 -m venv .venv\r\nif not exist .venv\\pronto (\r\n.venv\\Scripts\\python.exe -m pip install -r requirements.txt\r\nif errorlevel 1 (pause & exit /b 1)\r\necho pronto>.venv\\pronto\r\n)\r\n.venv\\Scripts\\python.exe -m streamlit run seguranca_offline.py --server.address 127.0.0.1\r\npause\r\n')
        z.writestr('LEIA-ME.txt', '10 SUL — SEGURANÇA OFFLINE\n\n1. Extraia toda a pasta em local permanente no computador. Requer Python 3.11 ou superior.\n2. Na primeira execução, com internet, abra INICIAR_WINDOWS.bat para instalar as dependências. Depois a inicialização funciona sem internet.\n3. O mapa inicial acompanha o pacote. A base principal fica em dados/seguranca.sqlite3: faça backup dessa pasta. Não a apague ao atualizar o código.\n4. Para publicar automaticamente no online, o administrador precisa configurar SUPABASE_URL e SUPABASE_SERVICE_KEY no arquivo local .streamlit/secrets.toml (mesma conexão do Portal). Esse arquivo não acompanha o pacote. Mantenha a chave somente no computador autorizado; nunca envie por WhatsApp ou publique no navegador.\n5. Com o aplicativo aberto, a sincronização tenta publicar a cada 30 segundos. Sem conexão, mantém a fila local. Ao reabrir, continua os envios.\n6. A direção é offline → online. Alterações independentes no online geram conflito, preservado para revisão. Use um computador como base principal.\n7. Este pacote cobre o mapa e plano preventivo da Segurança, não todos os módulos do RH. A frequência observada do Monitor exige conexão e fica indisponível offline.\n8. Consulta online continua no Portal com o login de Segurança, em ?seguranca=1&consulta_riscos=1.\n')
    return out.getvalue()
