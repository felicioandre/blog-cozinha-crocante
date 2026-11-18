/* Cozinha Crocante — busca por ingredientes e botões de compartilhar.
   As receitas vêm de /busca.json (gerado pelo build a partir do posts.json). */
(() => {
  'use strict';
  const BASE = (window.SITE && window.SITE.base) || '';

  /* Temperos/itens de despensa que a maioria das pessoas já tem (a pessoa pode desligar). */
  const TEMPEROS = ['sal', 'pimenta-do-reino', 'azeite', 'óleo', 'orégano', 'canela', 'páprica', 'alho em pó', 'alecrim'];
  const CATEGORIAS = { airfryer: 'Air fryer', frigideira: 'Frigideira', salgado: 'Salgados', doce: 'Sobremesas' };

  /* grafias/sinônimos comuns -> forma usada nas receitas (ambos já normalizados) */
  const SINONIMOS = {
    'mussarela': 'mucarela', 'mozarela': 'mucarela', 'mozzarela': 'mucarela', 'muzzarela': 'mucarela',
    'peito de frango': 'frango', 'sobrecoxa': 'frango', 'coxa de frango': 'frango', 'file de frango': 'frango', 'asa de frango': 'frango',
    'azeite de oliva': 'azeite', 'cheiro verde': 'cheiro-verde', 'pimenta do reino': 'pimenta-do-reino', 'batata doce': 'batata-doce',
    'linguica toscana': 'linguica', 'patinho': 'carne moida', 'acem': 'carne moida',
    'tomate pelado': 'tomate', 'tomate picado': 'tomate', 'paozinho': 'pao france'
  };

  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const norm = s => String(s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/\s+/g, ' ').trim();
  const sing = s => { const n = norm(s); return n.length > 3 && n.endsWith('s') ? n.slice(0, -1) : n; };
  const alts = k => k.split('|');
  const nomeChave = k => alts(k).join(' ou ');
  const ehTempero = k => alts(k).every(a => TEMPEROS.includes(a));

  let RECEITAS = [];
  let CONHECIDOS = new Map();
  let dadosPromise = null;
  let tenho = [], modo = 'exato', temperosOk = true;

  /* ---- estado guardado enquanto a pessoa navega entre páginas ---- */
  function salvar() {
    try { sessionStorage.setItem('cc_busca', JSON.stringify({ tenho, modo, temperosOk })); } catch (e) {}
  }
  function carregar() {
    try {
      const s = JSON.parse(sessionStorage.getItem('cc_busca') || 'null');
      if (s) { tenho = Array.isArray(s.tenho) ? s.tenho : []; modo = s.modo === 'mais' ? 'mais' : 'exato'; temperosOk = s.temperosOk !== false; }
    } catch (e) {}
  }

  /* ---- dados ---- */
  function carregarDados() {
    if (!dadosPromise) {
      dadosPromise = fetch(BASE + '/busca.json', { cache: 'no-cache' })
        .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(lista => {
          RECEITAS = lista;
          CONHECIDOS = new Map();
          RECEITAS.forEach(r => [...r.chave, ...(r.opc || [])].forEach(k => alts(k).forEach(a => {
            if (!CONHECIDOS.has(sing(a))) CONHECIDOS.set(sing(a), a);
          })));
          const lista2 = [...CONHECIDOS.values()].filter(a => !TEMPEROS.includes(a)).sort((a, b) => a.localeCompare(b, 'pt-BR'));
          document.getElementById('ing-list').innerHTML = [...CONHECIDOS.values()].map(a => `<option value="${esc(a)}">`).join('');
          document.getElementById('quick').innerHTML = lista2.map(a => `<button type="button" class="chip" data-add="${esc(a)}" aria-pressed="false">${esc(a)}</button>`).join('');
        })
        .catch(() => { dadosPromise = null; throw new Error('falha'); });
    }
    return dadosPromise;
  }

  function adicionar(txt) {
    String(txt).split(',').map(s => s.trim()).filter(Boolean).forEach(p => {
      const nome = CONHECIDOS.get(sing(p)) || CONHECIDOS.get(SINONIMOS[norm(p)] || '') || p;
      if (!tenho.some(t => sing(t) === sing(nome))) tenho.push(nome);
    });
  }

  function avaliar(r) {
    const U = new Set(tenho.map(sing));
    const req = r.chave.filter(k => !(temperosOk && ehTempero(k)));
    const tem = k => alts(k).some(a => U.has(sing(a)));
    return { r, ok: req.filter(tem), falta: req.filter(k => !tem(k)), total: req.length };
  }

  function cardHTML(r, status) {
    const thumb = r.imagem ? `<img src="${BASE}/img/${esc(r.imagem)}" alt="" loading="lazy">` : r.emoji;
    return `<a class="card" href="${BASE}/receitas/${esc(r.slug)}/">
      <div class="thumb" style="background:${esc(r.cor)}">${thumb}</div>
      <div class="body">
        <div class="tags">${r.tags.map(t => `<span class="tag">${esc(CATEGORIAS[t] || t)}</span>`).join('')}</div>
        <h3>${esc(r.titulo)}</h3>
        <p>${esc(r.resumo)}</p>
        <div class="meta"><span>⏱ ${esc(r.tempo)}</span><span>🍽 ${esc(r.porcoes)}</span></div>
        ${status || ''}
      </div></a>`;
  }

  function statusHTML(x) {
    if (x.falta.length === 0) return '<div class="status ok">✔ Você tem tudo para fazer</div>';
    return `<div class="status falta">Você tem ${x.ok.length} de ${x.total}. Faltam: ${x.falta.map(k => esc(nomeChave(k))).join(', ')}</div>`;
  }

  /* ---- tela de busca ---- */
  function atualizarBusca() {
    const $ = id => document.getElementById(id);
    $('sel').innerHTML = tenho.length
      ? tenho.map((t, i) => `<span class="sel-chip">${esc(t)} <button type="button" data-rm="${i}" aria-label="Remover ${esc(t)}">×</button></span>`).join('') +
        '<button type="button" class="link" data-act="limpar">Limpar tudo</button>'
      : '';
    const U = new Set(tenho.map(sing));
    document.querySelectorAll('#quick .chip').forEach(c => c.setAttribute('aria-pressed', U.has(sing(c.dataset.add))));
    $('badge').textContent = tenho.length;
    $('badge').hidden = !tenho.length;
    document.querySelector('input[name="modo"][value="' + modo + '"]').checked = true;
    $('temperos').checked = temperosOk;

    const area = $('resultado-busca');
    if (!RECEITAS.length) { area.innerHTML = '<p class="vazio-dica">Carregando receitas…</p>'; return; }
    if (!tenho.length) { area.innerHTML = '<p class="vazio-dica">Adicione ingredientes para ver as receitas que combinam.</p>'; return; }

    const res = RECEITAS.map(avaliar)
      .filter(x => modo === 'exato' ? (x.falta.length === 0 && x.ok.length > 0) : x.ok.length > 0)
      .sort((a, b) => (b.ok.length / b.total) - (a.ok.length / a.total) || a.falta.length - b.falta.length);

    if (!res.length) {
      area.innerHTML = `<div class="empty">
        <p><strong>Nenhuma receita encontrada${modo === 'exato' ? ' só com esses ingredientes' : ''}.</strong></p>
        <p>${modo === 'exato'
          ? 'Adicione mais itens ou <button type="button" class="link" data-act="mais">mostre receitas em que posso comprar o que falta</button>.'
          : 'Tente outros ingredientes.'}</p></div>`;
      return;
    }
    area.innerHTML = `<p class="count">${res.length} ${res.length === 1 ? 'receita encontrada' : 'receitas encontradas'}</p>
      <div class="grid">${res.map(x => cardHTML(x.r, statusHTML(x))).join('')}</div>`;
  }

  const gaveta = document.getElementById('gaveta');
  const aba = document.getElementById('aba-busca');

  function abrirBusca() {
    gaveta.classList.add('open');
    gaveta.setAttribute('aria-hidden', 'false');
    aba.setAttribute('aria-expanded', 'true');
    document.body.classList.add('travado');
    atualizarBusca();
    carregarDados().then(atualizarBusca).catch(() => {
      document.getElementById('resultado-busca').innerHTML = '<p class="vazio-dica">Não consegui carregar as receitas agora. Tente de novo em instantes.</p>';
    });
    setTimeout(() => document.getElementById('ing-input').focus(), 300);
  }
  function fecharBusca() {
    if (!gaveta.classList.contains('open')) return;
    gaveta.classList.remove('open');
    gaveta.setAttribute('aria-hidden', 'true');
    aba.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('travado');
    aba.focus();
  }

  carregar();
  atualizarBusca();   // mostra a bolinha com o número de ingredientes guardados

  document.addEventListener('click', e => {
    const b = e.target.closest('[data-add],[data-rm],[data-act],[data-copiar],[data-nativo]');
    if (!b) {
      if (e.target.closest('#gaveta .card')) fecharBusca();
      return;
    }
    if (b.hasAttribute('data-copiar')) { copiarLink(b); return; }
    if (b.hasAttribute('data-nativo')) { compartilharNativo(b); return; }
    if (b.dataset.act === 'abrir') { abrirBusca(); return; }
    if (b.dataset.act === 'fechar') { fecharBusca(); return; }
    if (b.dataset.add) {
      const i = tenho.findIndex(t => sing(t) === sing(b.dataset.add));
      if (i >= 0) tenho.splice(i, 1); else adicionar(b.dataset.add);
    } else if (b.dataset.rm !== undefined) {
      tenho.splice(Number(b.dataset.rm), 1);
    } else if (b.dataset.act === 'limpar') {
      tenho = [];
    } else if (b.dataset.act === 'mais') {
      modo = 'mais';
    }
    salvar();
    atualizarBusca();
  });
  document.addEventListener('submit', e => {
    if (e.target.id !== 'f-ing') return;
    e.preventDefault();
    const inp = document.getElementById('ing-input');
    adicionar(inp.value);
    inp.value = '';
    salvar();
    atualizarBusca();
  });
  document.addEventListener('change', e => {
    if (e.target.name === 'modo') { modo = e.target.value; salvar(); atualizarBusca(); }
    if (e.target.id === 'temperos') { temperosOk = e.target.checked; salvar(); atualizarBusca(); }
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') fecharBusca(); });

  /* ---- compartilhar ---- */
  function dadosShare(btn) {
    const box = btn.closest('.share');
    return { url: box.dataset.url, title: box.dataset.title };
  }
  function copiarLink(btn) {
    const { url } = dadosShare(btn);
    const ok = () => { const t = btn.textContent; btn.textContent = 'Link copiado ✔'; setTimeout(() => { btn.textContent = t; }, 2000); };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(ok).catch(() => window.prompt('Copie o link:', url));
    } else {
      window.prompt('Copie o link:', url);
    }
  }
  function compartilharNativo(btn) {
    const { url, title } = dadosShare(btn);
    if (navigator.share) navigator.share({ title, url }).catch(() => {});
  }
  if (navigator.share) document.querySelectorAll('[data-nativo]').forEach(b => { b.hidden = false; });
})();
