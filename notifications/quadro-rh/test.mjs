import assert from 'node:assert/strict';
import {rhSlot,summarizeRh,rhSummaryAlert} from './rh-summary.mjs';
import {deliveryDue} from './rules.mjs';
const rows=[{id:1,ativo:true,tipo_contratacao:'SPOT'},{id:2,ativo:true},{id:3,ativo:true,data_desligamento:'2026-11-16'},{id:4,ativo:true}];
const s=summarizeRh(rows,[{colaborador_id:1,codigo:'AF'},{colaborador_id:2,codigo:'FE'}],'2026-11-05','2026-11-17',()=> 'OPERACIONAL');
assert.equal(s.counts.registrados,3);assert.equal(s.situations.AF.SPOT,1);assert.equal(s.counts.pendentes,1);
for(const h of ['09','13','16']){const now=Date.parse(`2026-11-17T${h}:00:00-03:00`);const a=rhSummaryAlert(s,now);assert.ok(a.body.includes('05/11/2026'));assert.equal(deliveryDue(a,{sent_at:new Date(now).toISOString()},now+60000),false);}
assert.equal(rhSummaryAlert(s,Date.parse('2026-11-17T10:00:00-03:00')),null);
assert.equal(rhSlot(Date.parse('2026-11-18T01:00:00Z')).today,'2026-11-17');
assert.ok(rhSummaryAlert({...s,reference:null},Date.parse('2026-11-17T09:00:00-03:00')).body.includes('sem referência'));
console.log('PASS: horários de Brasília, referência, tipos, vínculos, pendências e entrega única.');
