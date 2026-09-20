let insights = JSON.parse(localStorage.getItem('insights_data')) || [
  { id: 1, insight: "Los usuarios sordos no confían en traducciones automáticas sin revisión humana (P4)", reqFunc: "Modo de revisión manual", reqUX: "Etiqueta visual de estado de revisión", decisionArq: "Sistema de colas asíncronas para revisión", prioridad: 1, estado: "Validado" },
  { id: 2, insight: "Diccionario visual necesita carga rápida de clips cortos (P5)", reqFunc: "Buscador de señas con precarga", reqUX: "Reproductor de video liviano en bucle", decisionArq: "Almacenamiento en CDN e índices en base de datos", prioridad: 2, estado: "Pendiente" },
  { id: 3, insight: "Se requiere historial accesible de sesiones pasadas (P6)", reqFunc: "Guardado de sesiones de traducción", reqUX: "Lista cronológica filtrable", decisionArq: "Tabla sesion_traduccion con índice por fecha", prioridad: 3, estado: "Validado" }
];

document.getElementById('insightForm').addEventListener('submit', (e) => {
  e.preventDefault();
  const nuevo = {
    id: Date.now(),
    insight: document.getElementById('insight').value,
    reqFunc: document.getElementById('reqFunc').value,
    reqUX: document.getElementById('reqUX').value,
    decisionArq: document.getElementById('decisionArq').value,
    prioridad: parseInt(document.getElementById('prioridad').value),
    estado: document.getElementById('estado').value
  };
  insights.push(nuevo);
  guardarYRenderizar();
  e.target.reset();
});

function cambiarPrioridad(id, nuevaPrio) {
  const item = insights.find(i => i.id === id);
  if (item) {
    item.prioridad = parseInt(nuevaPrio);
    guardarYRenderizar(); // Recalcula y vuelve a pintar la lista reordenada
  }
}

function borrarInsight(id) {
  insights = insights.filter(i => i.id !== id);
  guardarYRenderizar();
}

function guardarYRenderizar() {
  // ORDENAR AUTOMÁTICAMENTE POR PRIORIDAD (1 = Alta, 2 = Media, 3 = Baja)
  insights.sort((a, b) => a.prioridad - b.prioridad);
  
  localStorage.setItem('insights_data', JSON.stringify(insights));
  
  const treeView = document.getElementById('treeView');
  treeView.innerHTML = '';

  insights.forEach(item => {
    const prioTexto = item.prioridad === 1 ? 'Alta' : item.prioridad === 2 ? 'Media' : 'Baja';
    const div = document.createElement('div');
    div.className = 'node-insight';
    div.innerHTML = `
      <div>
        <strong>Insight:</strong> ${item.insight} 
        <span class="badge prio-${item.prioridad}">Prioridad: ${prioTexto}</span>
        <em>[${item.estado}]</em>
        <select onchange="cambiarPrioridad(${item.id}, this.value)">
          <option value="1" ${item.prioridad === 1 ? 'selected' : ''}>Cambiar a Alta</option>
          <option value="2" ${item.prioridad === 2 ? 'selected' : ''}>Cambiar a Media</option>
          <option value="3" ${item.prioridad === 3 ? 'selected' : ''}>Cambiar a Baja</option>
        </select>
        <button onclick="borrarInsight(${item.id})" style="background:red; padding:2px 5px; margin-left:5px;">X</button>
      </div>
      <div class="node-req"><strong>↳ Funcional:</strong> ${item.reqFunc} | <strong>UX:</strong> ${item.reqUX}</div>
      <div class="node-arq"><strong>  ↳ Arquitectura:</strong> ${item.decisionArq}</div>
    `;
    treeView.appendChild(div);
  });
}

function exportarJSON() {
  const blob = new Blob([JSON.stringify(insights, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'insights.json';
  a.click();
}

function exportarCSV() {
  let csv = 'ID,Insight,ReqFuncional,ReqUX,DecisionArquitectura,Prioridad,Estado\n';
  insights.forEach(row => {
    csv += `"${row.id}","${row.insight}","${row.reqFunc}","${row.reqUX}","${row.decisionArq}","${row.prioridad}","${row.estado}"\n`;
  });
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'insights.csv';
  a.click();
}

// Carga inicial al abrir la página
guardarYRenderizar();