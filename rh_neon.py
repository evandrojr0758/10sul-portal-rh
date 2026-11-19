"""Database and private file access for the Streamlit Portal RH."""

import csv
import re
from functools import lru_cache
from urllib.parse import parse_qsl

import psycopg
from psycopg import sql
from psycopg.types.json import Json, Jsonb


_OPERADORES = {
    "eq": "=", "neq": "<>", "gt": ">", "gte": ">=", "lt": "<", "lte": "<=",
    "like": "LIKE", "ilike": "ILIKE",
}
_OPCOES = {"select", "order", "limit", "offset", "on_conflict"}
_RPC = {
    "rh_importar_ponto": ("p_arquivo", "p_hash", "p_unidade", "p_usuario", "p_registros"),
    "rh_excluir_importacao_ponto": ("p_id", "p_unidade", "p_usuario"),
}
_BUCKETS = {
    "rh-ocorrencias-anexos", "rh-cadastro-aracruz", "rh-fechamentos-aracruz",
    "rh-fechamentos-cmc", "rh-fechamentos-tres-lagoas",
}


def _identificador(nome):
    if not re.fullmatch(r"[a-z_][a-z_0-9]*", nome):
        raise ValueError("Identificador inválido na consulta de RH.")
    return sql.Identifier(nome)


def _campo(nome):
    coluna, sep, chave = nome.partition("->>")
    if sep:
        return sql.SQL("{} ->> {}").format(_identificador(coluna), sql.Literal(chave))
    return _identificador(coluna)


def _campos(valor):
    if valor == "*":
        return sql.SQL("*")
    return sql.SQL(", ").join(_campo(coluna) for coluna in valor.split(","))


def _where(filtros, valores):
    condicoes = []
    for campo, filtro in filtros:
        negativa = filtro.startswith("not.")
        op, separador, valor = filtro.removeprefix("not.").partition(".")
        if not separador:
            raise ValueError("Filtro inválido na consulta de RH.")
        campo_sql = _campo(campo)
        if op == "is" and valor in ("null", "true", "false"):
            condicao = sql.SQL("{} IS {}").format(campo_sql, sql.SQL(valor.upper()))
        elif op == "in" and valor.startswith("(") and valor.endswith(")"):
            itens = next(csv.reader([valor[1:-1]], strict=True))
            if itens:
                condicao = sql.SQL("{} IN ({})").format(
                    campo_sql, sql.SQL(", ").join(sql.Placeholder() for _ in itens))
                valores.extend(itens)
            else:
                condicao = sql.SQL("FALSE")
        elif op in _OPERADORES:
            condicao = sql.SQL("{} {} %s").format(campo_sql, sql.SQL(_OPERADORES[op]))
            valores.append(valor.replace("*", "%") if op in ("like", "ilike") else valor)
        else:
            raise ValueError("Operador inválido na consulta de RH.")
        if negativa:
            condicao = sql.SQL("NOT ({})").format(condicao)
        condicoes.append(condicao)
    return sql.SQL(" WHERE ") + sql.SQL(" AND ").join(condicoes) if condicoes else sql.SQL("")


def _ordem(valor):
    campos = []
    for item in valor.split(","):
        coluna, *opcoes = item.split(".")
        direcao = next((op.upper() for op in opcoes if op in ("asc", "desc")), "ASC")
        nulos = next((op for op in opcoes if op in ("nullsfirst", "nullslast")), None)
        if len(opcoes) != len(set(opcoes)) or any(
            op not in ("asc", "desc", "nullsfirst", "nullslast") for op in opcoes
        ) or {"asc", "desc"} <= set(opcoes) or {"nullsfirst", "nullslast"} <= set(opcoes):
            raise ValueError("Ordenação inválida na consulta de RH.")
        ordenado = sql.SQL("{} {}").format(_campo(coluna), sql.SQL(direcao))
        if nulos:
            ordenado += sql.SQL(" NULLS FIRST" if nulos == "nullsfirst" else " NULLS LAST")
        campos.append(ordenado)
    return sql.SQL(" ORDER BY ") + sql.SQL(", ").join(campos)


def _rpc(conn, method, tabela, params, payload):
    nome = tabela.removeprefix("rpc/")
    campos = _RPC.get(nome)
    if method != "POST" or params or not campos or not isinstance(payload, dict) or set(payload) != set(campos):
        raise ValueError("Função inválida na consulta de RH.")
    valores = [Jsonb(payload[c]) if c == "p_registros" else payload[c] for c in campos]
    stmt = sql.SQL("SELECT public.{}({})").format(
        _identificador(nome), sql.SQL(", ").join(sql.Placeholder() for _ in campos))
    return conn.execute(stmt, valores).fetchone()[0]


def _inserir(conn, tabela, payload, options, preferencias):
    linhas = payload if isinstance(payload, list) else [payload]
    if not linhas:
        return [] if "return=representation" in preferencias else None
    if not all(isinstance(linha, dict) and linha and linha.keys() == linhas[0].keys() for linha in linhas):
        raise ValueError("Campos inconsistentes no lançamento de RH.")
    nomes = list(linhas[0])
    colunas = sql.SQL(", ").join(map(_identificador, nomes))
    stmt = sql.SQL("INSERT INTO {} ({}) SELECT {} FROM json_populate_recordset(NULL::{}, %s)").format(
        tabela, colunas, colunas, tabela)
    conflito = options.get("on_conflict")
    if conflito:
        chaves = conflito.split(",")
        stmt += sql.SQL(" ON CONFLICT ({})").format(sql.SQL(", ").join(map(_identificador, chaves)))
        if "resolution=ignore-duplicates" in preferencias:
            stmt += sql.SQL(" DO NOTHING")
        elif "resolution=merge-duplicates" in preferencias:
            atualizar = [_identificador(c) for c in nomes if c not in chaves]
            if atualizar:
                stmt += sql.SQL(" DO UPDATE SET ") + sql.SQL(", ").join(
                    sql.SQL("{} = EXCLUDED.{}").format(c, c) for c in atualizar)
            else:
                stmt += sql.SQL(" DO NOTHING")
        else:
            raise ValueError("Resolução de duplicidade inválida no lançamento de RH.")
    return _executar_escrita(conn, stmt, [Json(linhas)], options, preferencias)


def _executar_escrita(conn, stmt, valores, options, preferencias):
    if "return=representation" not in preferencias:
        conn.execute(stmt, valores)
        return None
    stmt += sql.SQL(" RETURNING {}").format(_campos(options.get("select", "*")))
    stmt = sql.SQL("WITH dados AS ({}) SELECT row_to_json(dados) FROM dados").format(stmt)
    return [r[0] for r in conn.execute(stmt, valores)]


def consultar(dsn, method, tabela, params="", payload=None, prefer=None):
    """Execute the filter, ordering and mutation forms used by the portal."""
    with psycopg.connect(dsn, connect_timeout=8, prepare_threshold=None) as conn:
        conn.execute("SET LOCAL statement_timeout = '25s'")
        conn.execute("SET LOCAL TIME ZONE 'UTC'")
        if tabela.startswith("rpc/"):
            return _rpc(conn, method, tabela, params, payload)
        if not tabela.startswith("rh_"):
            raise ValueError("Tabela fora do Portal RH.")
        alvo = sql.SQL("public.{}").format(_identificador(tabela))
        pares = parse_qsl(params, keep_blank_values=True)
        options = {k: v for k, v in pares if k in _OPCOES}
        filtros = [(k, v) for k, v in pares if k not in _OPCOES]
        preferencias = {p.strip() for p in (prefer or "").split(",")}
        valores = []
        if method == "GET":
            where = _where(filtros, valores)
            stmt = sql.SQL("SELECT {} FROM {}").format(_campos(options.get("select", "*")), alvo) + where
            if "order" in options:
                stmt += _ordem(options["order"])
            limit, offset = int(options.get("limit", 1000)), int(options.get("offset", 0))
            if limit < 0 or offset < 0:
                raise ValueError("Paginação inválida na consulta de RH.")
            stmt += sql.SQL(" LIMIT %s OFFSET %s")
            stmt = sql.SQL("SELECT row_to_json(dados) FROM ({}) dados").format(stmt)
            return [r[0] for r in conn.execute(stmt, [*valores, min(1000, limit), offset])]
        if method == "POST" and not filtros:
            return _inserir(conn, alvo, payload, options, preferencias)
        if not filtros or any(k in options for k in ("limit", "offset", "order", "on_conflict")):
            raise ValueError("A alteração exige filtros de RH.")
        if method == "PATCH" and isinstance(payload, dict) and payload:
            colunas = sql.SQL(", ").join(map(_identificador, payload))
            stmt = sql.SQL("UPDATE {} SET ({}) = (SELECT {} FROM json_populate_record(NULL::{}, %s))").format(
                alvo, colunas, colunas, alvo)
            valores.append(Json(payload))
        elif method == "DELETE":
            stmt = sql.SQL("DELETE FROM {}").format(alvo)
        else:
            raise ValueError("Operação inválida na consulta de RH.")
        stmt += _where(filtros, valores)
        return _executar_escrita(conn, stmt, valores, options, preferencias)


@lru_cache(maxsize=4)
def _storage(endpoint, region, key, secret):
    import boto3
    from botocore.config import Config

    if not all((endpoint, region, key, secret)) or not endpoint.startswith("https://"):
        raise RuntimeError("Configure o armazenamento privado do Neon nos Secrets do Portal RH.")
    return boto3.client(
        "s3", endpoint_url=endpoint, region_name=region,
        aws_access_key_id=key, aws_secret_access_key=secret,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                      connect_timeout=8, read_timeout=35,
                      request_checksum_calculation="when_required",
                      response_checksum_validation="when_required"),
    )


def buckets(config):
    return [{"id": b["Name"]} for b in _storage(*config).list_buckets()["Buckets"]
            if b["Name"] in _BUCKETS]


def arquivo(config, method, bucket, caminho, dados=None, mime=None, *, upsert=True):
    from botocore.exceptions import ClientError

    if bucket not in _BUCKETS or not caminho:
        raise ValueError("Caminho inválido no armazenamento de RH.")
    s3 = _storage(*config)
    try:
        if method == "GET":
            with s3.get_object(Bucket=bucket, Key=caminho)["Body"] as body:
                return body.read()
        if method == "POST":
            opcoes = {} if upsert else {"IfNoneMatch": "*"}
            s3.put_object(Bucket=bucket, Key=caminho, Body=dados,
                          ContentType=mime or "application/octet-stream", **opcoes)
            return None
        if method == "DELETE":
            s3.delete_object(Bucket=bucket, Key=caminho)
            return None
    except ClientError as exc:
        codigo = exc.response["Error"]["Code"]
        if method == "GET" and codigo in ("NoSuchKey", "404", "NotFound"):
            raise FileNotFoundError("Arquivo de RH não encontrado.") from exc
        raise RuntimeError(f"Falha no armazenamento de RH ({codigo}).") from exc
    raise ValueError("Operação inválida no armazenamento de RH.")
