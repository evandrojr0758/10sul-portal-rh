import sys,os,webbrowser,threading
from pathlib import Path

def main():
    root=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parents[1]))
    os.chdir(root)
    os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS']='false'
    sys.path.insert(0,str(root))
    # Use a fixed localhost endpoint; do not expose the desktop server to the network.
    from streamlit.web import cli
    threading.Timer(4,lambda:webbrowser.open('http://127.0.0.1:18517')).start()
    sys.argv=['streamlit','run',str(root/'seguranca_desktop.py'),'--server.address=127.0.0.1','--server.port=18517','--server.headless=true','--browser.gatherUsageStats=false']
    cli.main()
if __name__=='__main__':main()
