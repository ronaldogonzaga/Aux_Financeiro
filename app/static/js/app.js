function toast(msg, tipo = "ok") {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.className = "toast " + tipo;
  el.hidden = false;
  clearTimeout(el._t);
  el._t = setTimeout(() => { el.hidden = true; }, 3500);
}

async function api(url, options = {}) {
  const res = await fetch(url, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.erro || res.statusText || "Erro na requisição");
  }
  return data;
}

function initConfig() {
  const form = document.getElementById("formConfig");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    const payload = Object.fromEntries(fd.entries());
    payload.usar_tls = form.querySelector('[name="usar_tls"]').checked;
    try {
      await api("/api/configuracao", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      toast("Configuração salva.");
    } catch (err) {
      toast(err.message, "erro");
    }
  });
}

function initTemplate() {
  const form = document.getElementById("formTemplate");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    const payload = Object.fromEntries(fd.entries());
    payload.enviar_copia = form.querySelector('[name="enviar_copia"]').checked;
    try {
      await api("/api/template", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      toast("Template salvo.");
    } catch (err) {
      toast(err.message, "erro");
    }
  });
}

function initPrestadores() {
  const dialog = document.getElementById("prestadorDialog");
  const btnNovo = document.getElementById("btnNovo");
  const btnSalvar = document.getElementById("btnSalvarPrestador");
  if (!dialog || !btnNovo) return;

  function fecharDialog() {
    dialog.close();
  }

  function openDialog(data = null) {
    document.getElementById("prestadorDialogTitle").textContent = data ? "Editar prestador" : "Novo prestador";
    document.getElementById("prestadorId").value = data?.id || "";
    document.getElementById("prestadorNome").value = data?.nome || "";
    document.getElementById("prestadorEmail").value = data?.email || "";
    document.getElementById("prestadorAtivo").checked = data ? !!Number(data.ativo) : true;
    dialog.showModal();
    document.getElementById("prestadorNome").focus();
  }

  btnNovo.addEventListener("click", () => openDialog());

  document.getElementById("btnFecharPrestador")?.addEventListener("click", fecharDialog);
  document.getElementById("btnCancelarPrestador")?.addEventListener("click", fecharDialog);

  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) fecharDialog();
  });

  document.querySelectorAll(".btn-edit").forEach((btn) => {
    btn.addEventListener("click", () => {
      openDialog({
        id: btn.dataset.id,
        nome: btn.dataset.nome,
        email: btn.dataset.email,
        ativo: btn.dataset.ativo,
      });
    });
  });

  document.querySelectorAll(".btn-del").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm("Excluir este prestador?")) return;
      try {
        await api(`/api/prestadores/${btn.dataset.id}`, { method: "DELETE" });
        toast("Prestador excluído.");
        location.reload();
      } catch (err) {
        toast(err.message, "erro");
      }
    });
  });

  btnSalvar.addEventListener("click", async (e) => {
    e.preventDefault();
    const nomeEl = document.getElementById("prestadorNome");
    const emailEl = document.getElementById("prestadorEmail");
    if (!nomeEl.value.trim() || !emailEl.value.trim()) {
      toast("Nome e e-mail são obrigatórios.", "erro");
      (!nomeEl.value.trim() ? nomeEl : emailEl).focus();
      return;
    }
    const id = document.getElementById("prestadorId").value;
    const payload = {
      nome: nomeEl.value.trim(),
      email: emailEl.value.trim(),
      ativo: document.getElementById("prestadorAtivo").checked,
    };
    try {
      if (id) {
        await api(`/api/prestadores/${id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      } else {
        await api("/api/prestadores", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      }
      fecharDialog();
      toast("Prestador salvo.");
      location.reload();
    } catch (err) {
      toast(err.message, "erro");
    }
  });

  const formImport = document.getElementById("formImport");
  if (formImport) {
    formImport.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fileInput = document.getElementById("arquivoImport");
      if (!fileInput.files.length) return;
      const fd = new FormData();
      fd.append("arquivo", fileInput.files[0]);
      try {
        const res = await fetch("/api/prestadores/importar", { method: "POST", body: fd });
        const data = await res.json();
        if (!res.ok || !data.ok) throw new Error(data.erro || "Falha na importação");
        toast(`Importado: ${data.inseridos} novos, ${data.atualizados} atualizados.`);
        setTimeout(() => location.reload(), 800);
      } catch (err) {
        toast(err.message, "erro");
      }
    });
  }
}

function folderNameFromPath(path) {
  if (!path) return "Nenhuma pasta selecionada";
  const parts = path.replace(/[\\/]+$/, "").split(/[\\/]/);
  return parts[parts.length - 1] || path;
}

function setFolderUI(target, path) {
  const input = document.getElementById(target === "medico" ? "pasta_medico" : "pasta_convenio");
  const nameEl = document.getElementById(target === "medico" ? "nome_medico" : "nome_convenio");
  const pathEl = document.getElementById(target === "medico" ? "path_medico_display" : "path_convenio_display");
  const card = document.getElementById(target === "medico" ? "cardMedico" : "cardConvenio");
  const clearBtn = card?.querySelector(".btn-clear-folder");
  const placeholder = target === "medico"
    ? "Ex.: …\\RELATÓRIO MÉDICO\\Pagamento 15-09-26"
    : "Ex.: …\\RELATÓRIO CONVÊNIOS";

  input.value = path || "";
  nameEl.textContent = folderNameFromPath(path);
  pathEl.textContent = path || placeholder;
  pathEl.title = path || "";
  pathEl.classList.toggle("is-empty", !path);
  card.classList.toggle("has-path", !!path);
  if (clearBtn) clearBtn.hidden = !path;
}

function initFolderPickers() {
  document.querySelectorAll(".btn-browse").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const target = btn.dataset.target;
      const input = document.getElementById(target === "medico" ? "pasta_medico" : "pasta_convenio");
      btn.disabled = true;
      const label = btn.textContent;
      btn.textContent = "Abrindo…";
      try {
        const data = await api("/api/selecionar-pasta", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            titulo: btn.dataset.titulo || "Selecionar pasta",
            inicial: input.value || "",
          }),
        });
        if (data.cancelado) return;
        if (!data.ok || !data.pasta) throw new Error(data.erro || "Não foi possível selecionar a pasta.");
        setFolderUI(target, data.pasta);
        toast("Pasta selecionada.");
      } catch (err) {
        toast(err.message, "erro");
      } finally {
        btn.disabled = false;
        btn.textContent = label;
      }
    });
  });

  document.querySelectorAll(".btn-clear-folder").forEach((btn) => {
    btn.addEventListener("click", () => {
      setFolderUI(btn.dataset.target, "");
    });
  });

  ["medico", "convenio"].forEach((t) => {
    const input = document.getElementById(t === "medico" ? "pasta_medico" : "pasta_convenio");
    if (input?.value) {
      document.getElementById(t === "medico" ? "cardMedico" : "cardConvenio")?.classList.add("has-path");
    }
  });
}

let previewData = null;
let pollTimer = null;

function initEnvio() {
  const btnPreview = document.getElementById("btnPreview");
  if (!btnPreview) return;

  initFolderPickers();
  btnPreview.addEventListener("click", runPreview);
  document.getElementById("btnEnviar")?.addEventListener("click", runEnviar);
  document.getElementById("chkTodos")?.addEventListener("change", (e) => {
    document.querySelectorAll(".chk-item").forEach((c) => {
      if (!c.disabled) c.checked = e.target.checked;
    });
    syncSelecionados();
  });

  pollStatus();
}

async function runPreview() {
  const pasta_medico = document.getElementById("pasta_medico").value.trim();
  const pasta_convenio = document.getElementById("pasta_convenio").value.trim();
  const btn = document.getElementById("btnPreview");
  btn.disabled = true;
  btn.textContent = "Analisando…";

  try {
    const data = await api("/api/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pasta_relatorio_medico: pasta_medico,
        pasta_relatorio_convenio: pasta_convenio,
      }),
    });
    if (!data.ok) throw new Error(data.erro || "Falha na análise");
    previewData = data;
    renderPreview(data);
    toast(`Análise concluída · período ${data.periodo}`);
  } catch (err) {
    toast(err.message, "erro");
  } finally {
    btn.disabled = false;
    btn.textContent = "Analisar anexos";
  }
}

function renderPreview(data) {
  const panel = document.getElementById("previewPanel");
  panel.hidden = false;
  document.getElementById("previewSummary").textContent =
    `Período: ${data.periodo} · ${data.total} prestadores · ${data.com_anexo} com anexo · ${data.sem_anexo} sem anexo`;

  const tbody = document.querySelector("#previewTable tbody");
  tbody.innerHTML = "";

  data.itens.forEach((item, idx) => {
    const tr = document.createElement("tr");
    if (!item.tem_anexos) tr.classList.add("row-warn");
    tr.innerHTML = `
      <td>
        <input type="checkbox" class="chk-item" data-idx="${idx}"
          ${item.selecionado ? "checked" : ""} ${item.tem_anexos ? "" : "disabled"}>
      </td>
      <td>${escapeHtml(item.nome)}</td>
      <td>${escapeHtml(item.email)}</td>
      <td><strong>${item.qtd_anexos}</strong></td>
      <td>${item.tem_anexos
        ? '<span class="badge ok">Pronto</span>'
        : '<span class="badge off">Sem anexo</span>'}</td>
      <td><button type="button" class="btn btn-ghost btn-sm btn-ver" data-idx="${idx}">Ver anexos</button></td>
    `;
    tbody.appendChild(tr);
  });

  tbody.querySelectorAll(".chk-item").forEach((c) => {
    c.addEventListener("change", syncSelecionados);
  });
  tbody.querySelectorAll(".btn-ver").forEach((btn) => {
    btn.addEventListener("click", () => showAnexos(Number(btn.dataset.idx)));
  });

  syncSelecionados();
}

function syncSelecionados() {
  if (!previewData) return;
  document.querySelectorAll(".chk-item").forEach((c) => {
    const idx = Number(c.dataset.idx);
    previewData.itens[idx].selecionado = c.checked;
  });
  const qtd = previewData.itens.filter((i) => i.selecionado && i.tem_anexos).length;
  const btn = document.getElementById("btnEnviar");
  btn.disabled = qtd === 0;
  btn.textContent = qtd ? `Confirmar e enviar (${qtd})` : "Confirmar e enviar";
}

function showAnexos(idx) {
  const item = previewData.itens[idx];
  const dialog = document.getElementById("anexosDialog");
  document.getElementById("dialogTitle").textContent = item.nome;
  const list = document.getElementById("dialogList");
  list.innerHTML = "";
  if (!item.anexos.length) {
    list.innerHTML = "<li>Nenhum anexo encontrado.</li>";
  } else {
    item.anexos.forEach((a) => {
      const li = document.createElement("li");
      li.innerHTML = `<strong>${escapeHtml(a.nome)}</strong><br><span class="muted">${escapeHtml(a.tipo)}${a.origem ? " · " + escapeHtml(a.origem) : ""}</span>`;
      list.appendChild(li);
    });
  }
  const avisos = document.getElementById("dialogAvisos");
  avisos.innerHTML = (item.avisos || []).map((a) => `<div>• ${escapeHtml(a)}</div>`).join("");
  dialog.showModal();
}

async function runEnviar() {
  if (!previewData) return;
  syncSelecionados();
  const selecionados = previewData.itens.filter((i) => i.selecionado && i.tem_anexos);
  if (!selecionados.length) return;

  if (!confirm(`Enviar e-mails para ${selecionados.length} prestador(es)?\nIntervalo de 3s entre envios · máx. 80/hora.`)) {
    return;
  }

  const btn = document.getElementById("btnEnviar");
  btn.disabled = true;

  try {
    const data = await api("/api/enviar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        periodo: previewData.periodo,
        itens: selecionados,
      }),
    });
    document.getElementById("envioProgress").hidden = false;
    toast(`Envio #${data.envio_id} iniciado.`);
    pollStatus();
  } catch (err) {
    toast(err.message, "erro");
    btn.disabled = false;
  }
}

function pollStatus() {
  clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const st = await api("/api/envio/status");
      const box = document.getElementById("envioProgress");
      if (!box) return;

      if (st.em_andamento || st.progresso) {
        box.hidden = false;
        const p = st.progresso || {};
        const total = p.total || 1;
        const atual = p.atual || p.enviados || 0;
        const pct = Math.min(100, Math.round((atual / total) * 100));
        document.getElementById("progressFill").style.width = pct + "%";

        let msg = "";
        if (p.tipo === "pausa") {
          msg = p.mensagem;
        } else if (st.em_andamento) {
          msg = `Enviando… ${p.enviados || 0} ok · ${p.falhas || 0} falha(s) · ${atual}/${total}`;
          if (p.nome) msg += ` · último: ${p.nome}`;
        } else if (st.resultado) {
          msg = `Concluído: ${st.resultado.enviados} enviados, ${st.resultado.falhas} falha(s).`;
          document.getElementById("progressFill").style.width = "100%";
          clearInterval(pollTimer);
          const btn = document.getElementById("btnEnviar");
          if (btn) btn.disabled = false;
        }
        document.getElementById("progressText").textContent = msg;
      }

      if (!st.em_andamento && st.resultado) {
        clearInterval(pollTimer);
      }
    } catch (_) {

    }
  }, 1500);
}

function escapeHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function initDashboard() {
  const live = document.getElementById("dashLive");
  if (!live) return;

  const text = document.getElementById("dashLiveText");
  const timer = setInterval(async () => {
    try {
      const st = await api("/api/envio/status");
      if (!st.em_andamento) {
        clearInterval(timer);
        if (st.resultado) {
          text.textContent = `Concluído: ${st.resultado.enviados} enviados, ${st.resultado.falhas} falha(s).`;
        }
        return;
      }
      const p = st.progresso || {};
      if (p.tipo === "pausa") {
        text.textContent = p.mensagem;
      } else {
        text.textContent = `Lote #${st.envio_id} · ${p.enviados || 0} ok · ${p.falhas || 0} falha(s) · ${p.atual || 0}/${p.total || "?"}`;
      }
    } catch (_) {

    }
  }, 2000);
}

document.addEventListener("DOMContentLoaded", () => {
  const page = window.PAGE;
  if (page === "config") initConfig();
  if (page === "template") initTemplate();
  if (page === "prestadores") initPrestadores();
  if (page === "envio") initEnvio();
  if (page === "dashboard") initDashboard();
});
