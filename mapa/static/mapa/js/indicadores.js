(() => {
  const recordsBody = document.getElementById("records-list");
  const searchInput = document.getElementById("records-search");
  const recordsCount = document.getElementById("records-count");
  const stateMessage = document.getElementById("registrations-state");
  const colonyChart = document.getElementById("colony-chart");
  const genderChart = document.getElementById("gender-chart");
  const detailDialog = document.getElementById("registration-detail");
  const detailTitle = document.getElementById("detail-title");
  const detailState = document.getElementById("detail-state");
  const detailContent = document.getElementById("detail-content");
  const detailFields = document.getElementById("detail-fields");
  const detailImages = document.getElementById("detail-images");
  const detailResidents = document.getElementById("detail-residents");
  const detailResidentsSection = document.getElementById("detail-residents-section");
  const detailLocation = document.getElementById("detail-location");
  const reportButton = document.getElementById("generate-report");
  let records = [];
  searchInput.disabled = true;

  function formatFieldValue(value) {
    if (Array.isArray(value)) return value.map(formatFieldValue).join(", ");
    if (value && typeof value === "object") return JSON.stringify(value, null, 2);
    if (typeof value === "boolean") return value ? "Sim" : "Não";
    return String(value);
  }

  function appendFields(container, fields) {
    container.replaceChildren();
    for (const field of fields) {
      const item = document.createElement("dl");
      item.className = "record-field";
      const label = document.createElement("dt");
      label.textContent = field.label;
      const value = document.createElement("dd");
      value.textContent = formatFieldValue(field.value);
      item.append(label, value);
      container.appendChild(item);
    }
    if (!container.childElementCount) {
      const empty = document.createElement("p");
      empty.className = "chart-state";
      empty.textContent = "Nenhuma informação adicional disponível.";
      container.appendChild(empty);
    }
  }

  function renderImages(images) {
    detailImages.replaceChildren();
    for (const image of images) {
      if (
        !image ||
        typeof image.url !== "string" ||
        new URL(image.url).hostname !== "res.cloudinary.com"
      ) {
        continue;
      }
      const link = document.createElement("a");
      link.className = "record-image-link";
      link.href = image.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.setAttribute("aria-label", image.name || "Abrir imagem do cadastro");
      const element = document.createElement("img");
      element.src = image.url;
      element.alt = image.name || "Imagem do cadastro";
      element.loading = "lazy";
      link.appendChild(element);
      detailImages.appendChild(link);
    }
    detailImages.hidden = !detailImages.childElementCount;
  }

  async function showRecordDetail(record) {
    detailTitle.textContent = record.name || "Detalhes do cadastro";
    detailState.textContent = "Carregando cadastro…";
    detailState.classList.remove("is-error");
    detailState.hidden = false;
    detailContent.hidden = true;
    detailDialog.showModal();

    try {
      const response = await fetch(`/api/moradores/${encodeURIComponent(record.id)}/`, {
        headers: { Accept: "application/json" },
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || `Falha ao carregar o cadastro (HTTP ${response.status}).`);
      }
      if (
        payload.id !== record.id ||
        typeof payload.title !== "string" ||
        !Array.isArray(payload.fields) ||
        !Array.isArray(payload.residents) ||
        !Array.isArray(payload.images) ||
        (payload.coordinates !== null &&
          (!payload.coordinates ||
            !Number.isFinite(payload.coordinates.latitude) ||
            !Number.isFinite(payload.coordinates.longitude))) ||
        payload.fields.some((field) => !field || typeof field.label !== "string") ||
        payload.residents.some((resident) =>
          !resident ||
          typeof resident.name !== "string" ||
          !Array.isArray(resident.fields) ||
          resident.fields.some((field) => !field || typeof field.label !== "string"),
        ) ||
        payload.images.some((image) => !image || typeof image.url !== "string")
      ) {
        throw new Error("Os detalhes recebidos estão em formato inválido.");
      }

      detailTitle.textContent = payload.title;
      detailLocation.textContent = payload.coordinates
        ? `Coordenadas: ${payload.coordinates.latitude.toFixed(5)}°, ${payload.coordinates.longitude.toFixed(5)}°`
        : "Este cadastro não possui coordenadas informadas.";
      appendFields(detailFields, payload.fields);
      renderImages(payload.images);
      detailResidents.replaceChildren();
      for (const resident of payload.residents) {
        const card = document.createElement("article");
        card.className = "record-resident";
        const name = document.createElement("h4");
        name.textContent = resident.name;
        card.appendChild(name);
        appendFields(card, resident.fields);
        detailResidents.appendChild(card);
      }
      detailResidentsSection.hidden = !detailResidents.childElementCount;
      detailContent.hidden = false;
      detailState.hidden = true;
    } catch (error) {
      console.error("Erro ao carregar detalhes do cadastro:", error);
      detailState.textContent = error.message || "Não foi possível carregar os detalhes do cadastro.";
      detailState.classList.add("is-error");
    }
  }

  function showState(message, isError = false) {
    stateMessage.textContent = message;
    stateMessage.classList.toggle("is-error", isError);
    stateMessage.hidden = false;
  }

  function renderChart(container, values, emptyMessage) {
    container.replaceChildren();
    if (!values.length) {
      const empty = document.createElement("p");
      empty.className = "chart-state";
      empty.textContent = emptyMessage;
      container.appendChild(empty);
      return;
    }

    const maximum = Math.max(...values.map((item) => item.count));
    for (const item of values) {
      const row = document.createElement("div");
      row.className = "chart-row";
      row.setAttribute("role", "listitem");

      const heading = document.createElement("div");
      heading.className = "chart-row-heading";
      const label = document.createElement("span");
      label.textContent = item.label;
      const count = document.createElement("strong");
      count.textContent = item.count.toLocaleString("pt-BR");
      heading.append(label, count);

      const track = document.createElement("div");
      track.className = "chart-track";
      track.setAttribute("aria-hidden", "true");
      const bar = document.createElement("span");
      bar.style.width = `${Math.max((item.count / maximum) * 100, 2)}%`;
      track.appendChild(bar);
      row.append(heading, track);
      container.appendChild(row);
    }
  }

  function formatDate(value) {
    if (typeof value !== "string" || !value) return "—";
    if (!/^\d{4}-\d{2}-\d{2}(?:$|T)/.test(value)) return value;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeZone: "UTC" }).format(date);
  }

  function renderRecords() {
    const query = searchInput.value.trim().toLocaleLowerCase("pt-BR");
    const filteredRecords = records.filter((record) =>
      `${record.name} ${record.colony}`.toLocaleLowerCase("pt-BR").includes(query),
    );
    recordsBody.replaceChildren();
    recordsCount.textContent = `${filteredRecords.length.toLocaleString("pt-BR")} de ${records.length.toLocaleString("pt-BR")} cadastros`;
    stateMessage.hidden = filteredRecords.length > 0;
    if (!filteredRecords.length) {
      showState(query ? "Nenhum cadastro corresponde à busca." : "Nenhum cadastro foi encontrado.");
      return;
    }

    for (const record of filteredRecords) {
      const row = document.createElement("tr");
      const name = document.createElement("th");
      name.scope = "row";
      const detailButton = document.createElement("button");
      detailButton.className = "record-detail-button";
      detailButton.type = "button";
      detailButton.textContent = record.name || "Morador sem nome informado";
      detailButton.addEventListener("click", () => showRecordDetail(record));
      name.appendChild(detailButton);
      const colony = document.createElement("td");
      colony.textContent = record.colony || "Não informada";
      const residents = document.createElement("td");
      residents.textContent = Number(record.linked_residents || 0).toLocaleString("pt-BR");
      const date = document.createElement("td");
      date.textContent = formatDate(record.registered_at);
      row.append(name, colony, residents, date);
      recordsBody.appendChild(row);
    }
  }

  async function loadIndicators() {
    try {
      const response = await fetch("/api/indicadores/", {
        headers: { Accept: "application/json" },
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || `Falha ao carregar cadastros (HTTP ${response.status}).`);
      }
      const validCounts = (items) => items.every(
        (item) => item && typeof item.label === "string" && Number.isFinite(item.count) && item.count >= 0,
      );
      if (
        !Array.isArray(payload.records) ||
        !Array.isArray(payload.by_colony) ||
        !Array.isArray(payload.residents_by_gender) ||
        !validCounts(payload.by_colony) ||
        !validCounts(payload.residents_by_gender) ||
        !Number.isFinite(payload.total_records) ||
        !Number.isFinite(payload.linked_residents) ||
        payload.records.some((record) =>
          !record ||
          typeof record.id !== "string" ||
          !record.id ||
          typeof record.name !== "string" ||
          typeof record.colony !== "string" ||
          !Number.isFinite(record.linked_residents) ||
          record.linked_residents < 0 ||
          (record.registered_at !== null && typeof record.registered_at !== "string"),
        ) ||
        payload.total_records !== payload.records.length ||
        payload.linked_residents !== payload.records.reduce(
          (total, record) => total + record.linked_residents,
          0,
        )
      ) {
        throw new Error("Os indicadores recebidos estão em formato inválido.");
      }

      records = [...payload.records].sort((left, right) => left.name.localeCompare(right.name, "pt-BR"));
      searchInput.disabled = false;
      reportButton.disabled = false;

      document.getElementById("total-records").textContent = payload.total_records.toLocaleString("pt-BR");
      document.getElementById("total-residents").textContent = payload.linked_residents.toLocaleString("pt-BR");
      document.getElementById("total-colonies").textContent = payload.by_colony.length.toLocaleString("pt-BR");

      const colonies = payload.by_colony.slice(0, 7);
      const remainingColonies = payload.by_colony.slice(7);
      if (remainingColonies.length) {
        colonies.push({
          label: "Demais colônias",
          count: remainingColonies.reduce((total, item) => total + item.count, 0),
        });
      }
      renderChart(colonyChart, colonies, "Não há dados de colônia para exibir.");
      renderChart(genderChart, payload.residents_by_gender, "Não há dados de moradores vinculados para exibir.");
      renderRecords();
    } catch (error) {
      console.error("Erro ao carregar indicadores dos cadastros:", error);
      searchInput.disabled = true;
      renderChart(colonyChart, [], "Indicadores indisponíveis.");
      renderChart(genderChart, [], "Indicadores indisponíveis.");
      recordsCount.textContent = "Não foi possível carregar os cadastros.";
      showState(error.message || "Não foi possível carregar os cadastros.", true);
    }
  }

  searchInput.addEventListener("input", renderRecords);
  reportButton.addEventListener("click", () => {
    const currentQuery = searchInput.value;
    searchInput.value = "";
    renderRecords();
    document.getElementById("report-date").textContent = new Intl.DateTimeFormat("pt-BR", {
      dateStyle: "long",
    }).format(new Date());

    try {
      window.print();
    } finally {
      searchInput.value = currentQuery;
      renderRecords();
    }
  });
  document.getElementById("detail-close").addEventListener("click", () => detailDialog.close());
  loadIndicators();
})();
