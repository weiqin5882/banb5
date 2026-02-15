let sessionId = null;
let currentOfficialMap = {};
let currentServiceMap = {};
let requiredKeys = [];
let allRows = [];
let page = 1;
const pageSize = 20;
let sortKey = 'index';
let sortAsc = true;

const keyLabels = {
  order_id: "订单号",
  product_name: "商品名称",
  order_status: "订单状态",
  sales_amount: "销售金额",
  cost_amount: "成本金额",
};

function makeSelect(options, selected, id) {
  const opts = ['<option value="">-- 请选择 --</option>']
    .concat(options.map(c => `<option value="${c}" ${c === selected ? 'selected' : ''}>${c}</option>`))
    .join('');
  return `<select class="form-select form-select-sm" id="${id}">${opts}</select>`;
}

function renderMappings(data) {
  requiredKeys = data.required_keys;
  currentOfficialMap = data.official_auto_mapping;
  currentServiceMap = data.service_auto_mapping;

  let html = '<div class="row"><div class="col-md-6"><h6>官方订单表</h6>';
  requiredKeys.forEach(k => {
    html += `<label class="form-label mt-2">${keyLabels[k]}</label>`;
    html += makeSelect(data.official_columns, currentOfficialMap[k], `off_${k}`);
  });
  html += '</div><div class="col-md-6"><h6>客服统计表</h6>';
  requiredKeys.forEach(k => {
    html += `<label class="form-label mt-2">${keyLabels[k]}</label>`;
    html += makeSelect(data.service_columns, currentServiceMap[k], `srv_${k}`);
  });
  html += '</div></div>';

  document.getElementById('mappingContainer').innerHTML = html;
  document.getElementById('mappingCard').style.display = 'block';
}

function collectMapping(prefix) {
  const m = {};
  requiredKeys.forEach(k => {
    m[k] = document.getElementById(`${prefix}_${k}`).value;
  });
  return m;
}

function sortRows(rows) {
  const copy = [...rows];
  copy.sort((a, b) => {
    const va = a[sortKey];
    const vb = b[sortKey];
    if (typeof va === 'number' && typeof vb === 'number') return sortAsc ? va - vb : vb - va;
    return sortAsc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
  });
  return copy;
}

function renderTablePage() {
  const sorted = sortRows(allRows);
  const start = (page - 1) * pageSize;
  const pageRows = sorted.slice(start, start + pageSize);

  const tbody = document.querySelector('#resultTable tbody');
  tbody.innerHTML = pageRows.map(r => {
    const cls = r.is_loss ? 'loss-row' : '';
    return `<tr class="${cls}">
      <td>${r.index}</td><td>${r.order_id || ''}</td><td>${r.product_name || ''}</td>
      <td>${Number(r.sales_amount).toFixed(2)}</td><td>${Number(r.cost_amount).toFixed(2)}</td>
      <td>${Number(r.profit).toFixed(2)}</td><td>${r.final_status}</td>
    </tr>`;
  }).join('');

  const totalPages = Math.max(1, Math.ceil(allRows.length / pageSize));
  document.getElementById('pagination').innerHTML = `
    <button class="btn btn-sm btn-outline-secondary" ${page <= 1 ? 'disabled' : ''} onclick="window.__goPage(${page - 1})">上一页</button>
    <span>第 ${page} / ${totalPages} 页</span>
    <button class="btn btn-sm btn-outline-secondary" ${page >= totalPages ? 'disabled' : ''} onclick="window.__goPage(${page + 1})">下一页</button>
  `;
}

window.__goPage = function (targetPage) {
  const totalPages = Math.max(1, Math.ceil(allRows.length / pageSize));
  page = Math.min(totalPages, Math.max(1, targetPage));
  renderTablePage();
}

function renderResults(payload) {
  allRows = payload.rows || [];
  page = 1;
  renderTablePage();

  const s = payload.summary;
  document.getElementById('summary').innerHTML = `
    <div class="alert alert-info">
      总销售额: ${s.total_sales.toFixed(2)} | 总成本: ${s.total_cost.toFixed(2)} | 总利润: ${s.total_profit.toFixed(2)} |
      订单总数: ${s.order_count} | 正常匹配: ${s.matched_count} | 客服漏记: ${s.missing_count} | 客服多记: ${s.extra_count} | 亏损订单: ${s.loss_count}
    </div>`;

  document.getElementById('warnings').innerHTML = (payload.warnings || [])
    .map(w => `<div class="alert alert-warning py-1 px-2">${w}</div>`).join('');

  document.getElementById('resultCard').style.display = 'block';
}

document.querySelectorAll('#resultTable thead th.sortable').forEach(th => {
  th.addEventListener('click', () => {
    const key = th.dataset.key;
    if (sortKey === key) sortAsc = !sortAsc;
    else {
      sortKey = key;
      sortAsc = true;
    }
    renderTablePage();
  });
});

document.getElementById('uploadBtn').addEventListener('click', async () => {
  const official = document.getElementById('officialFile').files[0];
  const service = document.getElementById('serviceFile').files[0];
  if (!official || !service) {
    alert('请先选择两个文件');
    return;
  }

  const formData = new FormData();
  formData.append('official_file', official);
  formData.append('service_file', service);

  document.getElementById('uploadStatus').textContent = '上传中...';
  const res = await fetch('/api/upload', { method: 'POST', body: formData });
  const data = await res.json();
  if (!res.ok) {
    alert(data.detail || '上传失败');
    return;
  }

  sessionId = data.session_id;
  document.getElementById('uploadStatus').textContent = `上传成功，会话ID: ${sessionId}`;
  renderMappings(data);
});

document.getElementById('compareBtn').addEventListener('click', async () => {
  if (!sessionId) return;

  const officialMapping = collectMapping('off');
  const serviceMapping = collectMapping('srv');

  const formData = new FormData();
  formData.append('session_id', sessionId);
  formData.append('official_mapping', JSON.stringify(officialMapping));
  formData.append('service_mapping', JSON.stringify(serviceMapping));

  const res = await fetch('/api/compare', { method: 'POST', body: formData });
  const data = await res.json();
  if (!res.ok) {
    alert(`比对失败: ${JSON.stringify(data.detail)}`);
    return;
  }

  renderResults(data);
});

document.getElementById('exportBtn').addEventListener('click', () => {
  if (!sessionId) return;
  window.location.href = `/api/export/${sessionId}`;
});
