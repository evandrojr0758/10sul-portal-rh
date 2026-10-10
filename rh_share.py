"""Resumo compacto de frequência, sem alterar lançamentos."""
import base64
from collections import Counter
from io import BytesIO
from pathlib import Path
from functools import lru_cache


def resumir(colaboradores, grade, dias, ocorrencias, inicio, fim):
    ids = {int(c["id"]) for c in colaboradores}
    ativos = sum(str(c.get("ativo", False)).lower() in {"true", "1"} for c in colaboradores)
    totais = Counter()
    ranking = []
    for linha in grade:
        codigos = Counter(str(linha.get(d) or "").strip().upper() for d in dias)
        totais.update(codigos)
        fa, at = codigos["FA"], codigos["A"]
        if fa + at:
            ranking.append({"nome": str(linha.get("COLABORADOR") or ""), "faltas": fa,
                            "atestados": at, "total": fa + at})
    ranking.sort(key=lambda r: (-r["total"], r["nome"].casefold()))
    desvios = None
    if ocorrencias is not None:
        excluidos = {"ADVERTÊNCIA VERBAL", "ORIENTAÇÃO", "ELOGIO / RECONHECIMENTO"}
        desvios = 0
        for o in ocorrencias:
            tipo = str(o.get("tipo") or "").strip().upper()
            try:
                cid = int(o.get("colaborador_id") or 0)
            except (ValueError, TypeError):
                continue
            data = str(o.get("data") or "")[:10]
            if cid in ids and inicio <= data <= fim and tipo and tipo not in excluidos:
                desvios += 1
    return {"ativos": ativos, "faltas": totais["FA"], "atestados": totais["A"],
            "liberacoes": totais["LB"], "compensacoes": totais["COMP"],
            "desvios": desvios, "ranking": ranking[:5]}


@lru_cache(maxsize=32)
def fonte(size, bold=False):
    from PIL import ImageFont
    name = "monitor_font_bold.b64" if bold else "monitor_font.b64"
    data = base64.b64decode((Path(__file__).parent / "assets" / name).read_text(), validate=True)
    return ImageFont.truetype(BytesIO(data), size)


def gerar_imagem(resumo, periodo, filtros, atualizado, rascunho=False):
    from PIL import Image, ImageDraw
    imagem = Image.new("RGB", (1000, 4000), "#f3f6fa")
    d = ImageDraw.Draw(imagem)
    azul, texto, cinza = "#15364b", "#243746", "#667085"
    def txt(x, y, value, size=25, bold=False, color=texto):
        d.text((x, y), str(value), font=fonte(size, bold), fill=color)
    def wrap(value, x, y, width=910, size=23, color=cinza):
        line = ""
        for word in str(value).split():
            proposal = (line + " " + word).strip()
            if line and d.textlength(proposal, font=fonte(size)) > width:
                txt(x, y, line, size, color=color)
                y += size + 9
                line = word
            else:
                line = proposal
        if line:
            txt(x, y, line, size, color=color)
            y += size + 9
        return y
    d.rectangle((0, 0, 1000, 155), fill=azul)
    txt(40, 25, "10 SUL | PORTAL RH", 34, True, "white")
    txt(40, 78, "Resumo de frequência", 28, color="white")
    txt(40, 117, atualizado, 20, color="white")
    y = wrap(periodo, 40, 185, size=28, color=texto)
    y = wrap(filtros, 40, y + 8)
    if rascunho:
        y = wrap("RASCUNHO • Inclui lançamentos não salvos.", 40, y + 8, color="#a46a00")
    y += 20
    cards = [("Colaboradores ativos", resumo["ativos"]), ("Faltas • dias", resumo["faltas"]),
             ("Atestados • dias", resumo["atestados"]), ("Liberações • dias", resumo["liberacoes"]),
             ("Compensações • dias", resumo["compensacoes"]),
             ("Desvios • registros", resumo["desvios"] if resumo["desvios"] is not None else "Indisponível")]
    for i, (label, value) in enumerate(cards):
        x, cy = 40 + (i % 2) * 470, y + (i // 2) * 145
        d.rounded_rectangle((x, cy, x + 450, cy + 125), radius=14, fill="white", outline="#d6e0e6")
        txt(x + 20, cy + 15, label, 23)
        txt(x + 20, cy + 52, value, 42 if isinstance(value, int) else 27, True)
    y += 450
    txt(40, y, "Ranking de ausências • Top 5", 28, True)
    y += 48
    d.rectangle((40, y, 960, y + 45), fill=azul)
    for x, label in [(55, "Colaborador"), (625, "Faltas"), (725, "Atest."), (855, "Total")]:
        txt(x, y + 8, label, 22, True, "white")
    y += 45
    if not resumo["ranking"]:
        txt(55, y + 18, "Sem faltas ou atestados no período.", 24)
        y += 65
    for i, r in enumerate(resumo["ranking"]):
        d.rectangle((40, y, 960, y + 58), fill="white" if i % 2 == 0 else "#e9f0f5")
        name = r["nome"]
        while name and d.textlength(name, font=fonte(23)) > 535:
            name = name[:-1]
        if name != r["nome"]:
            name = name.rstrip() + "…"
        txt(55, y + 15, name, 23)
        for x, key in [(645, "faltas"), (755, "atestados"), (875, "total")]:
            txt(x, y + 15, r[key], 24, key == "total")
        y += 58
    y = wrap("Ausências = faltas + atestados em dias lançados; ranking restrito aos filtros da tela. Ativos = situação atual do cadastro.", 40, y + 24, size=20)
    y = wrap("Desvios: critério da gratificação; exclui advertência verbal, orientação e elogio / reconhecimento.", 40, y + 8, size=20)
    if resumo["desvios"] is None:
        y = wrap("Não foi possível consultar os desvios. O valor não foi tratado como zero.", 40, y + 8, size=20, color="#a46a00")
    txt(40, y + 20, "Desenvolvido por Evandro Junior", 18, color=cinza)
    out = BytesIO()
    imagem.crop((0, 0, 1000, y + 65)).save(out, "PNG")
    return out.getvalue()


def botao_compartilhar_imagem(png):
    import streamlit.components.v1 as components
    imagem_base64 = base64.b64encode(png).decode("ascii")
    html = """<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<style>
body{margin:0;font-family:Arial,sans-serif}button{width:100%;padding:13px;border:0;border-radius:8px;background:#128c7e;color:white;font-size:16px;cursor:pointer}button:disabled{opacity:.65}p{font-size:13px;color:#52616b;margin:8px 0}
</style>
<button id="share">Compartilhar imagem no WhatsApp</button>
<p id="status" role="status">Escolha o WhatsApp e o contato na tela de compartilhamento.</p>
<script>
const bytes=Uint8Array.from(atob("__PNG__"),c=>c.charCodeAt(0));
const file=new File([bytes],"resumo_rh_10sul.png",{type:"image/png"});
const button=document.getElementById("share"), status=document.getElementById("status");
const navigators=[navigator];
try { if(window.parent!==window) navigators.unshift(window.parent.navigator); } catch(e) {}
button.onclick=async()=>{
 const sharing=navigators.find(n=>{try{return typeof n.share==="function"&&typeof n.canShare==="function"&&n.canShare({files:[file]});}catch(e){return false;}});
 if(!sharing){status.textContent="Este navegador não permite compartilhar imagens diretamente. Use Baixar imagem PNG e anexe no WhatsApp.";return;}
 button.disabled=true;
 try{
  await sharing.share({files:[file],title:"10 SUL — Resumo do Portal RH"});
  status.textContent="Imagem compartilhada com o aplicativo escolhido.";
 }catch(e){
  status.textContent=e.name==="AbortError"?"Compartilhamento cancelado. Você pode tentar novamente.":"Não foi possível abrir o compartilhamento. Use Baixar imagem PNG e anexe no WhatsApp.";
 }finally{button.disabled=false;}
};
</script></html>""".replace("__PNG__", imagem_base64)
    components.html(html, height=130, scrolling=False)

