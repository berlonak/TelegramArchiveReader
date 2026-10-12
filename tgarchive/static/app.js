// copyright by berlonak
// telegram: @Kilax123
'use strict';
// All user-provided text is rendered via textContent or escaped before innerHTML.
const $ = id => document.getElementById(id);
const state = { view:'home', category:'all', chats:[], allChats:[], chat:null, messages:[],
  hasOlder:false, hasNewer:false, busy:false, generation:0, stats:null, search:{offset:0,items:[],more:false},
  gallery:{offset:0,items:[],more:false,kind:'all'}, contacts:{offset:0,items:[],more:false}, viewer:[], viewerIndex:0, viewerTarget:null };
let toastTimeout;
const esc = value => String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = n => new Intl.NumberFormat(locale(),{notation:n>=1000000?'compact':'standard',maximumFractionDigits:1}).format(n||0);
const dayFormat = ts => new Date(ts*1000).toLocaleDateString(locale(),{day:'numeric',month:'long',year:'numeric'});
const timeFormat = ts => new Date(ts*1000).toLocaleTimeString(locale(),{hour:'2-digit',minute:'2-digit'});
const shortDate = ts => new Date(ts*1000).toLocaleDateString(locale(),{day:'2-digit',month:'short'});
function toast(message){const node=$('toast');node.textContent=message;node.classList.add('show');clearTimeout(toastTimeout);toastTimeout=setTimeout(()=>node.classList.remove('show'),3600)}
function errMessage(err){return err?.message||t('error.request')}
async function api(url, options={}){
  const response=await fetch(url,{credentials:'same-origin',...options});
  // A failed login is also 401: show its own reason (wrong password), not "session ended".
  if(response.status===401&&!url.includes('/auth/login')){showLogin();throw new Error(t('error.session'))}
  let data;try{data=await response.json()}catch{data={}}
  if(!response.ok){throw new Error(typeof data.detail==='string'?serverText(data.detail):t('error.http',{status:response.status}))}
  return data;
}
const postJSON = (url, body={}) => api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
function showLogin(){$('loginPage').hidden=false;$('appPage').hidden=true;$('loadingPage').hidden=true;$('passwordInput').value='';setTimeout(()=>$('passwordInput').focus(),100)}
function showApp(){$('loginPage').hidden=true;$('appPage').hidden=false;$('loadingPage').hidden=true}
const slug = c => (c.category==='channels'?'channel':c.category==='groups'?'group':c.category==='saved'?'saved':'');
function initials(title){const parts=String(title||'?').split(/\s+/).filter(Boolean);return (parts.length>1?parts[0][0]+parts[1][0]:String(title||'?').slice(0,2)).toUpperCase()}
function avatar(c){const wrap=document.createElement('div');wrap.className=`avatar ${slug(c)}`;wrap.textContent=initials(c.title);if(c.avatar_path){const img=document.createElement('img');img.src=`/api/avatar/${c.id}`;img.loading='lazy';img.alt='';img.onerror=()=>img.remove();wrap.appendChild(img)}return wrap}
function empty(message, icon='⌕'){const div=document.createElement('div');div.className='empty-state';div.innerHTML=`<strong>${esc(icon)}</strong>${esc(message)}`;return div}
function view(name){state.view=name;for(const id of ['home','chat','search','gallery','bookmarks','contacts']){$(id+'View').hidden=id!==name}for(const id of ['Home','Search','Gallery','Bookmarks','Contacts'])$('nav'+id).classList.toggle('active',id.toLowerCase()===name);$('sidebar').classList.remove('open');}
function populateSelectors(){for(const select of [$('searchChat'),$('galleryChat')]){const old=select.value;select.replaceChildren(new Option(t('search.allChats'),''));for(const c of state.allChats){select.appendChild(new Option(`${c.title} (${c.messages_count})`,c.id))}select.value=old}}
function showPersonalChats(){state.category='personal';for(const item of $('categoryFilters').querySelectorAll('button'))item.classList.toggle('selected',item.dataset.category==='personal');$('chatFilter').value='';loadChats();view('home');$('sidebar').classList.add('open')}
function loadChats(){const q=$('chatFilter').value.trim().toLocaleLowerCase(locale());const cat=state.category;state.chats=state.allChats.filter(c=>(cat==='all'||(cat==='left'?c.left_archive:c.category===cat))&&(!q||c.title.toLocaleLowerCase(locale()).includes(q)));renderChatList()}
async function loadAllChats(){let all=[],offset=0;while(true){const result=await api('/api/chats?'+new URLSearchParams({limit:1000,offset}));all.push(...result.items);if(result.items.length<1000||!result.has_more)break;offset+=result.items.length}return all}
function renderChatList(){$('sidebarCount').textContent=fmt(state.chats.length);const list=$('chatList');list.replaceChildren();if(!state.chats.length){list.appendChild(empty(t('chats.none')));return}const frag=document.createDocumentFragment();for(const c of state.chats){const b=document.createElement('button');b.className='chat-item'+(state.chat?.id===c.id&&state.view==='chat'?' active':'');b.appendChild(avatar(c));const body=document.createElement('div');body.className='chat-item-content';body.innerHTML=`<div class="chat-item-top"><b>${esc(c.title)}</b><span class="chat-item-time">${c.last_ts?shortDate(c.last_ts):''}</span></div><div class="chat-item-bottom"><span class="chat-item-preview">${c.left_archive?'↶ ':''}${esc(c.last_preview||chatKind(c))}</span><span class="chat-item-count">${fmt(c.messages_count)}</span></div>`;b.appendChild(body);b.addEventListener('click',()=>openChat(c.id));frag.appendChild(b)}list.appendChild(frag)}
function chatKind(c){return t('kind.'+(['channels','groups','saved','personal'].includes(c.category)?c.category:'other'))}
function renderChatHeader(c){$('chatHeaderMeta').textContent=`${chatKind(c)}${c.left_archive?t('chat.left'):''} · ${tn('chat.messages',c.messages_count,fmt(c.messages_count))}`}
function getChat(chatId){return state.allChats.find(c=>c.id===Number(chatId))||state.chats.find(c=>c.id===Number(chatId))||{id:Number(chatId),title:t('chat.untitled'),category:'personal',messages_count:0}}
async function renderStats(){try{state.stats=await api('/api/stats');const s=state.stats;$('lastImport').textContent=s.last_import?t('stats.updated',{date:dayFormat(s.last_import)}):t('stats.empty');const cards=[['◉',s.chats,t('stats.chats')],['▤',s.messages,t('stats.messages')],['▧',(s.media.photo||0),t('stats.photos')],['▶',(s.media.video||0)+(s.media.video_message||0),t('stats.videos')]];$('statCards').replaceChildren(...cards.map(([icon,num,label])=>{const x=document.createElement('div');x.className='stat-card';x.innerHTML=`<span class="symbol">${esc(icon)}</span><b>${fmt(num)}</b><small>${esc(label)}</small>`;return x}));}catch(e){toast(errMessage(e))}}
async function home(){state.chat=null;view('home');renderChatList();await renderStats()}
async function openChat(chatId, around=null){state.generation++;const generation=state.generation;state.chat=getChat(chatId);state.messages=[];state.hasOlder=false;state.hasNewer=false;state.busy=false;view('chat');renderChatList();const c=state.chat;$('chatHeaderTitle').textContent=c.title;renderChatHeader(c);$('chatHeaderAvatar').replaceChildren(avatar(c));$('messageStream').replaceChildren(empty(t('chat.loading'),'◌'));$('messageLoad').replaceChildren();$('messageLoadNew').replaceChildren();$('latestButton').hidden=true;$('calendarPanel').hidden=true;try{const params=new URLSearchParams({limit:60});if(around)params.set('around',around);const result=await api(`/api/chats/${chatId}/messages?${params}`);if(generation!==state.generation)return;state.messages=result.items;state.hasOlder=result.has_more;state.hasNewer=result.has_newer;renderMessages(around);requestAnimationFrame(()=>{if(around){const el=document.querySelector(`[data-message-id="${around}"]`);if(el){el.scrollIntoView({block:'center'});setTimeout(()=>el.classList.remove('highlighted'),4000)}}else scrollBottom();});}catch(e){if(generation===state.generation)$('messageStream').replaceChildren(empty(errMessage(e),'!'))}}
function scrollBottom(){const area=$('messageScroll');area.scrollTop=area.scrollHeight}
function linkTextInto(parent,text){const regex=/(https?:\/\/[^\s<>]+)/g;let end=0;for(const match of text.matchAll(regex)){const start=match.index;if(start>end)parent.appendChild(document.createTextNode(text.slice(end,start)));const a=document.createElement('a');a.textContent=match[0];try{const u=new URL(match[0]);if(['https:','http:'].includes(u.protocol)){a.href=u.href;a.target='_blank';a.rel='noopener noreferrer'}else{parent.appendChild(document.createTextNode(match[0]));end=start+match[0].length;continue}}catch{parent.appendChild(document.createTextNode(match[0]));end=start+match[0].length;continue}parent.appendChild(a);end=start+match[0].length}if(end<text.length)parent.appendChild(document.createTextNode(text.slice(end)))}
function textParts(text,entities){const wrap=document.createElement('div');wrap.className='message-text';if(!Array.isArray(entities)||entities.map(x=>x?.text||'').join('')!==text){linkTextInto(wrap,text||'');return wrap}for(const entity of entities){const raw=String(entity?.text??'');const type=entity?.type||'plain';const tags={bold:'strong',italic:'em',underline:'u',strikethrough:'s',code:'code',pre:'pre',spoiler:'span'};let node=document.createElement(tags[type]||'span');if(type==='spoiler'){node.className='spoiler';node.title=t('message.spoiler');node.addEventListener('click',()=>node.classList.toggle('revealed'))}if(type==='text_link'||type==='link'){try{const url=new URL(entity.href||raw);if(['https:','http:'].includes(url.protocol)){node=document.createElement('a');node.href=url.href;node.target='_blank';node.rel='noopener noreferrer'}}catch{}}if(type==='plain'){linkTextInto(node,raw)}else{node.textContent=raw}wrap.appendChild(node)}return wrap}
function reactionText(item){if(typeof item==='string')return item;if(typeof item!=='object'||item===null)return '';return String(item.emoji||item.reaction||item.type||'')+(item.count?' '+item.count:'')}
function renderMessage(m){if(m.type!=='message'&&!m.media?.length){const svc=document.createElement('div');svc.className='service-row';svc.textContent=(m.sender?m.sender+' · ':'')+(m.body||m.action?.replaceAll('_',' ')||m.type);svc.dataset.messageId=m.id;return svc}
  // The export marks messages sent by current account via from_id=user<id>.
  const own=Boolean(state.stats?.me_id && m.sender_id===`user${state.stats.me_id}`);
  const row=document.createElement('div');row.className='message-row'+(own?' own':'');row.dataset.messageId=m.id;row.dataset.tgId=m.tg_id;
  const bubble=document.createElement('article');bubble.className='bubble';
  if(m.sender&&!own){const sender=document.createElement('div');sender.className='sender';sender.textContent=m.sender;bubble.appendChild(sender)}
  if(m.forwarded_from){const fw=document.createElement('div');fw.className='forwarded';fw.textContent=t('message.forwarded',{name:m.forwarded_from});bubble.appendChild(fw)}
  if(m.reply_to){const reply=document.createElement('button');reply.className='reply-preview';reply.innerHTML=`<b>↳ ${esc(m.reply_sender||t('message.replyTo'))}</b><span>${esc(m.reply_body?.slice(0,160)||t('message.number',{id:m.reply_to}))}</span>`;reply.title=t('message.goTo');reply.addEventListener('click',()=>jumpReply(m.reply_to));bubble.appendChild(reply)}
  if(m.body)bubble.appendChild(textParts(m.body,m.entities));
  if(m.media?.length){const holder=document.createElement('div');holder.className='message-media';for(const media of m.media.filter(x=>x.kind!=='thumbnail'))holder.appendChild(renderAttachment(media,m));bubble.appendChild(holder)}
  if(!m.body&&!m.media?.length){bubble.appendChild(textParts(m.action?.replaceAll('_',' ')||m.type||t('message.fallback'),[]))}
  if(m.reactions?.length){const line=document.createElement('div');line.className='reaction-row';for(const item of m.reactions.slice(0,16)){const span=document.createElement('span');span.className='reaction-pill';span.textContent=reactionText(item);line.appendChild(span)}bubble.appendChild(line)}
  const foot=document.createElement('div');foot.className='message-foot';foot.textContent=(m.ts?timeFormat(m.ts):'')+(m.edited?t('message.edited'):'');bubble.appendChild(foot);row.appendChild(bubble);
  const actions=document.createElement('div');actions.className='message-actions';const bookmark=document.createElement('button');bookmark.className='action-mini'+(m.bookmarked?' saved':'');bookmark.textContent=m.bookmarked?'★':'☆';bookmark.title=m.bookmarked?t('bookmarks.remove'):t('bookmarks.add');bookmark.addEventListener('click',()=>toggleBookmark(m,bookmark));const raw=document.createElement('button');raw.className='action-mini';raw.textContent='⋯';raw.title=t('message.raw');raw.addEventListener('click',()=>showRaw(m.id));actions.append(bookmark,raw);row.appendChild(actions);
  return row;
}
function renderAttachment(media,m){const kind=media.kind;if((kind==='photo'||kind==='sticker')&&['image/jpeg','image/png','image/webp','image/gif','image/avif'].includes(media.mime)||kind==='animation'&&media.mime==='image/gif'){
  const btn=document.createElement('button');btn.type='button';btn.className='media-preview-btn';btn.title=media.filename;const image=document.createElement('img');image.className='media-thumb';image.src=media.url;image.alt=media.filename||t('media.photo');image.loading='lazy';image.style.aspectRatio=(media.width>0&&media.height>0)?`${media.width} / ${media.height}`:'4 / 3';btn.appendChild(image);btn.addEventListener('click',()=>openViewer([{...media,chat_id:m.chat_id,message_id:m.id}],0));return btn}
  if(kind==='video'||kind==='video_message'||kind==='animation'){const v=document.createElement('video');v.src=media.url;v.controls=true;v.preload='metadata';v.playsInline=true;v.className='media-thumb';v.setAttribute('controlsList','nodownload');const box=document.createElement('div');box.className='media-play-box';const dl=document.createElement('a');dl.href=media.url+'?download=true';dl.textContent=t('media.downloadVideo');dl.className='media-download';box.append(v,dl);return box}
  if(kind==='voice'||kind==='audio'){const a=document.createElement('audio');a.src=media.url;a.controls=true;a.preload='none';a.className='media-audio';const box=document.createElement('div');box.className='media-play-box';const dl=document.createElement('a');dl.href=media.url+'?download=true';dl.textContent=t('media.downloadAudio');dl.className='media-download';box.append(a,dl);return box}
  const link=document.createElement('a');link.className='file-tile';link.href=media.url+'?download=true';link.download=media.filename;link.innerHTML=`<span class="file-icon">▤</span><span style="min-width:0"><div class="file-name">${esc(media.filename)}</div><div class="file-type">${esc(media.mime||t('media.file'))}</div></span><span style="margin-left:auto;color:var(--blue)">↓</span>`;return link}
// Keep existing message DOM nodes and loaded media intact during pagination.
// Full re-rendering after every page used to reset image dimensions and jump the viewport.
const MAX_LOADED_MESSAGES = 1200;
const WINDOW_AFTER_TRIM = 800;
function messageDay(m){return m.ts?new Date(m.ts*1000).toDateString():String(m.date_iso||'').slice(0,10)}
function daySeparator(m){const el=document.createElement('div');el.className='day-separator';el.textContent=m.ts?dayFormat(m.ts):String(m.date_iso||'').slice(0,10);return el}
function messageFragment(messages, previousDay='', highlight=null){
  const frag=document.createDocumentFragment();
  for(const m of messages){
    const day=messageDay(m);
    if(day!==previousDay){frag.appendChild(daySeparator(m));previousDay=day}
    const el=renderMessage(m);
    if(Number(m.id)===Number(highlight))el.classList.add('highlighted');
    frag.appendChild(el);
  }
  return frag;
}
function updateMessageControls(){
  $('latestButton').hidden=!state.hasNewer;
  const old=$('messageLoad');old.replaceChildren();
  if(state.hasOlder){const btn=document.createElement('button');btn.textContent=t('chat.older');btn.onclick=moreOld;old.appendChild(btn)}
  const newer=$('messageLoadNew');newer.replaceChildren();
  if(state.hasNewer){const btn=document.createElement('button');btn.textContent=t('chat.newer');btn.onclick=moreNew;newer.appendChild(btn)}
}
function renderMessages(highlight=null){
  const stream=$('messageStream');stream.replaceChildren();
  if(!state.messages.length){stream.appendChild(empty(t('chat.empty'),'◉'));updateMessageControls();return}
  stream.appendChild(messageFragment(state.messages,'',highlight));
  updateMessageControls();
}
// Preserve a message that is actually visible, rather than relying on scrollHeight:
// media, day separators and trimming can all change the total document height.
function visibleMessageAnchor(){
  const sc=$('messageScroll'),box=sc.getBoundingClientRect();
  for(const element of $('messageStream').children){
    if(!element.dataset.messageId)continue;
    const rect=element.getBoundingClientRect();
    if(rect.bottom>box.top+2 && rect.top<box.bottom-2)return {element, top:rect.top};
  }
  return null;
}
function preserveAnchor(update){
  const sc=$('messageScroll');const anchor=visibleMessageAnchor();
  // Disable native scroll anchoring during synchronous DOM changes, so the
  // manual adjustment doesn't get applied a second time.
  sc.style.overflowAnchor='none';
  update();
  if(anchor&&anchor.element.isConnected)sc.scrollTop+=anchor.element.getBoundingClientRect().top-anchor.top;
  requestAnimationFrame(()=>{sc.style.overflowAnchor='';});
}
function prependMessages(items){
  if(!items.length)return;
  const stream=$('messageStream');
  const previousFirst=state.messages[items.length]; // state already contains the older batch
  // New older page ends on the same day as the old first page: remove duplicate separator.
  if(previousFirst&&messageDay(items[items.length-1])===messageDay(previousFirst)
     &&stream.firstElementChild?.classList.contains('day-separator')){
    stream.firstElementChild.remove();
  }
  stream.prepend(messageFragment(items));
}
function appendMessages(items, oldLast){
  if(!items.length)return;
  $('messageStream').appendChild(messageFragment(items,oldLast?messageDay(oldLast):''));
}
function trimNewest(){
  if(state.messages.length<=MAX_LOADED_MESSAGES)return;
  state.messages=state.messages.slice(0,WINDOW_AFTER_TRIM);
  const last=state.messages[state.messages.length-1];
  const node=$('messageStream').querySelector(`[data-message-id="${last.id}"]`);
  if(node){while(node.nextSibling)node.nextSibling.remove()}
  state.hasNewer=true;
}
function trimOldest(){
  if(state.messages.length<=MAX_LOADED_MESSAGES)return;
  state.messages=state.messages.slice(-WINDOW_AFTER_TRIM);
  const first=state.messages[0];
  const stream=$('messageStream');const node=stream.querySelector(`[data-message-id="${first.id}"]`);
  if(node){
    while(stream.firstChild&&stream.firstChild!==node)stream.firstChild.remove();
    stream.insertBefore(daySeparator(first),node);
  }
  state.hasOlder=true;
}
async function moreOld(){
  if(!state.chat||!state.hasOlder||state.busy||!state.messages.length)return;
  state.busy=true;const gen=state.generation;const chatId=state.chat.id;
  const first=state.messages[0];const loadButton=$('messageLoad').querySelector('button');if(loadButton){loadButton.disabled=true;loadButton.textContent=t('chat.loadingMore')}
  try{
    const data=await api(`/api/chats/${chatId}/messages?`+new URLSearchParams({limit:60,before_ts:first.ts,before_id:first.id}));
    if(gen!==state.generation)return;
    preserveAnchor(()=>{
      state.messages=data.items.concat(state.messages);
      state.hasOlder=data.has_more;
      prependMessages(data.items);
      trimNewest();
      updateMessageControls();
    });
  }catch(e){if(gen===state.generation){toast(errMessage(e));updateMessageControls()}}
  finally{if(gen===state.generation)state.busy=false}
}
async function moreNew(){
  if(!state.chat||!state.hasNewer||state.busy||!state.messages.length)return;
  state.busy=true;const gen=state.generation;const chatId=state.chat.id;
  const last=state.messages[state.messages.length-1];const loadButton=$('messageLoadNew').querySelector('button');if(loadButton){loadButton.disabled=true;loadButton.textContent=t('chat.loadingMore')}
  try{
    const data=await api(`/api/chats/${chatId}/messages?`+new URLSearchParams({limit:60,after_ts:last.ts,after_id:last.id}));
    if(gen!==state.generation)return;
    preserveAnchor(()=>{
      state.messages.push(...data.items);
      state.hasNewer=data.has_newer;
      appendMessages(data.items,last);
      trimOldest();
      updateMessageControls();
    });
  }catch(e){if(gen===state.generation){toast(errMessage(e));updateMessageControls()}}
  finally{if(gen===state.generation)state.busy=false}
}
async function jumpReply(tgId){if(!state.chat)return;const found=state.messages.find(m=>m.tg_id===String(tgId));if(found){const el=document.querySelector(`[data-message-id="${found.id}"]`);if(el){el.scrollIntoView({behavior:'smooth',block:'center'});el.classList.add('highlighted');setTimeout(()=>el.classList.remove('highlighted'),4000);return}}try{const response=await api(`/api/chats/${state.chat.id}/resolve?tg_id=${encodeURIComponent(tgId)}`);await openChat(state.chat.id,response.id)}catch(e){toast(errMessage(e))}}
async function toggleBookmark(message,button){try{const save=!message.bookmarked;const data=await api(`/api/bookmarks/${message.id}`,save?{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'}:{method:'DELETE'});message.bookmarked=data.bookmarked;button.textContent=data.bookmarked?'★':'☆';button.classList.toggle('saved',data.bookmarked);toast(data.bookmarked?t('bookmarks.added'):t('bookmarks.removed'))}catch(e){toast(errMessage(e))}}
function searchParams(){const params=new URLSearchParams({q:$('globalQuery').value.trim(),limit:40,offset:state.search.offset});const values=[['chat_id','searchChat'],['sender','searchSender'],['after','searchAfter'],['before','searchBefore'],['has','searchHas']];for(const [key,id] of values){if($(id).value)params.set(key,$(id).value)}return params}
function gotoSearch(chatId=null,query=''){view('search');$('globalQuery').value=query;$('searchChat').value=chatId||'';if(query)runSearch(true);setTimeout(()=>$('globalQuery').focus(),60)}
async function runSearch(reset=true){if(reset){state.search={offset:0,items:[],more:false};$('searchResults').replaceChildren()}const q=$('globalQuery').value.trim();const filter=Boolean($('searchAfter').value||$('searchBefore').value||$('searchChat').value||$('searchSender').value||$('searchHas').value);if(!q&&!filter){$('searchTitle').textContent=t('search.enter');$('searchHint').textContent='';$('moreResults').hidden=true;return}const params=searchParams();$('searchTitle').textContent=t('search.searching');$('moreResults').hidden=true;try{const data=await api('/api/search?'+params);state.search.items.push(...data.items);state.search.offset+=data.items.length;state.search.more=data.has_more;renderSearchResults();}catch(e){toast(errMessage(e));$('searchTitle').textContent=t('search.error')}}
function renderResult(item){const button=document.createElement('button');button.className='result-card';const chat=getChat(item.chat_id);button.appendChild(avatar(chat));const content=document.createElement('div');content.className='result-content';const meta=document.createElement('div');meta.className='result-meta';const b=document.createElement('span');b.textContent=`${item.chat_title} · ${item.sender||t('message.fallback')}`;const t=document.createElement('span');t.textContent=item.ts?shortDate(item.ts):'';meta.append(b,t);const snip=document.createElement('div');snip.className='result-snippet';snip.textContent=item.body||t('search.attachment');content.append(meta,snip);button.append(content);const arrow=document.createElement('span');arrow.className='result-arrow';arrow.textContent='↗';button.append(arrow);button.addEventListener('click',()=>openChat(item.chat_id,item.id));return button}
function renderSearchResults(){state.search.done=true;const items=state.search.items;$('searchTitle').textContent=items.length?t('search.results',{n:fmt(items.length)+(state.search.more?' +':'')}):t('search.none');$('searchHint').textContent=items.length?t('search.hint'):'';const list=$('searchResults');list.replaceChildren();if(!items.length){list.appendChild(empty(t('search.tryOther')));return}const frag=document.createDocumentFragment();for(const it of items)frag.appendChild(renderResult(it));list.appendChild(frag);$('moreResults').hidden=!state.search.more}
function gotoGallery(chatId=null){state.gallery={offset:0,items:[],more:false,kind:'all'};$('galleryChat').value=chatId||'';for(const b of $('galleryFilters').querySelectorAll('button'))b.classList.toggle('selected',b.dataset.kind==='all');view('gallery');loadGallery(true)}
async function loadGallery(reset=false){if(reset){state.gallery.offset=0;state.gallery.items=[]}const params=new URLSearchParams({kind:state.gallery.kind,limit:48,offset:state.gallery.offset});if($('galleryChat').value)params.set('chat_id',$('galleryChat').value);$('galleryDescription').textContent=$('galleryChat').value?t('gallery.chatDescription'):t('gallery.description');try{const data=await api('/api/gallery?'+params);state.gallery.items.push(...data.items);state.gallery.offset+=data.items.length;state.gallery.more=data.has_more;renderGallery()}catch(e){toast(errMessage(e))}}
function renderGallery(){const list=$('galleryGrid');list.replaceChildren();if(!state.gallery.items.length){list.appendChild(empty(t('gallery.empty'),'▧'));$('moreGallery').hidden=true;return}const frag=document.createDocumentFragment();for(let index=0;index<state.gallery.items.length;index++){const m=state.gallery.items[index];const b=document.createElement('button');b.className='gallery-item';if((['photo','sticker'].includes(m.kind)&&['image/jpeg','image/png','image/webp','image/gif','image/avif'].includes(m.mime))||(m.kind==='animation'&&m.mime==='image/gif')){const img=document.createElement('img');img.className='gallery-image';img.src=m.url;img.loading='lazy';img.alt=m.filename||m.kind;b.appendChild(img)}else if(['video','video_message','animation'].includes(m.kind)&&m.mime!=='application/x-tgsticker'){const vid=document.createElement('video');vid.className='gallery-image video';vid.src=m.url+'#t=0.1';vid.preload='metadata';vid.muted=true;vid.playsInline=true;b.appendChild(vid)}else{const symbol=document.createElement('div');symbol.className='gallery-image';symbol.textContent=({voice:'◖))',audio:'♫',file:'▤'}[m.kind]||'▣');b.appendChild(symbol)}const cap=document.createElement('div');cap.className='gallery-caption';cap.innerHTML=`<b>${esc(m.filename||m.kind)}</b><small>${esc(m.chat_title)} · ${shortDate(m.ts)}</small>`;b.appendChild(cap);b.addEventListener('click',()=>openViewer(state.gallery.items,index));frag.appendChild(b)}list.appendChild(frag);$('moreGallery').hidden=!state.gallery.more}
async function gotoBookmarks(){view('bookmarks');try{const data=await api('/api/bookmarks');const list=$('bookmarksList');list.replaceChildren();if(!data.items.length){list.appendChild(empty(t('bookmarks.empty'),'☆'));return}for(const x of data.items)list.appendChild(renderResult(x))}catch(e){toast(errMessage(e))}}
function gotoContacts(){view('contacts');$('contactsQuery').value='';loadContacts(true)}
async function loadContacts(reset=false){if(reset){state.contacts={offset:0,items:[],more:false,generation:(state.contacts.generation||0)+1}}const generation=state.contacts.generation;const params=new URLSearchParams({q:$('contactsQuery').value.trim(),offset:state.contacts.offset,limit:60});try{const r=await api('/api/contacts?'+params);if(generation!==state.contacts.generation)return;state.contacts.items.push(...r.items);state.contacts.offset+=r.items.length;state.contacts.more=r.has_more;const list=$('contactsList');list.replaceChildren();for(const c of state.contacts.items){const div=document.createElement('div');div.className='result-card contact-card';const name=document.createElement('strong');name.textContent=[c.first_name,c.last_name].filter(Boolean).join(' ')||t('contacts.noName');const phone=document.createElement('small');phone.textContent=c.phone_number;div.append(name,phone);const btn=document.createElement('button');btn.className='secondary-button';btn.textContent=t('contacts.find');btn.addEventListener('click',()=>{$('chatFilter').value=name.textContent;state.category='personal';for(const item of $('categoryFilters').querySelectorAll('button'))item.classList.toggle('selected',item.dataset.category==='personal');loadChats();view('home');$('sidebar').classList.add('open')});div.appendChild(btn);list.appendChild(div)}$('moreContacts').hidden=!state.contacts.more;$('contactsCount').textContent=state.contacts.items.length?t('contacts.shown',{n:state.contacts.items.length+(state.contacts.more?'+':'')}):t('contacts.none')}catch(e){toast(errMessage(e))}}
function openViewer(items,index){if(!items?.length)return;state.viewer=items;state.viewerIndex=index;showViewerItem();$('overlay').hidden=false;document.body.style.overflow='hidden'}
function showViewerItem(){const m=state.viewer[state.viewerIndex];$('viewerTitle').textContent=m.filename||m.kind||t('viewer.media');$('viewerDownload').hidden=false;$('viewerDownload').href=m.url+'?download=true';$('viewerRaw').hidden=true;$('viewerBody').replaceChildren();if((['photo','sticker'].includes(m.kind)&&['image/jpeg','image/png','image/webp','image/gif','image/avif'].includes(m.mime))||(m.kind==='animation'&&m.mime==='image/gif')){const img=document.createElement('img');img.src=m.url;img.alt=m.filename||t('media.photo');$('viewerBody').appendChild(img)}else if(['video','video_message','animation'].includes(m.kind)&&m.mime!=='application/x-tgsticker'){const vid=document.createElement('video');vid.src=m.url;vid.controls=true;vid.autoplay=true;vid.playsInline=true;$('viewerBody').appendChild(vid)}else if(['audio','voice'].includes(m.kind)){const audio=document.createElement('audio');audio.src=m.url;audio.controls=true;audio.autoplay=true;$('viewerBody').appendChild(audio)}else{const file=document.createElement('a');file.className='secondary-button';file.href=m.url+'?download=true';file.textContent=t('viewer.downloadFile',{name:m.filename});file.download=m.filename;$('viewerBody').appendChild(file)}$('viewerCount').textContent=state.viewer.length>1?`${state.viewerIndex+1} / ${state.viewer.length}`:'';$('viewerPrev').disabled=state.viewerIndex===0;$('viewerNext').disabled=state.viewerIndex===state.viewer.length-1;$('viewerMessage').hidden=!m.message_id;}
function viewerStep(n){const index=state.viewerIndex+n;if(index<0||index>=state.viewer.length)return;state.viewerIndex=index;showViewerItem()}
function closeViewer(){$('overlay').hidden=true;$('viewerBody').replaceChildren();document.body.style.overflow=''}
async function showRaw(messageId){try{const data=await api(`/api/messages/${messageId}/raw`);state.viewerTarget=messageId;state.viewer=[];$('overlay').hidden=false;$('viewerTitle').textContent=t('viewer.raw');$('viewerDownload').hidden=true;$('viewerRaw').hidden=true;$('viewerCount').textContent='';$('viewerMessage').hidden=true;$('viewerPrev').disabled=$('viewerNext').disabled=true;const pre=document.createElement('pre');pre.textContent=JSON.stringify(data,null,2);$('viewerBody').replaceChildren(pre)}catch(e){toast(errMessage(e))}}
async function calendarJump(){if(!state.chat||!$('calendarDate').value)return;const params=new URLSearchParams({chat_id:state.chat.id,after:$('calendarDate').value,before:$('calendarDate').value,limit:1});$('calendarInfo').textContent=t('calendar.searching');try{const r=await api('/api/search?'+params);if(r.items.length){await openChat(state.chat.id,r.items[0].id);$('calendarPanel').hidden=true}else{$('calendarInfo').textContent=t('calendar.noneThatDay')}}catch(e){$('calendarInfo').textContent=errMessage(e)}}
function wire(){
  $('loginForm').addEventListener('submit',async e=>{e.preventDefault();$('loginError').textContent='';$('loginButton').disabled=true;try{await postJSON('/api/auth/login',{password:$('passwordInput').value});await boot()}catch(err){$('loginError').textContent=errMessage(err)}finally{$('loginButton').disabled=false}});
  $('eyeButton').addEventListener('click',()=>{$('passwordInput').type=$('passwordInput').type==='password'?'text':'password'});
  const logout=async()=>{try{await postJSON('/api/auth/logout',{})}catch{}showLogin()};$('logoutButton').onclick=logout;$('mobileLogout').onclick=logout;
  $('langButton').onclick=()=>{toggleLanguage();$('optionsMenu').hidden=true};$('loginLang').onclick=toggleLanguage;
  document.addEventListener('tgarchive:language',rerenderForLanguage);
  $('optionsButton').onclick=()=>$('optionsMenu').hidden=!$('optionsMenu').hidden;
  $('themeButton').onclick=()=>{document.body.classList.toggle('light');localStorage.setItem('tgarchive-theme',document.body.classList.contains('light')?'light':'dark');$('optionsMenu').hidden=true};
  $('navHome').onclick=home;$('navContacts').onclick=gotoContacts;$('navSearch').onclick=()=>gotoSearch();$('navGallery').onclick=()=>gotoGallery();$('navBookmarks').onclick=gotoBookmarks;
  let contactTimer;$('contactsQuery').addEventListener('input',()=>{clearTimeout(contactTimer);contactTimer=setTimeout(()=>loadContacts(true),300)});$('moreContacts').onclick=()=>loadContacts(false);$('contactsPersonal').onclick=showPersonalChats;
  $('homeSearch').onclick=()=>gotoSearch();$('homeMedia').onclick=()=>gotoGallery();
  $('chatSearch').onclick=()=>gotoSearch(state.chat?.id);$('chatMedia').onclick=()=>gotoGallery(state.chat?.id);$('chatLatestTop').onclick=()=>state.chat&&openChat(state.chat.id);$('latestButton').onclick=()=>state.chat&&openChat(state.chat.id);
  $('sidebarOpen').onclick=()=>$('sidebar').classList.add('open');$('sidebarClose').onclick=()=>$('sidebar').classList.remove('open');
  let chatFilterTimer;$('chatFilter').addEventListener('input',()=>{clearTimeout(chatFilterTimer);chatFilterTimer=setTimeout(loadChats,220)});
  $('categoryFilters').addEventListener('click',event=>{const b=event.target.closest('button[data-category]');if(!b)return;state.category=b.dataset.category;for(const item of $('categoryFilters').querySelectorAll('button'))item.classList.toggle('selected',item===b);loadChats()});
  $('messageScroll').addEventListener('scroll',()=>{const sc=$('messageScroll');if(sc.scrollTop<180)moreOld();else if(sc.scrollHeight-sc.scrollTop-sc.clientHeight<220)moreNew()},{passive:true});
  $('searchForm').onsubmit=e=>{e.preventDefault();runSearch(true)};$('moreResults').onclick=()=>runSearch(false);
  $('galleryChat').onchange=()=>loadGallery(true);$('galleryFilters').onclick=e=>{const btn=e.target.closest('button[data-kind]');if(!btn)return;state.gallery.kind=btn.dataset.kind;for(const b of $('galleryFilters').querySelectorAll('button'))b.classList.toggle('selected',b===btn);loadGallery(true)};$('moreGallery').onclick=()=>loadGallery(false);
  $('calendarClose').onclick=()=>$('calendarPanel').hidden=true;
  $('chatCalendar').onclick=async()=>{$('calendarPanel').hidden=!$('calendarPanel').hidden;if(!$('calendarPanel').hidden){try{const x=await api(`/api/chats/${state.chat.id}/days`);$('calendarInfo').textContent=x.days.length?t('calendar.days',{n:x.days.length}):t('calendar.noMessages');if(x.days.length)$('calendarDate').value=x.days[0].day}catch(e){toast(errMessage(e))}}};
  $('calendarGo').onclick=calendarJump;
  $('viewerClose').onclick=closeViewer;$('overlay').onclick=e=>{if(e.target===$('overlay'))closeViewer()};$('viewerPrev').onclick=()=>viewerStep(-1);$('viewerNext').onclick=()=>viewerStep(1);$('viewerMessage').onclick=()=>{const m=state.viewer[state.viewerIndex];if(m?.chat_id&&m?.message_id){closeViewer();openChat(m.chat_id,m.message_id)}};
  window.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();gotoSearch()}if(e.key==='Escape'){closeViewer();$('optionsMenu').hidden=true;$('calendarPanel').hidden=true;$('sidebar').classList.remove('open')}if(!$('overlay').hidden){if(e.key==='ArrowLeft')viewerStep(-1);if(e.key==='ArrowRight')viewerStep(1)}});
}
// Re-render whatever is on screen after the UI language changes; loaded data is reused.
function rerenderForLanguage(){
  if($('appPage').hidden)return;
  populateSelectors();renderChatList();
  if(!state.search.done)$('searchTitle').textContent=t('search.enter');
  if(state.view==='home')renderStats();
  else if(state.view==='chat'&&state.chat){renderChatHeader(state.chat);const sc=$('messageScroll');const top=sc.scrollTop;renderMessages();sc.scrollTop=top}
  else if(state.view==='search'&&state.search.done)renderSearchResults();
  else if(state.view==='gallery'){$('galleryDescription').textContent=$('galleryChat').value?t('gallery.chatDescription'):t('gallery.description');renderGallery()}
  else if(state.view==='bookmarks')gotoBookmarks();
  else if(state.view==='contacts')loadContacts(true);
}
async function boot(){try{await api('/api/auth/me');showApp();state.allChats=await loadAllChats();state.chats=state.allChats;populateSelectors();renderChatList();await home()}catch(e){if(!$('loginPage').hidden) return;toast(errMessage(e))}}
window.addEventListener('DOMContentLoaded',async()=>{applyI18n();$('searchTitle').textContent=t('search.enter');if(localStorage.getItem('tgarchive-theme')==='light')document.body.classList.add('light');wire();try{await boot()}catch{showLogin()}});
