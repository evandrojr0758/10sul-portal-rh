"""Preenche o modelo Excel do mapa de riscos preservando gráficos e estilos."""
from collections import Counter
from copy import deepcopy
from datetime import date, datetime
from io import BytesIO
from math import ceil
from pathlib import Path
import base64
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED
from zoneinfo import ZoneInfo

X = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
C = 'http://schemas.openxmlformats.org/drawingml/2006/chart'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
ET.register_namespace('x', X)
ET.register_namespace('c', C)
ET.register_namespace('a', A)
ET.register_namespace('r', 'http://schemas.openxmlformats.org/officeDocument/2006/relationships')
CATS = ['Fatalidade possível', 'Amputação possível', 'Afastamento possível', 'Lesão sem afastamento possível', 'Baixo potencial', 'A validar']
STATUS = ['Não iniciada', 'Em andamento', 'Concluída']
CAMPOS = [
    ['id', 'atividade', 'consequencia', 'severidade', 'validacao', 'riscos', 'controles', 'cenario', 'nr'],
    ['id', 'atividade', 'lacuna', 'acao', 'hierarquia', 'responsavel', 'prazo', 'status_acao', 'evidencia', 'probabilidade_residual', 'severidade_residual', 'nivel_residual'],
]


def _q(nome):
    return '{' + X + '}' + nome


def _valor(celula, valor):
    for filho in list(celula):
        celula.remove(filho)
    if isinstance(valor, (int, float)):
        celula.set('t', 'n')
        ET.SubElement(celula, _q('v')).text = str(valor)
    else:
        celula.set('t', 'inlineStr')
        texto = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', str(valor or ''))[:32767]
        t = ET.SubElement(ET.SubElement(celula, _q('is')), _q('t'))
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        t.text = texto


def gerar_excel_riscos(df, filtros='Todos os registros', agora=None):
    registros = df.fillna('').to_dict('records')
    instante = agora or datetime.now(ZoneInfo('America/Sao_Paulo'))
    modelo = base64.b64decode(Path(__file__).with_name('assets').joinpath('riscos_excel_template.b64').read_text())
    with ZipFile(BytesIO(modelo)) as entrada:
        arquivos = {nome: entrada.read(nome) for nome in entrada.namelist()}
    ultimo = max(6, 5 + len(registros))
    for numero, campos in [(2, CAMPOS[0]), (3, CAMPOS[1])]:
        nome = f'xl/worksheets/sheet{numero}.xml'
        raiz = ET.fromstring(arquivos[nome])
        dados = raiz.find(_q('sheetData'))
        modelos = [deepcopy(r) for r in dados if r.get('r') in ('6', '7')]
        for linha in list(dados):
            if int(linha.get('r')) >= 6:
                dados.remove(linha)
        larguras = [float(c.get('width')) for c in raiz.find(_q('cols'))]
        for i, registro in enumerate(registros):
            linha = deepcopy(modelos[i % 2])
            linha.set('r', str(i + 6))
            altura = 30
            for j, celula in enumerate(linha):
                coluna = re.sub(r'\d', '', celula.get('r'))
                celula.set('r', f'{coluna}{i+6}')
                valor = registro.get(campos[j], '')
                if campos[j] == 'prazo' and valor:
                    try:
                        valor = (date.fromisoformat(str(valor)[:10]) - date(1899, 12, 30)).days
                    except ValueError:
                        pass
                _valor(celula, valor)
                linhas = sum(max(1, ceil(len(s) / max(8, larguras[j] - 3))) for s in str(valor).split('\n'))
                altura = max(altura, linhas * 14 + 10)
            linha.set('ht', str(min(409, altura)))
            dados.append(linha)
        for cf in raiz.findall(_q('conditionalFormatting')):
            cf.set('sqref', re.sub(r'7$', str(ultimo), cf.get('sqref')))
            ancora = cf.get('sqref').split(':')[0]
            for regra in cf:
                if regra.get('type') == 'containsText' and regra.find(_q('formula')) is None:
                    ET.SubElement(regra, _q('formula')).text = 'ISNUMBER(SEARCH("' + regra.get('text').replace('"', '""') + '",' + ancora + '))'
        filtro = ET.Element(_q('autoFilter'), ref=f'A5:{chr(64+len(campos))}{ultimo}')
        raiz.insert(list(raiz).index(dados) + 1, filtro)
        propriedades = raiz.find(_q('sheetPr'))
        if propriedades is None:
            propriedades = ET.Element(_q('sheetPr'))
            raiz.insert(0, propriedades)
        ET.SubElement(propriedades, _q('pageSetUpPr'), fitToPage='1')
        ET.SubElement(raiz, _q('pageSetup'), orientation='landscape', paperSize='9', fitToWidth='1', fitToHeight='0')
        arquivos[nome] = ET.tostring(raiz, encoding='utf-8', xml_declaration=True)
    consequencias = Counter(r.get('consequencia') for r in registros)
    acoes = Counter(r.get('status_acao') for r in registros)
    valores = {'B5': len(registros), 'B6': sum(consequencias[c] for c in CATS[:2]),
               'B7': sum(consequencias[c] for c in CATS[2:4]),
               'B8': sum(r.get('validacao') != 'Validada' for r in registros),
               'B9': sum(bool(r.get('prazo') and str(r['prazo'])[:10] < instante.date().isoformat() and r.get('status_acao') != 'Concluída') for r in registros)}
    valores.update({f'B{i+14}': consequencias[c] for i, c in enumerate(CATS)})
    valores.update({f'B{i+26}': acoes[c] for i, c in enumerate(STATUS)})
    raiz = ET.fromstring(arquivos['xl/worksheets/sheet1.xml'])
    for celula in raiz.iter(_q('c')):
        ref = celula.get('r')
        if ref == 'A3':
            _valor(celula, 'Emitido em ' + instante.strftime('%d/%m/%Y %H:%M') + ' (Brasília)')
        if ref in valores:
            formula = celula.find(_q('f'))
            if formula is not None:
                formula.text = re.sub(r'([A-Z])7\b', lambda m: m[1] + str(ultimo), formula.text)
            celula.set('t', 'n')
            v = celula.find(_q('v'))
            if v is None:
                v = ET.SubElement(celula, _q('v'))
            v.text = str(valores[ref])
    arquivos['xl/worksheets/sheet1.xml'] = ET.tostring(raiz, encoding='utf-8', xml_declaration=True)
    # Escopo completo em linha própria, sem ocupar a área dos gráficos.
    for numero in (2, 3):
        nome = f'xl/worksheets/sheet{numero}.xml'
        raiz = ET.fromstring(arquivos[nome])
        celula = next(c for c in raiz.iter(_q('c')) if c.get('r') == 'A4')
        _valor(celula, 'Filtros: ' + filtros)
        arquivos[nome] = ET.tostring(raiz, encoding='utf-8', xml_declaration=True)
    for nome in [n for n in arquivos if '/charts/' in n and n.endswith('.xml')]:
        raiz = ET.fromstring(arquivos[nome])
        primeiro = 'chart1.' in nome
        quantidades = [consequencias[c] for c in CATS] if primeiro else [acoes[c] for c in STATUS]
        paleta = ['DC2626', 'EF4444', 'EAB308', 'FACC15', '16A34A', '64748B'] if primeiro else ['64748B', 'EAB308', '16A34A']
        for cache in raiz.findall('.//{' + C + '}numCache'):
            for filho in list(cache):
                if filho.tag.endswith('}pt') or filho.tag.endswith('}ptCount'):
                    cache.remove(filho)
            ET.SubElement(cache, '{' + C + '}ptCount', val=str(len(quantidades)))
            for i, valor in enumerate(quantidades):
                ET.SubElement(ET.SubElement(cache, '{' + C + '}pt', idx=str(i)), '{' + C + '}v').text = str(valor)
        for serie in raiz.findall('.//{' + C + '}ser'):
            for i, cor in enumerate(paleta):
                ponto = ET.Element('{' + C + '}dPt')
                ET.SubElement(ponto, '{' + C + '}idx', val=str(i))
                ET.SubElement(ET.SubElement(ET.SubElement(ponto, '{' + C + '}spPr'), '{' + A + '}solidFill'), '{' + A + '}srgbClr', val=cor)
                pos = next((j for j, child in enumerate(serie) if child.tag in ('{' + C + '}cat', '{' + C + '}val')), len(serie))
                serie.insert(pos, ponto)
        for grafico in raiz.findall('.//{' + C + '}barChart'):
            rotulos = grafico.find('{' + C + '}dLbls')
            if rotulos is None:
                rotulos = ET.Element('{' + C + '}dLbls')
                pos = next((j for j, child in enumerate(grafico)
                            if child.tag in ('{' + C + '}gapWidth', '{' + C + '}overlap',
                                             '{' + C + '}serLines', '{' + C + '}axId')),
                           len(grafico))
                grafico.insert(pos, rotulos)
            else:
                rotulos.clear()
            ET.SubElement(rotulos, '{' + C + '}numFmt', formatCode='0', sourceLinked='0')
            ET.SubElement(rotulos, '{' + C + '}dLblPos', val='outEnd')
            for campo, valor in [('showLegendKey', '0'), ('showVal', '1'),
                                 ('showCatName', '0'), ('showSerName', '0'),
                                 ('showPercent', '0'), ('showBubbleSize', '0')]:
                ET.SubElement(rotulos, '{' + C + '}' + campo, val=valor)
        for eixo in raiz.findall('.//{' + C + '}valAx'):
            escala = eixo.find('{' + C + '}scaling')
            ET.SubElement(escala, '{' + C + '}min', val='0')
            ET.SubElement(eixo, '{' + C + '}majorUnit', val=str(max(1, ceil(max(quantidades, default=0)/5))))
        arquivos[nome] = ET.tostring(raiz, encoding='utf-8', xml_declaration=True)
    saida = BytesIO()
    with ZipFile(saida, 'w', ZIP_DEFLATED) as z:
        for nome, conteudo in arquivos.items():
            z.writestr(nome, conteudo)
    return saida.getvalue()
