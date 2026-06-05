/**
 * Agent 聊天后台前端核心逻辑（全量防御与多维画像兼容版）
 */

// ============================================================
// 1. DOM 节点声明
// ============================================================
const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const resetButton = document.querySelector("#reset-button");
const messages = document.querySelector("#messages");

// 侧边栏及状态面板节点
const stageEl = document.querySelector("#stage");
const riskEl = document.querySelector("#risk");
const scoreEl = document.querySelector("#score");
const intentEl = document.querySelector("#intent");
const memoryEl = document.querySelector("#memory");
const candidatesEl = document.querySelector("#candidates");

// ============================================================
// 2. 状态渲染与核心防御层（重点修复区域）
// ============================================================

/**
 * 渲染全站状态面板
 * 🛡️ 已经为所有潜在的 null 节点加上了安全锁，即使 HTML 缺少某个组件，也绝不卡死后续渲染
 */
function renderState(data) {
  const relationship = data.relationship_state || {};
  const risk = data.risk || {};
  const analysis = data.analysis || {};
  const profile = data.profile || {};

  // 关系阶段渲染
  if (stageEl) {
    stageEl.textContent = `${relationship.stage || "-"} ${relationship.stage_label || ""}`.trim();
  }

  // 风险等级渲染
  if (riskEl) {
    riskEl.textContent = risk.risk_level || "-";
    riskEl.className = risk.risk_level === "high" ? "risk-high" : risk.risk_level === "medium" ? "risk-medium" : "";
  }

  // 综合分数/热情度渲染（兼容旧版 total_score 与新版 profile）
  if (scoreEl) {
    const totalScore = data.ranked?.total_score || profile.warmth;
    scoreEl.textContent = totalScore !== undefined ? Number(totalScore).toFixed(1) : "-";
  }

  // 意图分析渲染
  if (intentEl) {
    intentEl.textContent = analysis.intent || "-";
  }

  // 触发长期记忆与候选回复列表的渲染
  renderMemory(data.memory || {});
  renderCandidates(data.candidates || []);
}

/**
 * 渲染长期记忆面板
 * 🛡️ 头部非空拦截，防止 memoryEl 不存在时抛出 Cannot set properties of null
 */
function renderMemory(memory) {
  if (!memoryEl) return;

  const lines = [];
  if (memory.name) lines.push(`姓名：${memory.name}`);
  if (memory.city) lines.push(`城市：${memory.city}`);
  if (memory.occupation) lines.push(`职业：${memory.occupation}`);

  // 宠物信息解析
  if (Array.isArray(memory.pets) && memory.pets.length) {
    const pet = memory.pets[0];
    lines.push(`宠物：${pet.breed || pet.species || pet.name || "已记录"}`);
  }

  // 兴趣爱好解析
  if (Array.isArray(memory.interests) && memory.interests.length) {
    lines.push(`兴趣：${memory.interests.join("、")}`);
  }

  memoryEl.textContent = lines.length ? lines.join("\n") : "暂无";
}

/**
 * 渲染 6 条候选回复列表
 * 🛡️ 头部非空拦截。同时支持兼容字符串数组与对象数组，自带去油过滤网
 */
function renderCandidates(candidates) {
  if (!candidatesEl) return;

  // 清空现有的候选节点
  candidatesEl.replaceChildren();

  for (const candidate of candidates) {
    const li = document.createElement("li");
    // 自动兼容后端传回的是纯字符串列表还是含有 .text 属性的对象列表
    const textContent = typeof candidate === "string" ? candidate : candidate.text || "";

    // 🚫 【最后防线】如果在调优期间，模型仍然漏出了极个别残留的油腻、打压或卑微话术，前端直接强行屏蔽
    if (textContent.includes("治治我") || textContent.includes("死了那条心")) {
      continue;
    }

    li.textContent = textContent;
    candidatesEl.appendChild(li);
  }
}

// ============================================================
// 3. 聊天气泡与交互流控制
// ============================================================

/**
 * 向聊天面板中追加气泡
 */
function appendBubble(role, text, extraClass = "") {
  if (!messages) return null;

  const bubble = document.createElement("div");
  bubble.className = `bubble ${role} ${extraClass}`.trim();
  const span = document.createElement("span");
  span.textContent = text;
  bubble.appendChild(span);
  messages.appendChild(bubble);

  // 自动滚动到最新消息
  messages.scrollTop = messages.scrollHeight;
  return bubble;
}

/**
 * 设定页面按钮的忙碌状态
 */
function setBusy(isBusy) {
  if (sendButton) {
    sendButton.disabled = isBusy;
    sendButton.textContent = isBusy ? "生成中" : "发送";
  }
  if (resetButton) resetButton.disabled = isBusy;
  if (input) input.disabled = isBusy;
}

/**
 * 发送消息并请求后端 AI 接口
 */
async function sendMessage(text) {
  // 1. 用户气泡上屏，并塞入“正在想怎么回”的 Loading 占位状态
  appendBubble("user", text);
  const loading = appendBubble("assistant", "正在想怎么回...", "loading");
  setBusy(true);

  try {
    // 2. 请求后端 chat 接口
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || data.error || "请求失败");

    // 3. 移除 Loading 占位，将选定的默认最佳回复上屏
    if (loading) loading.remove();
    appendBubble("assistant", data.reply || "我在，你慢慢说");

    // 4. 驱动整个侧边栏状态以及 6 条候选列表的渲染（安全无阻塞跑通）
    renderState(data);
  } catch (error) {
    // 容错层：捕获任意异常（包括网络错误、后端500等），利落报错，不卡死界面
    if (loading) loading.remove();
    appendBubble("assistant", `出错了：${error.message}`);
    console.error("Chat API 交互产生硬错误:", error);
  } finally {
    setBusy(false);
    if (input) input.focus();
  }
}

// ============================================================
// 4. 全局事件监听绑定
// ============================================================

// 表单提交触发发送
if (form) {
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    input.style.height = "auto";
    sendMessage(text);
  });
}

// 输入框高度根据字数动态自适应调整
if (input) {
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
  });

  // 支持回车直接发送（Shift + Enter 换行）
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (form) form.requestSubmit();
    }
  });
}

// 重置按钮监听：清空当前流，保持长期记忆
if (resetButton) {
  resetButton.addEventListener("click", async () => {
    try {
      setBusy(true);
      await fetch("/api/reset", { method: "POST" });
      if (messages) messages.replaceChildren();
      appendBubble("assistant", "当前对话已清空，长期记忆还保留着。");
      if (candidatesEl) candidatesEl.replaceChildren();
    } catch (err) {
      console.error("重置会话失败:", err);
    } finally {
      setBusy(false);
    }
  });
}
