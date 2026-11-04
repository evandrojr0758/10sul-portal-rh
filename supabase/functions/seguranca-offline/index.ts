const encoder=new TextEncoder();
const url=Deno.env.get('SUPABASE_URL')!, key=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
const reply=(data:unknown,status=200)=>new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});
const b64=(b:Uint8Array)=>btoa(String.fromCharCode(...b)).replaceAll('+','-').replaceAll('/','_').replaceAll('=','');
const un64=(s:string)=>Uint8Array.from(atob(s.replaceAll('-','+').replaceAll('_','/')),c=>c.charCodeAt(0));
async function signingKey(){return crypto.subtle.importKey('raw',encoder.encode(key),{name:'HMAC',hash:'SHA-256'},false,['sign','verify']);}
async function token(user:any){const body=b64(encoder.encode(JSON.stringify({sub:user.id,scope:'seguranca-offline-v1',exp:Math.floor(Date.now()/1000)+86400*30})));return body+'.'+b64(new Uint8Array(await crypto.subtle.sign('HMAC',await signingKey(),encoder.encode(body))));}
async function api(table:string,params:string,method='GET',body?:unknown){const r=await fetch(url+'/rest/v1/'+table+'?'+params,{method,headers:{apikey:key,Authorization:'Bearer '+key,'Content-Type':'application/json',Prefer:'return=representation'},body:body===undefined?undefined:JSON.stringify(body)});if(!r.ok)throw new Error('Banco indisponível ('+r.status+')');const t=await r.text();return t?JSON.parse(t):[];}
async function all(table:string,params:string){const rows=[];for(let offset=0;offset<100000;offset+=1000){const part=await api(table,params+'&limit=1000&offset='+offset);rows.push(...part);if(part.length<1000)return rows;}throw Error('Base excedeu o limite de ativação');}
async function userFromToken(value:string){const [body,signature]=value.split('.');if(!body||!signature||!(await crypto.subtle.verify('HMAC',await signingKey(),un64(signature),encoder.encode(body))))throw Error('Sessão inválida');const p=JSON.parse(new TextDecoder().decode(un64(body)));if(p.scope!=='seguranca-offline-v1'||p.exp<Date.now()/1000||!Number.isSafeInteger(p.sub))throw Error('Sessão expirada');const users=await api('rh_usuarios','select=id,nome,usuario,perfil,ativo&id=eq.'+p.sub);const u=users[0];if(!u?.ativo||!['SEGURANCA','ADMIN'].includes(u.perfil))throw Error('Acesso negado');return u;}
const attempts=new Map<string,{count:number,since:number}>();
Deno.serve(async req=>{
 if(req.method!=='POST')return reply({error:'Método inválido'},405);
 try{
 const body=await req.json();let user;
 if(body.action==='login'){
  const ip=req.headers.get('x-forwarded-for')||'unknown';let a=attempts.get(ip);if(!a||Date.now()-a.since>600000)a={count:0,since:Date.now()};a.count++;attempts.set(ip,a);if(a.count>10)return reply({error:'Muitas tentativas. Aguarde 10 minutos.'},429);
  const username=String(body.usuario||'').trim().toLowerCase();if(!username||typeof body.senha!=='string'||body.senha.length>256)return reply({error:'Acesso inválido'},401);
  const users=await api('rh_usuarios','select=id,usuario,nome,perfil,ativo,senha_hash,trocar_senha&usuario=eq.'+encodeURIComponent(username)+'&limit=1');user=users[0];
  const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',encoder.encode(body.senha)))).map(v=>v.toString(16).padStart(2,'0')).join('');
  if(!user?.ativo||!['SEGURANCA','ADMIN'].includes(user.perfil)||user.senha_hash!==digest)return reply({error:'Usuário ou senha inválidos'},401);
  if(user.trocar_senha)return reply({error:'Troque a senha no Portal RH antes de ativar este computador.'},403);
  attempts.delete(ip);
  const [riscos,dna,colabs]=await Promise.all([all('rh_seguranca_riscos','select=*&order=id'),all('rh_dna_mensal','select=*&order=id'),all('rh_colaboradores','select=id,colaborador,destra,ativo,funcao&order=id')]);
  return reply({token:await token(user),usuario:{id:user.id,nome:user.nome,usuario:user.usuario,perfil:user.perfil},riscos,dna,colabs});
 }
 user=await userFromToken((req.headers.get('Authorization')||'').replace(/^Bearer /,''));
 const table=body.tabela,method=body.method;
 if(!['rh_seguranca_riscos','rh_dna_mensal','rh_colaboradores'].includes(table)||!['GET','PATCH','POST'].includes(method))return reply({error:'Operação não autorizada'},403);
 if(table==='rh_colaboradores'&&method!=='GET')return reply({error:'Cadastro de colaboradores é somente consulta'},403);
 const params=new URLSearchParams(String(body.params||''));
 const allowed=table==='rh_seguranca_riscos'?['select','id','atualizado_em','dados->>sync_uuid','order','limit']:table==='rh_dna_mensal'?['select','id','colaborador_id','competencia','atualizado_em','order','limit']:['select','order','limit'];
 for(const [name,value] of params){if(!allowed.includes(name)||value.length>300)return reply({error:'Filtro não autorizado'},400);}
 params.set('select',table==='rh_colaboradores'?'id,colaborador,destra,ativo,funcao':'*');params.set('limit','10000');
 if(method!=='GET'){
  if(method==='PATCH'&&!/^eq\.\d+$/.test(params.get('id')||''))return reply({error:'ID obrigatório'},400);
  const p=body.payload;if(!p||typeof p!=='object'||Array.isArray(p))return reply({error:'Registro inválido'},400);
  const fields=table==='rh_seguranca_riscos'?['dados','atualizado_em','atualizado_por']:['colaborador_id','competencia','quantidade','atualizado_em','atualizado_por'];
  if(Object.keys(p).some(k=>!fields.includes(k)))return reply({error:'Campo não autorizado'},400);
  if(table==='rh_dna_mensal'){
   if(!Number.isInteger(p.quantidade)||p.quantidade<0||p.quantidade>1000||!/^\d{4}-\d{2}-01$/.test(p.competencia)||!Number.isSafeInteger(p.colaborador_id))return reply({error:'DNA inválido'},400);
   // O prazo é conferido na data do lançamento offline; publicação pode ocorrer depois.
   const launched=new Date(p.atualizado_em);const [y,m]=p.competencia.split('-').map(Number);const deadline=new Date(Date.UTC(y,m,10,3));
   if(!Number.isFinite(+launched)||launched>=deadline||launched>new Date(Date.now()+300000))return reply({error:'Competência fechada ou data inválida. Regularize pelo Portal RH.'},409);
  }
  p.atualizado_por=user.nome||user.usuario;
 }
 const result=await api(table,params.toString(),method,method==='GET'?undefined:body.payload);return reply({result});
 }catch(e){return reply({error:String(e.message||'Falha na sincronização')},401);}
});
