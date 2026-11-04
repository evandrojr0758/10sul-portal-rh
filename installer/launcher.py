import sys,os,webbrowser,threading
from pathlib import Path

def main():
    logdir=Path(os.environ.get('LOCALAPPDATA') or Path.home())/'10Sul'/'Seguranca'/'logs'
    logdir.mkdir(parents=True,exist_ok=True)
    log=open(logdir/'inicializacao.log','a',encoding='utf-8',buffering=1)
    sys.stdout=log;sys.stderr=log
    import traceback
    root=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))
    os.chdir(root)
    os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS']='false'
    sys.path.insert(0,str(root))
    # Use a fixed localhost endpoint; do not expose the desktop server to the network.
    from streamlit.web import cli
    threading.Timer(4,lambda:webbrowser.open('http://127.0.0.1:18517')).start()
    sys.argv=['streamlit','run',str(root/'seguranca_desktop.py'),'--server.address=127.0.0.1','--server.port=18517','--server.headless=true','--browser.gatherUsageStats=false']
    try:
        cli.main()
    except BaseException:
        traceback.print_exc(file=log)
        raise
if __name__=='__main__':main()
