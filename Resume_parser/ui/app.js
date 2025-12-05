document.addEventListener('DOMContentLoaded', () => {
  const sessionId = localStorage.getItem('sessionId') || crypto.randomUUID();
  localStorage.setItem('sessionId', sessionId);

  const el = (id)=>document.getElementById(id);
  const fileInput = el('fileInput');
  const extractBtn = el('extractBtn');
  const jobsBtn = el('jobsBtn');
  const output = el('output');
  const statusEl = el('status');
  const skillsWrap = el('skillsWrap');
  const chatLog = el('chatLog');
  const chatText = el('chatText');
  const chatSend = el('chatSend');

  function setStatus(text, isError=false){
    statusEl.textContent = text || '';
    statusEl.style.color = isError ? '#f87171' : 'var(--muted)';
  }
  function renderSkills(skills){
    skillsWrap.innerHTML = '';
    if(!skills || !skills.length){ skillsWrap.innerHTML = '<span class="muted">None yet</span>'; return; }
    skills.forEach(s=>{
      const span = document.createElement('span');
      span.className = 'chip';
      span.textContent = s;
      skillsWrap.appendChild(span);
    });
  }
  function addBubble(text, who='ai'){
    const b = document.createElement('div');
    b.className = 'bubble ' + (who==='user'?'user':'ai');
    // Preserve line breaks and make plain URLs clickable without altering spacing
    const withLinks = text.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noreferrer noopener">$1</a>');
    b.innerHTML = withLinks;
    chatLog.appendChild(b);
    chatLog.scrollTop = chatLog.scrollHeight;
  }
  function renderRecommendations(recs){
    if(!recs || !recs.length) return;
    const ul = document.createElement('ul');
    ul.className = 'list';
    recs.forEach(r=>{
      const li = document.createElement('li');
      const title = document.createElement('div');
      title.textContent = r.title || 'Role';
      const reason = document.createElement('div');
      reason.className = 'muted';
      reason.textContent = r.reason || '';
      li.appendChild(title);
      if(r.link){
        const a = document.createElement('a');
        a.href = r.link; a.target = '_blank'; a.rel = 'noreferrer noopener';
        a.textContent = 'Open link';
        li.appendChild(a);
      }
      li.appendChild(reason);
      ul.appendChild(li);
    });
    chatLog.appendChild(ul);
    chatLog.scrollTop = chatLog.scrollHeight;
  }

  extractBtn.addEventListener('click', async ()=>{
    output.textContent = '';
    setStatus('');
    const file = fileInput.files[0];
    if(!file){ setStatus('Please select a file.', true); return; }
    extractBtn.disabled = true; jobsBtn.disabled = true;
    setStatus('Uploading and extracting...');
    try{
      const fd = new FormData(); fd.append('file', file);
      const res = await fetch('/extract', { method:'POST', body: fd });
      const json = await res.json();
      output.textContent = JSON.stringify(json, null, 2);
      renderSkills(json.skills);
      setStatus(res.ok ? 'Extraction complete' : ('Error: ' + (json.detail || res.statusText)), !res.ok);
    }catch(err){ setStatus('Failed: ' + err.message, true); }
    finally{ extractBtn.disabled = false; jobsBtn.disabled = false; }
  });

  jobsBtn.addEventListener('click', async ()=>{
    setStatus('Searching jobs...');
    try{
      const res = await fetch('/jobs');
      const data = await res.json();
      output.textContent = JSON.stringify(data, null, 2);
      if(data.recommendations) renderRecommendations(data.recommendations);
      setStatus(res.ok ? 'Done' : ('Error: ' + (data.detail || res.statusText)), !res.ok);
    }catch(err){ setStatus('Failed: ' + err.message, true); }
  });

  function sendChat(){
    const msg = chatText.value.trim(); if(!msg) return; chatText.value='';
    addBubble('You: ' + msg, 'user');
    (async () => {
      try{
        const res = await fetch('/chat', { method:'POST', headers:{ 'Content-Type':'application/json' }, body: JSON.stringify({ message: msg, session_id: sessionId }) });
        const data = await res.json();
        const text = data.text || JSON.stringify(data);
        addBubble(text, 'ai');
        if(data.recommendations) renderRecommendations(data.recommendations);
      }catch(err){ addBubble('Error: ' + err.message, 'ai'); }
    })();
  }

  chatSend.addEventListener('click', sendChat);
  chatText.addEventListener('keydown', (e)=>{ if(e.key==='Enter') sendChat(); });
});
