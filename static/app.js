/* 回归看板：只做两件事 —— 拉 /api/state/ 渲染，点按钮调 /api/run/ 或 /api/toggle/ */
(function () {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

  let lastJson = "";

  function toast(msg, kind) {
    const el = $("toast");
    el.textContent = msg;
    el.className = "toast " + (kind || "info");
    if (kind === "info") setTimeout(() => { if (el.textContent === msg) el.className = "toast hide"; }, 6000);
  }

  async function post(url, body) {
    const r = await fetch(url, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {})
    });
    return r.json();
  }

  function renderStats(last) {
    const d = last || { total: 35, passed: 0, failed: 0, pass_rate: 0, duration: 0, bugs_active: 0 };
    const items = [
      ["用例总数", d.total, "hl"], ["通过", d.passed, "ok"], ["失败", d.failed, "bad"],
      ["通过率", (d.pass_rate || 0).toFixed(1) + "%", "hl"],
      ["缺陷单", d.failed || 0, "warn"], ["耗时", (d.duration || 0).toFixed(1) + "s", ""]
    ];
    $("stats").innerHTML = items.map(([l, n, c]) =>
      `<div class="stat ${c}"><div class="n">${esc(n)}</div><div class="l">${esc(l)}</div></div>`).join("");
    $("run-at").textContent = last
      ? `${esc(last.run_at)} · 缺陷开关开启 ${esc(last.bugs_active)}/6`
      : "尚未运行，点上方「一键跑回归」开始";
  }

  function renderCases(last) {
    const box = $("cases");
    if (!last || !last.cases || !last.cases.length) {
      box.innerHTML = '<div class="empty">还没有回归结果。跑完一次后，35 条用例会按模块列在这里。</div>';
      return;
    }
    const groups = {};
    last.cases.forEach(c => { (groups[c.module || "其他"] ||= []).push(c); });
    box.innerHTML = Object.keys(groups).map(g => `
      <div class="case-group"><b>${esc(g)}（${groups[g].length}）</b>
      ${groups[g].map(c => `
        <div class="case-row ${c.status === "failed" ? "fail" : ""}">
          <span class="pill ${c.status === "failed" ? "bad" : "ok"}">${c.status === "failed" ? "失败" : "通过"}</span>
          <span class="name">${esc(c.name)}</span>
          ${c.defect ? `<span class="pill dup">${esc(c.defect)}</span>` : ""}
          <span class="dur">${Math.round((c.duration || 0) * 1000)}ms</span>
        </div>`).join("")}
      </div>`).join("");
  }

  function renderSwitches(flags, labels) {
    $("switches").innerHTML = Object.keys(labels).map(k => `
      <div class="switch-row">
        <div class="txt">${esc(labels[k])}<small class="mono">${esc(k)}</small></div>
        <label class="sw"><input type="checkbox" data-key="${esc(k)}" ${flags[k] ? "checked" : ""}><i></i></label>
      </div>`).join("");
    $("switches").querySelectorAll("input[data-key]").forEach(inp => {
      inp.addEventListener("change", async () => {
        await post("/api/toggle/", { key: inp.dataset.key, value: inp.checked });
        toast(inp.checked ? "已注入该缺陷，重跑回归即可抓到" : "已修复该缺陷，重跑回归即可验证", "info");
        load();
      });
    });
  }

  function renderCalls(calls) {
    if (!calls || !calls.length) { $("calls").innerHTML = '<div class="empty">暂无接口调用</div>'; return; }
    $("calls").innerHTML = `<table><thead><tr><th>方法</th><th>路径</th><th>状态</th><th>耗时</th></tr></thead><tbody>
      ${calls.map(c => `<tr><td class="mono">${esc(c.method)}</td><td class="mono">${esc(c.path)}</td>
        <td><span class="pill ${c.status >= 500 ? "bad" : c.status >= 400 ? "warn" : "ok"}">${esc(c.status)}</span></td>
        <td class="mono">${esc(c.duration_ms)}ms</td></tr>`).join("")}
    </tbody></table>`;
  }

  function renderDefects(defects) {
    $("defects").innerHTML = defects.map(d => `
      <div class="defect-card ${d.found ? "found" : ""}">
        <div class="meta">
          <span class="pill dup">${esc(d.id)}</span>
          <span class="pill ${d.severity.startsWith("P0") ? "bad" : "warn"}">${esc(d.severity)}</span>
          <span class="pill ${d.found ? "bad" : "muted"}">${d.found ? "本轮抓到" : "本轮未触发"}</span>
          <span class="pill ${d.active ? "warn" : "ok"}">${d.active ? "缺陷未修复" : "已模拟修复"}</span>
        </div>
        <h3>${esc(d.title)}</h3>
        <div class="mono" style="font-size:11.8px;color:var(--muted)">${esc(d.endpoint)}</div>
        <details>
          <summary>展开复现步骤与修复建议</summary>
          <dl>
            <dt>前置条件</dt><dd>${esc(d.precondition)}</dd>
            <dt>复现步骤</dt><dd><ol>${d.steps.map(s => `<li>${esc(s)}</li>`).join("")}</ol></dd>
            <dt>预期结果</dt><dd>${esc(d.expected)}</dd>
            <dt>实际结果</dt><dd>${esc(d.actual)}</dd>
            <dt>证据</dt><dd>${esc(d.evidence)}</dd>
            <dt>根因推测</dt><dd>${esc(d.root_cause)}</dd>
            <dt>修复建议</dt><dd>${esc(d.fix)}</dd>
            <dt>关联用例</dt><dd class="mono">${esc(d.case)}</dd>
          </dl>
        </details>
      </div>`).join("");
  }

  function renderRunStatus(run) {
    const running = !!(run && run.running);
    const btn = $("btn-run");
    btn.disabled = running;
    btn.innerHTML = running ? '<span class="spinner"></span>回归运行中…' : "▶ 一键跑回归（35 条）";
    $("run-hint").textContent = running
      ? "pytest 正在逐条调用接口，完成后会自动刷新看板与报告。"
      : (run && run.log ? "上轮日志尾部：" + String(run.log).slice(-160).replace(/\s+/g, " ")
        : "回归会重置商城种子数据 → 逐条调用接口 → 生成 allure-results / JUnit XML / 单页报告 / 缺陷单。");
  }

  async function load(force) {
    try {
      const r = await fetch("/api/state/?t=" + Date.now());
      const j = await r.json();
      const s = j.data || {};
      const sig = JSON.stringify(s);
      if (!force && sig === lastJson) return;
      const wasRunning = lastJson && JSON.parse(lastJson).run_status && JSON.parse(lastJson).run_status.running;
      lastJson = sig;
      renderStats(s.last_run);
      renderCases(s.last_run);
      renderSwitches(s.flags || {}, s.flag_labels || {});
      renderCalls(s.calls);
      renderDefects(s.defects || []);
      renderRunStatus(s.run_status);
      if (wasRunning && s.run_status && !s.run_status.running) {
        const lr = s.last_run || {};
        toast(`回归完成：${lr.passed} 通过 / ${lr.failed} 失败，报告已更新`, lr.failed ? "warn" : "");
      }
    } catch (e) {
      toast("读取看板状态失败：" + e.message, "warn");
    }
  }

  $("btn-run").addEventListener("click", async () => {
    const j = await post("/api/run/", {});
    toast(j.data && j.data.started === false ? "回归已经在跑了，稍等一下" : "已启动回归，35 条用例开始逐条执行…", "info");
    load(true);
  });
  $("btn-fix").addEventListener("click", async () => {
    await post("/api/toggle/", { all: false });
    toast("已模拟开发修完 6 个缺陷。再点「一键跑回归」，应当 35 条全绿。", "info");
    load(true);
  });
  $("btn-inject").addEventListener("click", async () => {
    await post("/api/toggle/", { all: true });
    toast("已重新注入 6 个缺陷。再跑一次即可复现缺陷单。", "info");
    load(true);
  });

  load(true);
  setInterval(() => load(false), 2000);
})();
