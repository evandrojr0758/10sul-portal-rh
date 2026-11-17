// Pure rules shared by the background sender and its tests. All timestamps
// without an offset come from the Brazilian local-time source, not UTC.
export const HOUR = 60 * 60 * 1000;
export const MONITOR_URL = 'https://10sul-monitor-gerencial-tah7ewvdikufrddrrysy56.streamlit.app/';
export const VEHICLES_URL = 'https://controle-veiculos-jpnsn36kukknr96dv9noma.streamlit.app/?view=admin&tab=veiculos';
export const STOCK_URL = 'https://10sul-estoque-cocb.streamlit.app/?pagina=painel';

// A date key deduplicates all minute checks and retries during the 08h window.
// Explicit IANA timezone keeps the schedule independent of the server clock.
export function stockAlerts(now) {
  if (!Number.isFinite(now)) throw new Error('Horário de verificação inválido.');
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/Sao_Paulo', weekday: 'short', year: 'numeric',
    month: '2-digit', day: '2-digit', hour: '2-digit', hourCycle: 'h23',
  }).formatToParts(now).map(part => [part.type, part.value]));
  if (!['Tue', 'Thu'].includes(parts.weekday) || parts.hour !== '08') return [];
  return [{key: `estoque:socorro:${parts.year}-${parts.month}-${parts.day}`,
    group: 'oficina', kind: 'estoque_socorro', title: '⚠️ ATENÇÃO!',
    body: 'Requisitar material para direcionar ao COCB e ITABATAN', url: STOCK_URL}];
}
const norm = value => String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toUpperCase();
const id = value => String(value ?? '').trim().replace(/\.0$/, '');
const key = row => `${id(row.os_id)}:${id(row.frota)}`;

export function eventLabel(value) {
  const event = norm(value).replace(/\s+/g, ' ');
  if (/^(?:CORRETIVA (?:N|NAO) PROG\.?|CNP)(?: PNEU)?$/.test(event)) {
    return event.endsWith(' PNEU') ? 'CNP PNEU' : 'CNP';
  }
  return String(value ?? '').trim();
}
const localDateTime = value => new Intl.DateTimeFormat('pt-BR', {
  timeZone:'America/Sao_Paulo', dateStyle:'short', timeStyle:'short',
}).format(value);
function returnBody(r, count) {
  const minutes = Math.floor((r.start-r.end)/60000);
  const days = Math.floor(minutes/1440), hours = Math.floor(minutes%1440/60);
  const elapsed = `${days}d ${hours}h ${String(minutes%60).padStart(2,'0')}min`;
  const description = String(r.row.descricao ?? '').trim().replace(/\s+/g,' ');
  return `Frota ${id(r.row.frota)} • ${eventLabel(r.row.evento)} • OS ${id(r.row.os_id)}\nÚltima ITR: ${localDateTime(r.end)}\nParada: ${localDateTime(r.start)}\nTempo desde a ITR: ${elapsed}\nDescrição: ${description || 'Não informada na ASN'}\nQtd. paradas após ITR: ${count}`;
}

export function timestamp(value) {
  if (!value || !String(value).trim()) return null;
  let text = String(value).trim().replace(' ', 'T');
  // PostgreSQL renders timestamptz offsets as +00 as well as +00:00.
  if (/T.*[+-]\d{2}$/.test(text)) text += ':00';
  const local = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(text) ? text : `${text}-03:00`;
  const date = Date.parse(local);
  return Number.isFinite(date) ? date : null;
}

export function combineMonitor(history, asn) {
  if (!asn.length) throw new Error('A origem ASN está vazia; não emitir alertas com uma base incompleta.');
  const records = new Map(history.map(row => [key(row), {...row, fim_asn: row.fim_asn ?? null}]));
  for (const row of asn) {
    const saved = records.get(key(row));
    const result = {...saved};
    for (const field of ['os_id', 'frota', 'evento', 'status', 'parada', 'descricao', 'modal', 'unidade', 'local_manutencao', 'excluida_asn_em']) {
      result[field] = row[field];
    }
    // ASN null values deliberately override an old closure when an OS reopens.
    result.fim_asn = row.fim ?? null;
    result.inicio = timestamp(saved?.inicio) === null ? row.inicio : saved.inicio;
    records.set(key(row), result);
  }
  return [...records.values()];
}

export function monitorAlerts(rows, now, acknowledged = new Set()) {
  if (!Number.isFinite(now)) throw new Error('Horário de verificação inválido.');
  const alerts = [];
  const pending = [];
  const sos = new Map();
  for (const row of rows) {
    if (row.excluida_asn_em || row.ausente_abertas_asn_em) continue;
    if (norm(row.unidade) !== 'ARA' || !norm(row.status).includes('MANUT')) continue;
    if (timestamp(row.fim_asn) !== null || timestamp(row.fim_liberacao_10sul) !== null) continue;
    const event = norm(row.evento);
    const start = timestamp(row.inicio) ?? timestamp(row.parada);
    if (event.startsWith('SOS') && start !== null && now - start >= 2 * HOUR && !acknowledged.has(`sos:${key(row)}`)) {
      sos.set(key(row), {os_id:id(row.os_id), frota:id(row.frota), start, local_manutencao:String(row.local_manutencao ?? '').trim().replace(/\s+/g,' ')});
    }
    if ((event === 'ITR' || event.includes('REVIS')) && timestamp(row.previsao_liberacao_10sul) === null) {
      pending.push({os_id: id(row.os_id), frota: id(row.frota), evento: row.evento});
    }
  }
  if (sos.size) {
    const records = [...sos.values()].sort((a,b)=>a.start-b.start || a.frota.localeCompare(b.frota) || a.os_id.localeCompare(b.os_id));
    const members = records.map(r=>`${r.os_id}:${r.frota}`).sort();
    const lines = records.map(r=>{
      const minutes=Math.floor((now-r.start)/60000);
      return `Frota ${r.frota} • ${Math.floor(minutes/60)}h ${String(minutes%60).padStart(2,'0')}min • ${r.local_manutencao ? (r.local_manutencao.length>120?r.local_manutencao.slice(0,117)+'…':r.local_manutencao) : 'Local não informado'}`;
    });
    // Stable display tag replaces the previous phone notification. Membership
    // identifies delivery state so a newly overdue SOS triggers immediately.
    let body=lines.join('\n');
    if(body.length>900) {
      const shown=[];let size=0;
      for(const line of lines) {if(size+line.length>800)break;shown.push(line);size+=line.length+1;}
      body=shown.join('\n')+`\n+ ${lines.length-shown.length} atendimento(s). Toque para ver todos.`;
    }
    alerts.unshift({key:`sos:grupo:${JSON.stringify(members)}`,tag:'sos:grupo',group:'oficina',kind:'sos',
      title:`🔴 ATENÇÃO — SOS COM 2H OU MAIS — ${new Set(records.map(r=>r.frota)).size} CARRETA(S)`,
      body,records,url:'https://central-10sul.peachycrown16.chatgpt.site/sos.html'});
  }
  if (pending.length) {
    const fleets = [...new Set(pending.map(row => row.frota))].sort();
    alerts.push({
      key: `previsao:${Math.floor(now / HOUR)}`, group: 'oficina', kind: 'previsao',
      title: '⚠️ PREVISÃO DE LIBERAÇÃO PENDENTE',
      body: `Favor informar a previsão das carretas de ITR e REVISÃO: ${fleets.join(', ')}.`,
      records: pending, url: MONITOR_URL,
    });
  }
  return alerts;
}

// The sender supplies an activation cut-off so old movements never become
// false "just departed/arrived" notifications during first initialization.
export function vehicleAlerts(movements, now, activation) {
  if (!Number.isFinite(now) || !Number.isFinite(activation)) throw new Error('Horário de verificação inválido.');
  const alerts = [];
  for (const row of movements) {
    const movementId = id(row.id);
    if (!movementId || !id(row.placa)) continue;
    const plate = norm(row.placa);
    const start = timestamp(row.data_hora_saida);
    const end = timestamp(row.data_hora_retorno);
    const base = {group: 'veiculos_gerencial', url: VEHICLES_URL};
    if (start !== null && start >= activation && start <= now) {
      alerts.push({...base, key: `veiculo:saida:${movementId}`, kind: 'veiculo_saida',
        title: `🚙 VEÍCULO ${plate} INDO PARA ${String(row.destino ?? '').trim()}`,
        body: row.condutor?.trim() ? `Conduzido por ${row.condutor.trim()}.` : `Ocupantes informados: ${String(row.pessoas ?? '').trim()}. Condutor não identificado no registro.`,
      });
    }
    if (end !== null && end >= activation && end <= now && norm(row.status) === 'DEVOLVIDO' && row.km_final !== null && row.km_final !== undefined && Number.isFinite(Number(row.km_final))) {
      alerts.push({...base, key: `veiculo:retorno:${movementId}`, kind: 'veiculo_retorno',
        title: `✅ VEÍCULO ${plate} ACABA DE CHEGAR`,
        body: `Retorno finalizado • KM final: ${Number(row.km_final).toLocaleString('pt-BR')} km.`,
      });
    }
    if (norm(row.status) === 'EM USO' && end === null && start !== null && now - start > 2 * HOUR) {
      alerts.push({...base, key: `veiculo:atraso:${movementId}`, kind: 'veiculo_atraso',
        title: `⚠️ VEÍCULO ${plate} AINDA NÃO RETORNOU`,
        body: `Mais de 2h em uso • Destino: ${String(row.destino ?? '').trim()}.`,
      });
    }
  }
  return alerts;
}

export function eligibleAlerts(alerts, device, sent, now) {
  if (!device.enabled) return [];
  return alerts.filter(alert => {
    if (alert.group === 'veiculos_gerencial' && !device.manager_authorized) return false;
    if (alert.group === 'oficina' && !device.oficina_enabled) return false;
    const previous = sent.get(alert.key);
    if (previous !== undefined) return false;
    // Hour buckets identify reminders, while this separate guard guarantees
    // an actual hour between deliveries even across a bucket boundary.
    if (alert.kind === 'previsao' && Number.isFinite(device.last_forecast_at) && now - device.last_forecast_at < HOUR) return false;
    return true;
  });
}

// SOS reminders recur an actual hour after the last successful delivery.
// Other notification types preserve their existing one-delivery rule.
export function deliveryDue(alert, prior, now) {
  if (prior?.sent_at && (!['sos','resumo_oficina'].includes(alert.kind) || now - new Date(prior.sent_at).getTime() < HOUR)) return false;
  if (prior?.last_attempt_at && now - new Date(prior.last_attempt_at).getTime() < Math.min(HOUR, 60000 * Math.pow(2, Math.min(prior.attempts - 1, 6)))) return false;
  return true;
}

/** One recurring summary per device, counting distinct fleets rather than OS. */
export function maintenanceSummary(rows, now, checkedAt) {
  if (!Number.isFinite(now)) throw new Error('Horário de verificação inválido.');
  const checked = timestamp(checkedAt);
  if (checked === null || checked > now + 60000 || now - checked > 90 * 60000) {
    return {key:'resumo:oficina',group:'oficina',kind:'resumo_oficina',
      title:'⚠️ CONFERÊNCIA DA ASN PENDENTE',
      body:'A consulta completa da ASN precisa ser atualizada. Quantidades de carretas temporariamente indisponíveis.',
      counts:null,total:null,url:MONITOR_URL};
  }
  const modals = new Set(['BITREM', 'SUPER BITREM', 'KNNAR', 'TRITREM', 'DEPOSITO', 'QUADRITREM', 'PENTATREM']);
  const groups = {cnp: new Set(), pneus: new Set(), sos: new Set(), itr: new Set(), revisao: new Set(), outros: new Set()};
  const total = new Set();
  for (const row of rows) {
    if (row.excluida_asn_em || row.ausente_abertas_asn_em || norm(row.unidade) !== 'ARA' || norm(row.status) !== 'MANUTENCAO') continue;
    // The workshop list follows the client's ASN closure. An internal 10 Sul
    // completion suppresses action reminders, but does not remove this fleet.
    if (!modals.has(norm(row.modal)) || timestamp(row.fim_asn) !== null) continue;
    const fleet = id(row.frota), event = norm(row.evento);
    if (!fleet) continue;
    const group = event === 'CORRETIVA N PROG. PNEU' ? 'pneus' :
      event === 'CORRETIVA N PROG.' ? 'cnp' :
      event.startsWith('SOS') ? 'sos' : event === 'ITR' ? 'itr' :
      event.startsWith('REVISAO') ? 'revisao' : 'outros';
    groups[group].add(fleet); total.add(fleet);
  }
  const counts = Object.fromEntries(Object.entries(groups).map(([name, fleets]) => [name, fleets.size]));
  const checkedText = localDateTime(checked);
  const overlap = Object.values(counts).reduce((sum,count)=>sum+count,0)>total.size;
  return {
    key:'resumo:oficina', group:'oficina', kind:'resumo_oficina',
    title:'🔧 CARRETAS EM MANUTENÇÃO — ARACRUZ',
    body:`CNP: ${counts.cnp}\nCNP PNEU: ${counts.pneus}\nSOS: ${counts.sos}\nITR: ${counts.itr}\nREVISÃO: ${counts.revisao}${counts.outros ? `\nOUTROS: ${counts.outros}` : ''}\nTotal: ${total.size} carretas distintas${overlap ? '\nHá frotas em mais de um evento.' : ''}\nASN conferida: ${checkedText}`,
    counts, total:total.size, url:MONITOR_URL,
  };
}


export function itrReturns(rows, now) {
  const unique = [...new Map(rows.filter(r => !r.excluida_asn_em && norm(r.unidade)==='ARA').map(r => [key(r), r])).values()];
  const latest = new Map();
  for (const r of unique) {
    const end = timestamp(r.fim_liberacao_10sul) ?? timestamp(r.fim_asn);
    if (norm(r.evento)!=='ITR' || end===null || end>now || !id(r.frota)) continue;
    if (!latest.has(id(r.frota)) || latest.get(id(r.frota)).end<end) latest.set(id(r.frota), {row:r,end});
  }
  const result=[];
  for (const r of unique) {
    const itr=latest.get(id(r.frota)), event=norm(r.evento), start=timestamp(r.parada) ?? timestamp(r.inicio);
    if (!itr || start===null || start>now || !(event.includes('CORRETIVA') || /^(SOS|CNP)\b/.test(event)) || key(r)===key(itr.row)) continue;
    if (start>=itr.end && start-itr.end<=120*HOUR) result.push({row:r,itr:itr.row,end:itr.end,start});
  }
  return result;
}
export function itrReturnAlerts(rows, now, activation) {
  const returns=itrReturns(rows,now), counts=new Map();
  for(const r of returns) counts.set(id(r.row.frota),(counts.get(id(r.row.frota))||0)+1);
  return returns.filter(r=>r.start>=activation || (norm(r.row.status).includes('MANUT') && timestamp(r.row.fim_asn)===null && timestamp(r.row.fim_liberacao_10sul)===null)).map(r=>({
    key:`retorno_itr:${key(r.itr)}:${key(r.row)}`,group:'oficina',kind:'retorno_itr',
    title:'🚨 RETORNO EM ATÉ 5 DIAS APÓS ITR',
    body:returnBody(r, counts.get(id(r.row.frota))),
    url:MONITOR_URL
  }));
}

export function rhExpiryAlerts(rows, now) {
  const parts=Object.fromEntries(new Intl.DateTimeFormat('en-US',{timeZone:'America/Sao_Paulo',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(now).map(p=>[p.type,p.value]));
  const today=Date.parse(`${parts.year}-${parts.month}-${parts.day}T00:00:00Z`);
  const alerts=[];
  const fields={venc_aso:'ASO',venc_integracao_fabrica:'Integração fábrica',venc_integracao_unf:'Integração UNF Florestal'};
  for(const row of rows) {
    if(!row.ativo || norm(row.status)==='INATIVO') continue;
    if(row.data_desligamento && Date.parse(String(row.data_desligamento).slice(0,10)+'T00:00:00Z')<today) continue;
    for(const [field,label] of Object.entries(fields)) {
      const value=String(row[field]||'').slice(0,10);
      if(!/^\d{4}-\d{2}-\d{2}$/.test(value)) continue;
      const days=Math.round((Date.parse(value+'T00:00:00Z')-today)/86400000);
      if(days>30 || !Number.isFinite(days)) continue;
      const stage=days<=0?'vencido':'30dias';
      const text=days<0?`vencido há ${-days} dia(s)`:days===0?'vence hoje':`vence em ${days} dia(s)`;
      alerts.push({key:`rh:vencimento:${row.id}:${field}:${value}:${stage}`,kind:'rh_vencimento',
        title:'PORTAL RH — VENCIMENTO',body:`${row.colaborador} — ${label}: ${text} (${value.split('-').reverse().join('/')}).`,
        url:'https://10sul-app-rh-jacpdfktaczhihbjnuucm2.streamlit.app/?vencimentos=1'});
    }
  }
  return alerts;
}

