"""Relatório PDF do mapa de riscos; recebe somente atividades salvas e filtradas."""
from collections import Counter
from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, LongTable

CATEGORIAS = ["Fatalidade possível", "Amputação possível", "Afastamento possível", "Lesão sem afastamento possível", "Baixo potencial", "A validar"]
CORES = ["#dc2626", "#ef4444", "#eab308", "#facc15", "#16a34a", "#64748b"]


def gerar_pdf_riscos(df, filtros="Todos os registros", agora=None):
    registros = df.fillna("").to_dict("records")
    instante = agora or datetime.now(ZoneInfo("America/Sao_Paulo"))
    saida = BytesIO()
    doc = SimpleDocTemplate(saida, pagesize=landscape(A4), rightMargin=16*mm,
                            leftMargin=16*mm, topMargin=18*mm, bottomMargin=16*mm)
    estilos = getSampleStyleSheet()
    estilos.add(ParagraphStyle(name="TituloRisco", fontSize=25, leading=29, textColor=colors.HexColor("#102b46"), spaceAfter=8))
    estilos.add(ParagraphStyle(name="TextoRisco", fontSize=9, leading=13, spaceAfter=5, textColor=colors.HexColor("#334155"), wordWrap="CJK"))
    estilos.add(ParagraphStyle(name="CelulaRisco", fontSize=8, leading=11, wordWrap="CJK"))
    estilos.add(ParagraphStyle(name="CabRisco", fontSize=8, leading=11, textColor=colors.white))
    estilos.add(ParagraphStyle(name="NumeroRisco", fontSize=23, leading=27, alignment=TA_CENTER, textColor=colors.HexColor("#102b46")))

    def p(valor, estilo="TextoRisco"):
        texto = escape(str(valor if valor is not None and valor != "" else "-"))
        return Paragraph(texto.replace("\n", "<br/>"), estilos[estilo])

    def tabela(cabecalhos, linhas, larguras):
        t = LongTable([[p(c, "CabRisco") for c in cabecalhos]] +
                      [[p(c, "CelulaRisco") for c in linha] for linha in linhas],
                      colWidths=larguras, repeatRows=1, splitInRow=1, hAlign="LEFT")
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#102b46")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor("#14b8a6")),
        ]))
        return t

    def prazo_br(valor):
        if not valor:
            return ""
        try:
            return datetime.fromisoformat(str(valor)[:10]).strftime("%d/%m/%Y")
        except ValueError:
            return str(valor)

    def grafico(titulo, categorias, campo, paleta):
        contagem = Counter(str(r.get(campo) or "Pendente") for r in registros)
        d = Drawing(doc.width, 38 + len(categorias)*25)
        d.add(String(0, d.height-14, titulo, fontName="Helvetica-Bold", fontSize=12, fillColor=colors.HexColor("#102b46")))
        maior = max([contagem[c] for c in categorias] + [1])
        for i, categoria in enumerate(categorias):
            y = d.height-43-i*25
            d.add(String(0, y+3, categoria, fontName="Helvetica", fontSize=9))
            largura = (doc.width-255)*contagem[categoria]/maior
            d.add(Rect(210, y, doc.width-255, 15, fillColor=colors.HexColor("#eef2f6"), strokeColor=None))
            if largura:
                d.add(Rect(210, y, largura, 15, fillColor=colors.HexColor(paleta[i]), strokeColor=None))
            d.add(String(doc.width-30, y+3, str(contagem[categoria]), fontName="Helvetica-Bold", fontSize=10))
        return d

    historia = [p("10 SUL  |  SEGURANÇA DO TRABALHO"), p("Mapa de riscos", "TituloRisco"),
                p("Relatório gerencial e plano preventivo"),
                p("Emitido em " + instante.strftime("%d/%m/%Y às %H:%M") + " (Brasília)"),
                p("Filtros: " + filtros), Spacer(1, 8)]
    criticos = sum(r.get("consequencia") in CATEGORIAS[:2] for r in registros)
    moderados = sum(r.get("consequencia") in CATEGORIAS[2:4] for r in registros)
    pendentes = sum(r.get("validacao") != "Validada" for r in registros)
    metricas = Table([[p(n, "NumeroRisco") for n in [len(registros), criticos, moderados, pendentes]],
                      [p(n) for n in ["Atividades selecionadas", "Potencial crítico", "Potencial moderado", "A validar em campo"]]],
                     colWidths=[doc.width/4]*4)
    metricas.setStyle(TableStyle([("BACKGROUND", (0,0),(-1,-1),colors.HexColor("#f1f5f9")),
                                 ("TOPPADDING",(0,0),(-1,0),10), ("BOTTOMPADDING",(0,-1),(-1,-1),8)]))
    historia += [metricas, Spacer(1, 16), grafico("Atividades por severidade", CATEGORIAS, "consequencia", CORES),
                 Spacer(1, 8), p("As cores representam a severidade selecionada. A classificação deve ser validada pela Segurança em campo; não representa uma nova avaliação de probabilidade.")]
    if registros:
        historia += [PageBreak(), p("Plano preventivo", "TituloRisco"),
                     grafico("Situação das ações", ["Não iniciada", "Em andamento", "Concluída"], "status_acao", ["#64748b", "#eab308", "#16a34a"])]
        vencidas = sum(bool(r.get("prazo") and str(r["prazo"])[:10] < instante.date().isoformat() and r.get("status_acao") != "Concluída") for r in registros)
        historia += [p(f"Ações com prazo vencido: {vencidas}. Todos os indicadores refletem a seleção exportada."), Spacer(1, 8),
                     tabela(["Atividade", "Ação proposta", "Responsável", "Prazo", "Status"],
                            [[r.get("atividade", ""), r.get("acao", ""), r.get("responsavel", ""), prazo_br(r.get("prazo")), r.get("status_acao", "")] for r in registros],
                            [doc.width*f for f in [.23,.36,.16,.10,.15]]),
                     PageBreak(), p("Atividades e controles", "TituloRisco"),
                     tabela(["Atividade / NR", "Severidade / validação", "Perigos e riscos", "Controles atuais"],
                            [[str(r.get("atividade", "")) + "\nNR: " + str(r.get("nr", "")),
                              str(r.get("consequencia", "")) + "\n" + str(r.get("validacao", "")),
                              r.get("riscos", ""), r.get("controles", "")] for r in registros],
                            [doc.width*f for f in [.23,.20,.27,.30]]),
                     PageBreak(), p("Cenários e reavaliação", "TituloRisco"),
                     tabela(["Atividade", "Cenário / lacuna", "Hierarquia / evidência", "Risco residual"],
                            [[r.get("atividade", ""), str(r.get("cenario", "")) + "\nLacuna: " + str(r.get("lacuna", "")),
                              str(r.get("hierarquia", "")) + "\nEvidência: " + str(r.get("evidencia", "")),
                              "Probabilidade: " + str(r.get("probabilidade_residual", "")) + "\nSeveridade: " + str(r.get("severidade_residual", "")) + "\nNível: " + str(r.get("nivel_residual", ""))] for r in registros],
                            [doc.width*f for f in [.22,.29,.29,.20]])]
    else:
        historia.append(p("Nenhuma atividade para os filtros selecionados."))

    def rodape(canvas, documento):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#cbd5e1"))
        canvas.line(doc.leftMargin, 12*mm, landscape(A4)[0]-doc.rightMargin, 12*mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawString(doc.leftMargin, 8*mm, "10 Sul | Mapa de riscos | Segurança do trabalho")
        canvas.drawRightString(landscape(A4)[0]-doc.rightMargin, 8*mm, f"Página {documento.page}")
        canvas.restoreState()
    doc.build(historia, onFirstPage=rodape, onLaterPages=rodape)
    return saida.getvalue()
