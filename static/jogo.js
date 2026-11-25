/* Cozinha Crocante — jogo da palavra do dia (página /palavra-do-dia/).
   A palavra vem de /jogo.json (gerado pelo build); o dicionário do tamanho do dia vem de /dicionario/<n>.txt.
   Só existem palavras que estão no dicionário. */
(() => {
  'use strict';
  const BASE = (window.SITE && window.SITE.base) || '';
  const TENTATIVAS = 6;
  const CHAVE = 'cc_jogo';

  const el = {
    jogo: document.getElementById('jogo'),
    grade: document.getElementById('grade'),
    teclado: document.getElementById('teclado'),
    aviso: document.getElementById('jogo-aviso'),
    fim: document.getElementById('jogo-fim'),
  };
  if (!el.jogo || !el.grade) return;

  let info = null;            // conteúdo de jogo.json
  let alvo = '';              // palavra do dia normalizada (sem acento)
  let n = 0;                  // tamanho da palavra
  let dicionario = null;      // Set com as palavras de n letras
  let tentativas = [];        // tentativas confirmadas (normalizadas)
  let atual = [];             // letras digitadas na linha atual
  let encerrado = false;
  let travado = false;        // true se não foi possível carregar o jogo ou o dicionário

  /* ---- utilidades ---- */
  const normalizar = s => String(s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  function avisar(texto) { el.aviso.textContent = texto || ''; }

  /* ---- progresso guardado por data ---- */
  function carregarProgresso() {
    try {
      const s = JSON.parse(localStorage.getItem(CHAVE) || 'null');
      if (s && s.data === info.data && Array.isArray(s.tentativas)) tentativas = s.tentativas.slice(0, TENTATIVAS);
    } catch (e) { tentativas = []; }
  }
  function salvarProgresso() {
    try { localStorage.setItem(CHAVE, JSON.stringify({ data: info.data, tentativas })); } catch (e) { /* navegador bloqueou: segue sem salvar */ }
  }

  /* ---- dicas em duas passadas (repetições como no Termo) ---- */
  function avaliar(tent) {
    const dica = Array(n).fill('ausente');
    const sobra = {};
    for (let i = 0; i < n; i++) {
      if (tent[i] === alvo[i]) dica[i] = 'certa';
      else sobra[alvo[i]] = (sobra[alvo[i]] || 0) + 1;
    }
    for (let i = 0; i < n; i++) {
      if (dica[i] !== 'certa' && sobra[tent[i]] > 0) { dica[i] = 'presente'; sobra[tent[i]]--; }
    }
    return dica;
  }

  const ROTULO = { certa: 'letra certa', presente: 'letra existe em outra posição', ausente: 'letra não está na palavra' };

  /* ---- desenho ---- */
  function desenharGrade() {
    el.jogo.style.setProperty('--colunas', n);
    let html = '';
    for (let linha = 0; linha < TENTATIVAS; linha++) {
      const feita = tentativas[linha];
      const dicas = feita ? avaliar(feita) : null;
      html += '<div class="linha" role="row">';
      for (let i = 0; i < n; i++) {
        let letra = '', classe = 'celula', rotulo = 'vazia';
        if (feita) {
          letra = feita[i].toUpperCase();
          classe += ' c-' + dicas[i];
          rotulo = `${feita[i]}, ${ROTULO[dicas[i]]}`;
        } else if (linha === tentativas.length && !encerrado && atual[i]) {
          letra = atual[i].toUpperCase();
          classe += ' digitando';
          rotulo = `${atual[i]}, sem dica ainda`;
        }
        html += `<span class="${classe}" role="cell" aria-label="${esc(rotulo)}">${esc(letra)}</span>`;
      }
      html += '</div>';
    }
    el.grade.innerHTML = html;
    pintarTeclado();
  }

  const PRIORIDADE = { certa: 3, presente: 2, ausente: 1 };
  function pintarTeclado() {
    const melhor = {};
    tentativas.forEach(t => avaliar(t).forEach((d, i) => {
      const letra = t[i];
      if (!melhor[letra] || PRIORIDADE[d] > PRIORIDADE[melhor[letra]]) melhor[letra] = d;
    }));
    el.teclado.querySelectorAll('.tecla[data-tecla]').forEach(b => {
      const d = melhor[b.dataset.tecla];
      b.classList.remove('t-certa', 't-presente', 't-ausente');
      if (d) b.classList.add('t-' + d);
    });
  }

  function mostrarFim(acertou) {
    const receita = `${BASE}/receitas/${encodeURIComponent(info.slug)}/`;
    el.fim.hidden = false;
    el.fim.innerHTML = `
      <p><strong>${acertou ? `Acertou em ${tentativas.length} ${tentativas.length === 1 ? 'tentativa' : 'tentativas'}!` : 'Não foi dessa vez.'}</strong>
      A palavra de hoje é <b>${esc(info.palavra)}</b>.</p>
      <p><a class="jogo-receita" href="${esc(receita)}">Ver receita: ${esc(info.titulo)}</a></p>`;
  }

  function encerrar(acertou) {
    encerrado = true;
    mostrarFim(acertou);
    avisar('');
  }

  function travar(mensagem) {
    travado = true;
    avisar(mensagem);
    el.fim.hidden = false;
    el.fim.innerHTML = `<p>${esc(mensagem)}</p><p><a href="${esc(BASE + '/')}">Voltar para a página inicial</a></p>`;
  }

  /* ---- ações ---- */
  function digitar(letra) {
    if (encerrado || travado || atual.length >= n) return;
    atual.push(letra);
    avisar('');
    desenharGrade();
  }

  function apagar() {
    if (encerrado || travado) return;
    atual.pop();
    avisar('');
    desenharGrade();
  }

  function confirmar() {
    if (encerrado || travado) return;
    if (atual.length < n) { avisar(`Faltam ${n - atual.length} letra(s).`); return; }
    const palavra = normalizar(atual.join(''));
    if (!dicionario.has(palavra)) {
      avisar('Essa palavra não existe no dicionário. Tente outra; as letras ficam na linha.');
      return;
    }
    tentativas.push(palavra);
    atual = [];
    salvarProgresso();
    avisar('');
    desenharGrade();
    if (palavra === alvo) encerrar(true);
    else if (tentativas.length === TENTATIVAS) encerrar(false);
    else if (el.fim) el.fim.hidden = true;
  }

  /* ---- entrada: teclado físico e tela ---- */
  document.addEventListener('keydown', e => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    // Enter/Espaço com botão focado já disparam o clique do botão; as letras continuam valendo
    if (e.target && e.target.tagName === 'BUTTON' && (e.key === 'Enter' || e.key === ' ')) return;
    if (e.key === 'Enter') { e.preventDefault(); confirmar(); }
    else if (e.key === 'Backspace') { e.preventDefault(); apagar(); }
    else if (/^[a-zA-ZçÇ]$/.test(e.key)) digitar(normalizar(e.key));
  });

  el.teclado.addEventListener('click', e => {
    const b = e.target.closest('button');
    if (!b) return;
    if (b.dataset.tecla) digitar(normalizar(b.dataset.tecla));
    else if (b.dataset.acao === 'enter') confirmar();
    else if (b.dataset.acao === 'apagar') apagar();
    b.blur();   // tira o foco do botão: as teclas físicas seguem indo para a página, e Espaço não clica de novo
  });

  /* ---- início ---- */
  function iniciar(dados) {
    info = dados;
    alvo = normalizar(info.palavra);
    n = info.tamanho;
    carregarProgresso();
    encerrado = tentativas.length > 0 && (tentativas[tentativas.length - 1] === alvo || tentativas.length === TENTATIVAS);
    desenharGrade();
    if (encerrado) mostrarFim(tentativas[tentativas.length - 1] === alvo);
  }

  fetch(BASE + '/jogo.json', { cache: 'no-cache' })
    .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(dados => {
      return fetch(dados.dicionario, { cache: 'no-cache' })
        .then(r => { if (!r.ok) throw new Error(r.status); return r.text(); })
        .then(texto => {
          dicionario = new Set(texto.split('\n').filter(Boolean));
          iniciar(dados);
        })
        .catch(() => travar('Não consigo conferir as palavras agora. Tente de novo mais tarde.'));
    })
    .catch(() => travar('O jogo não está disponível agora. Tente de novo mais tarde.'));
})();
