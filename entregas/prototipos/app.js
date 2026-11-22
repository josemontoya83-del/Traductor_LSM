let insightsData = [];

// Precargar datos de entrevistas P4, P5 y P6
const initialData = [
  {
    id: 1,
    insight: "P4: Los usuarios sordos no confían en traducciones automáticas sin opción de verificación.",
    reqFunc: "Modo de revisión manual de glosa antes de enviar",
    reqUX: "Indicador visual del nivel de certeza del modelo IA",
    decisionArq: "Arquitectura basada en eventos con cola de moderación (RabbitMQ/Kafka)",
    prioridad: "1",
    estado: "Validado"
  },
  {
    id: 2,
    insight: "P5: La iluminación deficiente y fondos oscuros reducen drásticamente la precisión del rastreo de señas.",
    reqFunc: "Filtro de preprocesamiento de video y ajuste de contraste automático",
    reqUX: "Alerta en pantalla de 'Poca iluminación' o 'Sombra detectada'",
    decisionArq: "Procesamiento de visión computacional en cliente (WebAssembly / OpenCVJS)",
    prioridad: "2",
    estado: "Validado"
  },
  {
    id: 3,
    insight: "P6: Los intérpretes humanos necesitan atajos de teclado para corregir errores rápidamente.",
    reqFunc: "Atajos de teclado configurables para palabras comunes de la LSM",
    reqUX: "Panel flotante de sugerencias predictivas",
    decisionArq: "Store global de estado reactivo (Redux/Zustand) con caché en LocalStorage",
    prioridad: "3",
    estado: "Pendiente"
  }
];

// Cargar al iniciar
document.addEventListener('DOMContentLoaded', () => {
  const saved = localStorage.getItem('insights_p1');
  if (saved) {
    insightsData = JSON.parse(saved);
  } else {
    insightsData = initialData;
    guardarEnStorage();
  }
  renderTree();
});

// "Ley embebida": Ordenar siempre por prioridad (1=Alta, 2=Media, 3=Baja)
function reordenarPorPrioridad() {
  insightsData.sort((a, b) => parseInt(a.prioridad) - parseInt(b.prioridad));
}

function guardarEnStorage() {
  reordenarPorPrioridad();
  localStorage.setItem('insights_p1', JSON.stringify(insightsData));
}

// Agregar nuevo Insight desde el formulario
document.getElementById('insightForm').addEventListener('submit', (e) => {
  e.preventDefault();
  
  const newItem = {
    id: Date.now(),
    insight: document.getElementById('insight').value.trim(),
    reqFunc: document.getElementById('reqFunc').value.trim(),
    reqUX: document.getElementById('reqUX').value.trim(),
    decisionArq: document.getElementById('decisionArq').value.trim(),
    prioridad: document.getElementById('prioridad').value,
    estado: document.getElementById('estado').value
  };

  insightsData.push(newItem);
  guardarEnStorage();
  renderTree();
  e.target.reset();
});

// Renderizar la vista de árbol
function renderTree() {
  reordenarPorPrioridad();
  const container = document.getElementById('treeView');
  document.getElementById('totalCounter').innerText = `${insightsData.length} Registro(s)`;
  container.innerHTML = '';

  if (insightsData.length === 0) {
    container.innerHTML = '<p style="text-align:center; color:#9ca3af; padding: 20px;">No hay insights registrados.</p>';
    return;
  }

  insightsData.forEach((item) => {
    const prioLabel = item.prioridad === '1' ? 'Alta' : item.prioridad === '2' ? 'Media' : 'Baja';
    const prioClass = item.prioridad === '1' ? 'badge-alta' : item.prioridad === '2' ? 'badge-media' : 'badge-baja';
    const estadoClass = item.estado === 'Validado' ? 'badge-validado' : 'badge-pendiente';

    const node = document.createElement('div');
    node.className = 'tree-node';
    node.innerHTML = `
      <div class="node-header">
        <span class="insight-title">💡 ${item.insight}</span>
        <div class="node-tags">
          <span class="badge ${prioClass}">Prioridad: ${prioLabel}</span>
          <span class="badge ${estadoClass}">${item.estado}</span>
        </div>
      </div>
      <div class="tree-branches">
        <div class="branch-item">
          <span class="branch-icon">└── ⚙️</span>
          <span class="branch-label">Requisito Funcional:</span>
          <span class="branch-value">${item.reqFunc}</span>
        </div>
        <div class="branch-item">
          <span class="branch-icon">└── 🎨</span>
          <span class="branch-label">Requisito UX:</span>
          <span class="branch-value">${item.reqUX}</span>
        </div>
        <div class="branch-item">
          <span class="branch-icon">└── 🏗️</span>
          <span class="branch-label">Decisión Arq:</span>
          <span class="branch-value"><strong>${item.decisionArq}</strong></span>
        </div>
      </div>
      <div class="node-controls">
        <label style="font-size:0.8rem;">Cambiar Prioridad:</label>
        <select class="select-inline" onchange="cambiarPrioridad(${item.id}, this.value)">
          <option value="1" ${item.prioridad === '1' ? 'selected' : ''}>Alta</option>
          <option value="2" ${item.prioridad === '2' ? 'selected' : ''}>Media</option>
          <option value="3" ${item.prioridad === '3' ? 'selected' : ''}>Baja</option>
        </select>
        <button class="btn btn-secondary" onclick="eliminarItem(${item.id})" style="padding: 4px 8px; font-size: 0.8rem; color: #dc2626;">Eliminar</button>
      </div>
    `;
    container.appendChild(node);
  });
}

// "Ley embebida" en acción al cambiar select de prioridad
function cambiarPrioridad(id, nuevaPrioridad) {
  const item = insightsData.find(i => i.id === id);
  if (item) {
    item.prioridad = nuevaPrioridad;
    guardarEnStorage();
    renderTree(); // Se reordena y vuelve a pintar de inmediato
  }
}

function eliminarItem(id) {
  insightsData = insightsData.filter(i => i.id !== id);
  guardarEnStorage();
  renderTree();
}

// Exportar a JSON
function exportarJSON() {
  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(insightsData, null, 2));
  const downloadAnchor = document.createElement('a');
  downloadAnchor.setAttribute("href", dataStr);
  downloadAnchor.setAttribute("download", "mapeo_requerimientos.json");
  document.body.appendChild(downloadAnchor);
  downloadAnchor.click();
  downloadAnchor.remove();
}

// Exportar a CSV
function exportarCSV() {
  let csvContent = "data:text/csv;charset=utf-8,ID,Insight,Requisito_Funcional,Requisito_UX,Decision_Arquitectura,Prioridad,Estado\n";
  insightsData.forEach(row => {
    const cleanInsight = `"${row.insight.replace(/"/g, '""')}"`;
    const cleanFunc = `"${row.reqFunc.replace(/"/g, '""')}"`;
    const cleanUX = `"${row.reqUX.replace(/"/g, '""')}"`;
    const cleanArq = `"${row.decisionArq.replace(/"/g, '""')}"`;
    csvContent += `${row.id},${cleanInsight},${cleanFunc},${cleanUX},${cleanArq},${row.prioridad},${row.estado}\n`;
  });

  const encodedUri = encodeURI(csvContent);
  const link = document.createElement('a');
  link.setAttribute('href', encodedUri);
  link.setAttribute('download', 'mapeo_requerimientos.csv');
  document.body.appendChild(link);
  link.click();
  link.remove();
}