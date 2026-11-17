export function rhSlot(now) {
  const p=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:'America/Sao_Paulo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',hourCycle:'h23'}).formatToParts(now).map(x=>[x.type,x.value]));
  return {today:`${p.year}-${p.month}-${p.day}`,hour:p.hour,due:['09','13','16'].includes(p.hour)};
}
export function summarizeRh(rows, frequency, reference, today, classify) {
  const people=[...new Map(rows.filter(c=>c.ativo && (!c.data_admissao || c.data_admissao<=today) && (!c.data_desligamento || c.data_desligamento>=today)).map(c=>[String(c.id),c])).values()];
  const counts={registrados:people.length,outros:0,operacionais:0,spot:0,pendentes:0};
  const situations={FE:{total:0,SPOT:0,OUTROS:0,OPERACIONAL:0},FA:{total:0,SPOT:0,OUTROS:0,OPERACIONAL:0},AF:{total:0,SPOT:0,OUTROS:0,OPERACIONAL:0}};
  const map=new Map(frequency.map(f=>[String(f.colaborador_id),String(f.codigo||'').trim().toUpperCase()]));
  for(const c of people){
    const cls=classify(c)==='OPERACIONAL'?'OPERACIONAL':'OUTROS';
    const spot=String(c.tipo_contratacao||'').trim().toUpperCase()==='SPOT';
    counts[cls==='OPERACIONAL'?'operacionais':'outros']++;if(spot)counts.spot++;
    const code=map.get(String(c.id));if(!code)counts.pendentes++;
    if(situations[code]){situations[code].total++;situations[code][spot?'SPOT':cls]++;}
  }
  return {today,reference,counts,situations};
}
export function rhSummaryAlert(summary, now) {
  const slot=rhSlot(now);if(!slot.due)return null;
  const {counts:c,situations:s,reference:r}=summary;
  const fmt=d=>d?.split('-').reverse().join('/')||'sem lançamentos';
  const parts=[`Referência: ${fmt(r)}`,`Registrados: ${c.registrados} | Outros: ${c.outros} | Operacionais: ${c.operacionais} | Spot: ${c.spot}`];
  if(r)for(const [code,label] of [['FE','Férias'],['FA','Faltas'],['AF','Afastados']]){const q=s[code];parts.push(`${label}: ${q.total} (Spot ${q.SPOT} / Outros ${q.OUTROS} / Operacional ${q.OPERACIONAL})`);}
  else parts.push('Férias, faltas e afastamentos: sem referência preenchida.');
  parts.push(`Sem lançamento na referência: ${c.pendentes}`);
  return {key:`rh:quadro:${slot.today}:${slot.hour}`,kind:'rh_quadro',title:`PORTAL RH — QUADRO ${slot.hour}H`,body:parts.join('\n'),url:'https://10sul-app-rh-jacpdfktaczhihbjnuucm2.streamlit.app/'};
}
