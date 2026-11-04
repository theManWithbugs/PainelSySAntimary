(() => {
  const mapElement = document.getElementById("map");
  if (!mapElement || !window.L || !window.proj4) {
    const message = document.getElementById("map-message");
    if (message) {
      message.textContent = "Não foi possível iniciar o mapa. Verifique sua conexão e recarregue a página.";
      message.classList.add("error");
      message.hidden = false;
    }
    return;
  }

  const map = L.map(mapElement, { zoomControl: false, scrollWheelZoom: true });
  L.control.zoom({ position: "bottomright" }).addTo(map);
  L.control.attribution({ prefix: false }).addTo(map);

  const streetTiles = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  });
  const satelliteTiles = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 19, maxNativeZoom: 17, attribution: "Tiles &copy; Esri", className: "satellite-tiles" },
  );
  let showingSatellite = true;
  satelliteTiles.addTo(map);
  map.setView([-9.3, -68.21], 10);

  proj4.defs("EPSG:29189", "+proj=utm +zone=19 +south +ellps=aust_SA +towgs84=-57,1,-41,0,0,0,0 +units=m +no_defs");
  proj4.defs("EPSG:20049", "+proj=utm +zone=19 +south +ellps=GRS80 +units=m +no_defs");

  const message = document.getElementById("map-message");
  const coordinates = document.getElementById("map-coordinates");
  const markerButton = document.getElementById("marker-button");
  const layersPanel = document.getElementById("camadas");
  const recordPanel = document.getElementById("record-panel");
  const recordImages = document.getElementById("record-images");
  const recordFields = document.getElementById("record-fields");
  const recordResidents = document.getElementById("record-residents");
  const recordResidentList = document.getElementById("record-resident-list");
  const collectedCount = document.getElementById("collected-count");
  let markerMode = false;
  let boundaryLayer;
  let lotsLayer;
  let roadsLayer;
  const collectedLayer = L.featureGroup().addTo(map);
  const ugaiLayer = L.layerGroup().addTo(map);
  let selectedCollectedMarker;

  function showMessage(text, isError = false) {
    message.textContent = text;
    message.classList.toggle("error", isError);
    message.hidden = false;
    if (!isError) {
      window.setTimeout(() => {
        message.hidden = true;
      }, 3200);
    }
  }

  function transformCoordinates(coordinate, sourceCode) {
    if (
      Array.isArray(coordinate) &&
      coordinate.length >= 2 &&
      typeof coordinate[0] === "number" &&
      typeof coordinate[1] === "number"
    ) {
      const [longitude, latitude] = proj4(sourceCode, "EPSG:4326", coordinate);
      return [longitude, latitude, ...coordinate.slice(2)];
    }
    if (Array.isArray(coordinate)) {
      return coordinate.map((part) => transformCoordinates(part, sourceCode));
    }
    throw new Error("A geometria contém coordenadas inválidas.");
  }

  function transformFeatureCollection(collection, sourceCode) {
    return {
      ...collection,
      features: collection.features.map((feature) => ({
        ...feature,
        geometry: {
          ...feature.geometry,
          coordinates: transformCoordinates(feature.geometry.coordinates, sourceCode),
        },
      })),
    };
  }

  async function loadLayer(path, sourceCode) {
    const response = await fetch(path);
    if (!response.ok) {
      throw new Error(`Falha ao carregar ${path} (HTTP ${response.status}).`);
    }
    const collection = await response.json();
    if (collection.type !== "FeatureCollection" || !Array.isArray(collection.features)) {
      throw new Error(`O arquivo ${path} não contém uma coleção GeoJSON válida.`);
    }
    return sourceCode ? transformFeatureCollection(collection, sourceCode) : collection;
  }

  function createPopup(kicker, title, detail) {
    const content = document.createElement("div");
    content.className = "feature-popup";

    const heading = document.createElement("div");
    heading.className = "feature-popup-kicker";
    heading.textContent = kicker;
    content.appendChild(heading);

    const name = document.createElement("div");
    name.className = "feature-popup-title";
    name.textContent = title;
    content.appendChild(name);

    if (detail) {
      const extra = document.createElement("div");
      extra.className = "feature-popup-detail";
      extra.textContent = detail;
      content.appendChild(extra);
    }
    return content;
  }

  function lotStyle(feature) {
    const lotNumber = feature.properties.Numero_Lote || "";
    const numericPart = Number.parseInt(lotNumber.match(/\d+/)?.[0] || "0", 10);
    return {
      color: "#9b7948",
      weight: 1.2,
      opacity: 0.9,
      fillColor: numericPart % 2 === 0 ? "#d2ba8a" : "#c7ad7b",
      fillOpacity: 0.14,
    };
  }

  function setupInteractions() {
    boundaryLayer = L.geoJSON(boundaryData, {
      style: { color: "#f5f2df", weight: 3, opacity: 0.95 },
      onEachFeature: (feature, layer) => {
        const properties = feature.properties || {};
        layer.bindPopup(createPopup("Unidade de conservação", properties.NOME || "Antimary", properties.CATEGORIA || "Floresta Estadual"));
      },
    }).addTo(map);

    lotsLayer = L.geoJSON(lotsData, {
      style: lotStyle,
      onEachFeature: (feature, layer) => {
        const properties = feature.properties || {};
        const details = [];
        if (properties.Propriedade) details.push(properties.Propriedade);
        if (properties.Hectares) details.push(`${Number(properties.Hectares).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} ha`);
        layer.bindPopup(createPopup("Lote", properties.Numero_Lote || "Lote sem identificação", details.join(" · ")));
        layer.on({
          mouseover: () => layer.setStyle({ weight: 2, color: "#775c35", fillOpacity: 0.62 }),
          mouseout: () => lotsLayer.resetStyle(layer),
        });
      },
    }).addTo(map);

    roadsLayer = L.geoJSON(roadsData, {
      style: { color: "#f0d7a2", weight: 1.5, opacity: 0.82, dashArray: "5 4" },
      onEachFeature: (_feature, layer) => {
        layer.bindPopup(createPopup("Acesso", "Ramal da floresta", "Trecho da malha de acesso"));
        layer.on({
          mouseover: () => layer.setStyle({ color: "#765a37", weight: 3 }),
          mouseout: () => roadsLayer.resetStyle(layer),
        });
      },
    }).addTo(map);

    const ugaiIcon = L.divIcon({
      className: "ugai-marker",
      html: '<span aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M4 20h16M6 20V9l6-5 6 5v11M9 20v-6h6v6M9 10h.01M15 10h.01"/></svg></span>',
      iconSize: [33, 33],
      iconAnchor: [16, 16],
    });
    const ugaiMarker = L.marker([-9.3338, -68.3204], { icon: ugaiIcon }).addTo(ugaiLayer);
    ugaiMarker.bindPopup(
      createPopup(
        "Base de apoio",
        "UGAI do Antimary",
        "Unidade de Gestão Ambiental Integrada · -9.3338°, -68.3204°",
      ),
    );
    const ugaiTooltip = document.createElement("span");
    ugaiTooltip.textContent = "UGAI do Antimary";
    ugaiMarker.bindTooltip(ugaiTooltip, {
      direction: "top",
      offset: [0, -16],
      className: "record-marker-tooltip",
    });

    document.getElementById("layer-collected").addEventListener("change", (event) => {
      toggleLayer(event.currentTarget.checked, collectedLayer);
    });
    document.getElementById("layer-ugai").addEventListener("change", (event) => {
      toggleLayer(event.currentTarget.checked, ugaiLayer);
    });

    const boundaryBounds = boundaryLayer.getBounds();
    if (boundaryBounds.isValid()) {
      map.fitBounds(boundaryBounds, { padding: [22, 22] });
    } else {
      throw new Error("O limite da floresta não possui uma extensão geográfica válida.");
    }

    document.getElementById("layer-boundary").addEventListener("change", (event) => {
      toggleLayer(event.currentTarget.checked, boundaryLayer);
    });
    document.getElementById("layer-lots").addEventListener("change", (event) => {
      toggleLayer(event.currentTarget.checked, lotsLayer);
    });
    document.getElementById("layer-roads").addEventListener("change", (event) => {
      toggleLayer(event.currentTarget.checked, roadsLayer);
    });
  }

  function toggleLayer(visible, layer) {
    if (visible) layer.addTo(map);
    else map.removeLayer(layer);
  }

  function collectedIcon(selected = false) {
    return L.divIcon({
      className: selected ? "collected-marker collected-marker-selected" : "collected-marker",
      html: '<span aria-hidden="true"></span>',
      iconSize: [20, 20],
      iconAnchor: [10, 10],
    });
  }

  function formatFieldValue(value) {
    if (Array.isArray(value)) return value.map(formatFieldValue).join(", ");
    if (value && typeof value === "object") return JSON.stringify(value, null, 2);
    if (typeof value === "boolean") return value ? "Sim" : "Não";
    return String(value);
  }

  function closeRecordPanel() {
    recordPanel.hidden = true;
    layersPanel.hidden = false;
    if (selectedCollectedMarker) {
      selectedCollectedMarker.setIcon(collectedIcon());
      selectedCollectedMarker = null;
    }
  }

  function showRecordPanel(record, marker) {
    if (selectedCollectedMarker && selectedCollectedMarker !== marker) {
      selectedCollectedMarker.setIcon(collectedIcon());
    }
    selectedCollectedMarker = marker;
    selectedCollectedMarker.setIcon(collectedIcon(true));
    layersPanel.hidden = true;
    recordPanel.hidden = false;
    document.getElementById("record-title").textContent = record.title;
    document.getElementById("record-location").textContent =
      `Coordenadas: ${record.latitude.toFixed(5)}°, ${record.longitude.toFixed(5)}°`;

    recordImages.replaceChildren();
    for (const image of record.images || []) {
      if (!image.url || new URL(image.url).hostname !== "res.cloudinary.com") continue;
      const link = document.createElement("a");
      link.className = "record-image-link";
      link.href = image.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.setAttribute("aria-label", image.name || "Abrir imagem da coleta");

      const element = document.createElement("img");
      element.src = image.url;
      element.alt = image.name || "Imagem da coleta";
      element.loading = "lazy";
      link.appendChild(element);
      recordImages.appendChild(link);
    }

    recordFields.replaceChildren();
    for (const field of record.fields || []) {
      const item = document.createElement("dl");
      item.className = "record-field";
      const label = document.createElement("dt");
      label.textContent = field.label;
      const value = document.createElement("dd");
      value.textContent = formatFieldValue(field.value);
      item.append(label, value);
      recordFields.appendChild(item);
    }
    if (!recordFields.childElementCount) {
      const empty = document.createElement("p");
      empty.className = "layers-hint";
      empty.textContent = "Este registro não possui outras informações.";
      recordFields.appendChild(empty);
    }

    recordResidentList.replaceChildren();
    for (const resident of record.residents || []) {
      const card = document.createElement("article");
      card.className = "record-resident";
      const name = document.createElement("h5");
      name.textContent = resident.name || "Morador sem nome informado";
      card.appendChild(name);
      for (const field of resident.fields || []) {
        const item = document.createElement("dl");
        item.className = "record-field";
        const label = document.createElement("dt");
        label.textContent = field.label;
        const value = document.createElement("dd");
        value.textContent = formatFieldValue(field.value);
        item.append(label, value);
        card.appendChild(item);
      }
      recordResidentList.appendChild(card);
    }
    recordResidents.hidden = !recordResidentList.childElementCount;
  }

  async function loadMoradores() {
    try {
      const response = await fetch("/api/moradores/", { headers: { Accept: "application/json" } });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || `Falha ao carregar os registros (HTTP ${response.status}).`);
      }
      if (!Array.isArray(payload.moradores)) {
        throw new Error("A resposta do Firebase não contém uma lista de moradores.");
      }

      for (const record of payload.moradores) {
        if (
          !Number.isFinite(record.latitude) ||
          !Number.isFinite(record.longitude) ||
          !Array.isArray(record.fields) ||
          !Array.isArray(record.residents) ||
          !Array.isArray(record.images)
        ) {
          throw new Error("Um registro recebido do Firebase está em formato inválido.");
        }
        const marker = L.marker([record.latitude, record.longitude], { icon: collectedIcon() });
        const tooltip = document.createElement("span");
        tooltip.textContent = "Ponto coletado";
        marker.bindTooltip(tooltip, { direction: "top", offset: [0, -30], className: "record-marker-tooltip" });
        marker.on("click", () => showRecordPanel(record, marker));
        collectedLayer.addLayer(marker);
      }

      collectedCount.textContent = `${payload.moradores.length} pontos carregados`;
      showMessage(
        payload.moradores.length
          ? `${payload.moradores.length} pontos coletados carregados do Firebase.`
          : "Nenhum ponto com coordenadas válidas foi encontrado na coleção.",
      );
    } catch (error) {
      console.error("Erro ao carregar pontos coletados:", error);
      collectedCount.textContent = "Indisponível";
      showMessage(error.message || "Não foi possível carregar os pontos coletados.", true);
    }
  }

  function createUserMarker(latlng) {
    const markerIcon = L.divIcon({
      className: "user-marker-icon",
      html: '<span aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></svg></span>',
      iconSize: [31, 37],
      iconAnchor: [15, 36],
    });
    const marker = L.marker(latlng, { icon: markerIcon, draggable: true }).addTo(map);
    marker.bindPopup(createPopup("Ponto marcado", "Localização personalizada", `${latlng.lat.toFixed(5)}, ${latlng.lng.toFixed(5)}`)).openPopup();
    marker.on("dragend", () => {
      const position = marker.getLatLng();
      marker.setPopupContent(createPopup("Ponto marcado", "Localização personalizada", `${position.lat.toFixed(5)}, ${position.lng.toFixed(5)}`));
    });
  }

  map.on("mousemove", (event) => {
    coordinates.textContent = `COORDENADAS: ${event.latlng.lat.toFixed(5)}°, ${event.latlng.lng.toFixed(5)}°`;
  });
  map.on("click", (event) => {
    if (!markerMode) return;
    createUserMarker(event.latlng);
    markerMode = false;
    markerButton.classList.remove("is-active");
    map.getContainer().classList.remove("map-is-marking");
    showMessage("Ponto adicionado. Arraste o ícone para ajustar a posição.");
  });

  markerButton.addEventListener("click", () => {
    markerMode = !markerMode;
    markerButton.classList.toggle("is-active", markerMode);
    map.getContainer().classList.toggle("map-is-marking", markerMode);
    showMessage(markerMode ? "Clique no mapa para adicionar um ponto." : "Marcação cancelada.");
  });
  document.getElementById("record-close").addEventListener("click", closeRecordPanel);

  document.getElementById("locate-button").addEventListener("click", () => {
    if (!navigator.geolocation) {
      showMessage("Este navegador não oferece suporte à localização.", true);
      return;
    }
    showMessage("Obtendo sua localização…");
    map.locate({ setView: true, maxZoom: 14 });
  });
  map.on("locationfound", (event) => {
    L.circleMarker(event.latlng, {
      radius: 7,
      color: "#fff",
      weight: 3,
      fillColor: "#3476b5",
      fillOpacity: 1,
    }).addTo(map).bindPopup(createPopup("Sua localização", "Você está aqui", `${event.latlng.lat.toFixed(5)}, ${event.latlng.lng.toFixed(5)}`)).openPopup();
    showMessage("Localização encontrada.");
  });
  map.on("locationerror", (event) => {
    showMessage(`Não foi possível obter sua localização: ${event.message}`, true);
  });

  document.getElementById("basemap-button").addEventListener("click", (event) => {
    showingSatellite = !showingSatellite;
    if (showingSatellite) {
      map.removeLayer(streetTiles);
      satelliteTiles.addTo(map);
    } else {
      map.removeLayer(satelliteTiles);
      streetTiles.addTo(map);
    }
    event.currentTarget.setAttribute("aria-label", showingSatellite ? "Alternar para mapa de ruas" : "Alternar mapa e satélite");
    showMessage(showingSatellite ? "Imagem de satélite ativada." : "Mapa de ruas ativado.");
  });

  let boundaryData;
  let lotsData;
  let roadsData;
  Promise.all([
    loadLayer("/static/mapa/dados/limites.geojson"),
    loadLayer("/static/mapa/dados/lotes.geojson", "EPSG:29189"),
    loadLayer("/static/mapa/dados/ramais.geojson", "EPSG:20049"),
  ])
    .then(([boundary, lots, roads]) => {
      boundaryData = boundary;
      lotsData = lots;
      roadsData = roads;
      setupInteractions();
      loadMoradores();
    })
    .catch((error) => {
      console.error("Erro ao carregar as camadas do mapa:", error);
      showMessage("Não foi possível carregar as camadas geográficas. Verifique a conexão e tente novamente.", true);
    });
})();
