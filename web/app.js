/**
 * Agent 聊天后台前端核心逻辑（多会话路由与命名隔离版）
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
const favorabilityDetailEl = document.querySelector("#favorability-detail");
const intentEl = document.querySelector("#intent");
const memoryEl = document.querySelector("#memory");
const candidatesEl = document.querySelector("#candidates");
const opportunityActionEl = document.querySelector("#opportunity-action");
const opportunityReasonEl = document.querySelector("#opportunity-reason");
const opportunityNextEl = document.querySelector("#opportunity-next");
const coachWhyEl = document.querySelector("#coach-why");
const coachSendNoteEl = document.querySelector("#coach-send-note");
const coachPointsEl = document.querySelector("#coach-points");
const offlineReadinessEl = document.querySelector("#offline-readiness");
const offlineTopicsEl = document.querySelector("#offline-topics");
const offlineRescueEl = document.querySelector("#offline-rescue");
const confidenceStreakEl = document.querySelector("#confidence-streak");
const confidenceEncouragementEl = document.querySelector("#confidence-encouragement");
const confidenceWinsEl = document.querySelector("#confidence-wins");

// 💡 核心新增：会话命名管理器节点
const sessionSelect = document.querySelector("#session-select");
const addSessionBtn = document.querySelector("#add-session-btn");
let lastResponseData = null;

// ============================================================
// 2. 状态渲染与核心防御层
// ============================================================

function renderState(data) {
  const relationship = data.relationship_state || {};
  const risk = data.risk || {};
  const analysis = data.analysis || {};
  const profile = data.profile || {};

  if (stageEl) {
    stageEl.textContent = `${relationship.stage || "-"} ${relationship.stage_label || ""}`.trim();
  }

  if (riskEl) {
    riskEl.textContent = risk.risk_level || "-";
    riskEl.className = risk.risk_level === "high" ? "risk-high" : risk.risk_level === "medium" ? "risk-medium" : "";
  }

  if (scoreEl) {
    const favorabilityScore = relationship.favorability_score;
    const fallbackScore = data.ranked?.total_score || profile.warmth;
    const displayScore = favorabilityScore !== undefined ? favorabilityScore : fallbackScore;
    scoreEl.textContent = displayScore !== undefined ? `${Number(displayScore).toFixed(1)}/100` : "-";
  }

  if (favorabilityDetailEl) {
    const label = relationship.favorability_label || "陌生观望";
    const boundary = relationship.intimacy_boundary || "不要推进身体接触。";
    favorabilityDetailEl.textContent = `${label}｜${boundary}`;
  }

  if (intentEl) {
    intentEl.textContent = analysis.intent || "-";
  }

  renderMemory(data.memory || {});
  renderCandidates(data.candidates || []);
  renderGrowthSupport(data.growth_support || {}, data.memory || {});
}

function renderMemory(memory) {
  if (!memoryEl) return;

  const lines = [];
  if (memory.name) lines.push(`姓名：${memory.name}`);
  if (memory.city) lines.push(`城市：${memory.city}`);
  if (memory.occupation) lines.push(`职业：${memory.occupation}`);

  if (Array.isArray(memory.pets) && memory.pets.length) {
    const pet = memory.pets[0];
    lines.push(`宠物：${pet.breed || pet.species || pet.name || "已记录"}`);
  }

  if (Array.isArray(memory.interests) && memory.interests.length) {
    lines.push(`兴趣：${memory.interests.join("、")}`);
  }

  memoryEl.textContent = lines.length ? lines.join("\n") : "暂无";
}

function renderCandidates(candidates) {
  if (!candidatesEl) return;
  candidatesEl.replaceChildren();

  candidates.forEach((candidate, index) => {
    const li = document.createElement("li");
    const textContent = typeof candidate === "string" ? candidate : candidate.text || "";

    // 【边界熔断拦截】
    if (textContent.includes("治治我") || textContent.includes("死了那条心")) {
      return;
    }

    const text = document.createElement("span");
    text.textContent = textContent;

    const copyButton = document.createElement("button");
    copyButton.type = "button";
    copyButton.className = "candidate-copy-button";
    copyButton.textContent = "复制";
    copyButton.addEventListener("click", async () => {
      await copyText(textContent);
      await sendFeedback({
        action: "candidate_copy",
        selectedReply: textContent,
        editedReply: textContent,
        turnId: lastResponseData?.turn_id || "",
        selectedIndex: index,
      });
      copyButton.textContent = "已复制";
      setTimeout(() => {
        copyButton.textContent = "复制";
      }, 1000);
    });

    li.append(text, copyButton);
    candidatesEl.appendChild(li);
  });
}

function renderGrowthSupport(growthSupport, memory) {
  const socialCoach = growthSupport.social_coach || {};
  const opportunity = growthSupport.opportunity || {};
  const offlineAssist = growthSupport.offline_assist || {};
  const confidence = growthSupport.confidence || memory.confidence || {};

  if (opportunityActionEl) {
    const confidenceText = opportunity.confidence !== undefined ? ` ${Number(opportunity.confidence).toFixed(0)}%` : "";
    opportunityActionEl.textContent = `${opportunity.action || "-"}${confidenceText}`;
  }
  if (opportunityReasonEl) opportunityReasonEl.textContent = opportunity.reason || "-";
  if (opportunityNextEl) {
    const nextStep = opportunity.next_step || "-";
    const timing = opportunity.timing ? `｜${opportunity.timing}` : "";
    opportunityNextEl.textContent = `${nextStep}${timing}`;
  }

  if (coachWhyEl) coachWhyEl.textContent = socialCoach.why_this_reply || "-";
  if (coachSendNoteEl) coachSendNoteEl.textContent = socialCoach.send_note || "-";
  renderList(coachPointsEl, socialCoach.learning_points || []);

  if (offlineReadinessEl) offlineReadinessEl.textContent = offlineAssist.readiness || "-";
  renderList(offlineTopicsEl, offlineAssist.topics || offlineAssist.preparation || []);
  renderList(offlineRescueEl, offlineAssist.cold_rescue || []);

  if (confidenceStreakEl) {
    const streak = confidence.current_streak !== undefined ? confidence.current_streak : 0;
    const totalWins = confidence.total_wins !== undefined ? confidence.total_wins : 0;
    confidenceStreakEl.textContent = `连续 ${streak} 轮｜累计 ${totalWins} 个亮点`;
  }
  if (confidenceEncouragementEl) confidenceEncouragementEl.textContent = confidence.encouragement || "";
  renderList(confidenceWinsEl, confidence.wins || recentWinDetails(confidence));
}

function renderList(target, items) {
  if (!target) return;
  target.replaceChildren();
  const normalized = Array.isArray(items) ? items.filter(Boolean).slice(0, 4) : [];
  if (!normalized.length) {
    const li = document.createElement("li");
    li.textContent = "暂无";
    target.appendChild(li);
    return;
  }
  for (const item of normalized) {
    const li = document.createElement("li");
    li.textContent = typeof item === "string" ? item : item.detail || item.skill || String(item);
    target.appendChild(li);
  }
}

function recentWinDetails(confidence) {
  const wins = confidence.recent_wins || [];
  if (!Array.isArray(wins)) return [];
  return wins.map((win) => win.detail || win.skill).filter(Boolean);
}

// ============================================================
// 3. 聊天气泡与多会话交互流控制
// ============================================================

function appendBubble(role, text, extraClass = "") {
  if (!messages) return null;
  const bubble = document.createElement("div");
  bubble.className = `bubble ${role} ${extraClass}`.trim();
  const span = document.createElement("span");
  span.textContent = text;
  bubble.appendChild(span);
  messages.appendChild(bubble);
  messages.scrollTop = messages.scrollHeight;
  return bubble;
}

function appendAssistantReply(data) {
  const reply = data.reply || "我在，你慢慢说";
  const bubble = appendBubble("assistant", reply);
  if (!bubble) return;

  const actions = document.createElement("div");
  actions.className = "reply-actions";

  const editInput = document.createElement("textarea");
  editInput.className = "reply-edit";
  editInput.rows = 2;
  editInput.value = reply;
  editInput.setAttribute("aria-label", "实际发送文本");
  editInput.title = "可以先改成你的口吻，再复制发送";

  const buttonRow = document.createElement("div");
  buttonRow.className = "reply-button-row";

  const copyButton = document.createElement("button");
  copyButton.type = "button";
  copyButton.className = "small-action-button";
  copyButton.textContent = "复制回复";
  copyButton.addEventListener("click", async () => {
    const editedReply = editInput.value.trim() || reply;
    await copyText(editedReply);
    copyButton.textContent = "已复制";
    setTimeout(() => {
      copyButton.textContent = "复制回复";
    }, 1200);
    await sendFeedback({
      action: "copy",
      selectedReply: reply,
      editedReply,
      turnId: data.turn_id,
      selectedIndex: data.ranked?.candidate ? candidateIndex(data.candidates || [], data.ranked.candidate.text) : null,
    });
  });

  const sentButton = document.createElement("button");
  sentButton.type = "button";
  sentButton.className = "small-action-button";
  sentButton.textContent = "记录已发";
  sentButton.addEventListener("click", async () => {
    const editedReply = editInput.value.trim() || reply;
    await sendFeedback({
      action: "sent",
      selectedReply: reply,
      editedReply,
      turnId: data.turn_id,
      selectedIndex: data.ranked?.candidate ? candidateIndex(data.candidates || [], data.ranked.candidate.text) : null,
    });
    markFeedback(sentButton, "已记录");
  });

  const goodButton = document.createElement("button");
  goodButton.type = "button";
  goodButton.className = "small-action-button positive";
  goodButton.textContent = "好";
  goodButton.addEventListener("click", async () => {
    await sendFeedback({
      action: "rating",
      rating: "good",
      selectedReply: reply,
      editedReply: editInput.value.trim(),
      turnId: data.turn_id,
    });
    markFeedback(goodButton, "已记好");
  });

  const badButton = document.createElement("button");
  badButton.type = "button";
  badButton.className = "small-action-button negative";
  badButton.textContent = "不好";
  badButton.addEventListener("click", async () => {
    await sendFeedback({
      action: "rating",
      rating: "bad",
      selectedReply: reply,
      editedReply: editInput.value.trim(),
      turnId: data.turn_id,
    });
    markFeedback(badButton, "已记不好");
  });

  buttonRow.append(copyButton, sentButton, goodButton, badButton);
  actions.append(editInput, buttonRow);
  bubble.appendChild(actions);
  messages.scrollTop = messages.scrollHeight;
}

async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const temp = document.createElement("textarea");
  temp.value = text;
  temp.style.position = "fixed";
  temp.style.left = "-9999px";
  document.body.appendChild(temp);
  temp.focus();
  temp.select();
  document.execCommand("copy");
  temp.remove();
}

function markFeedback(button, text) {
  const oldText = button.textContent;
  button.textContent = text;
  button.disabled = true;
  setTimeout(() => {
    button.textContent = oldText;
    button.disabled = false;
  }, 1200);
}

function candidateIndex(candidates, text) {
  const index = candidates.findIndex((candidate) => (candidate.text || "") === text);
  return index >= 0 ? index : null;
}

async function sendFeedback({ action, rating = "", selectedReply = "", editedReply = "", turnId = "", selectedIndex = null }) {
  const currentGirlId = sessionSelect ? sessionSelect.value : "default_girl";
  try {
    await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: currentGirlId,
        turn_id: turnId || lastResponseData?.turn_id || "",
        action,
        rating,
        selected_reply: selectedReply,
        selected_index: selectedIndex,
        edited_reply: editedReply,
      }),
    });
  } catch (error) {
    console.warn("反馈日志记录失败:", error);
  }
}

function setBusy(isBusy) {
  if (sendButton) {
    sendButton.disabled = isBusy;
    sendButton.textContent = isBusy ? "生成中" : "发送";
  }
  if (resetButton) resetButton.disabled = isBusy;
  if (input) input.disabled = isBusy;
}

/**
 * 发送消息（动态绑定当前选中的会话 user_id）
 */
async function sendMessage(text) {
  // 💡 核心改动：获取当前在跟哪个女生聊天（把选择的值作为 user_id 发给后端）
  const currentGirlId = sessionSelect ? sessionSelect.value : "default_girl";

  appendBubble("user", text);
  const loading = appendBubble("assistant", "正在想怎么回...", "loading");
  setBusy(true);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        user_id: currentGirlId, // 💡 对应后端 EmotionChatAgent 接收的 user_id
      }),
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || data.error || "请求失败");

    if (loading) loading.remove();
    lastResponseData = data;
    appendAssistantReply(data);

    // 渲染属于该女生的最新画像和侧边栏状态
    renderState(data);
  } catch (error) {
    if (loading) loading.remove();
    appendBubble("assistant", `出错了：${error.message}`);
    console.error("API 报错:", error);
  } finally {
    setBusy(false);
    if (input) input.focus();
  }
}

// ============================================================
// 4. 会话管理监听（动态切换与新建命名）
// ============================================================

// 💡 监听切换：当你从下拉框选“小林”换到“薇薇”时，自动清空屏幕并向后端拉取新人的画像
if (sessionSelect) {
  sessionSelect.addEventListener("change", async () => {
    const targetGirlId = sessionSelect.value;
    const targetGirlName = sessionSelect.options[sessionSelect.selectedIndex].text;

    if (messages) messages.replaceChildren();
    if (candidatesEl) candidatesEl.replaceChildren();
    lastResponseData = null;

    appendBubble("assistant", `成功切入与【${targetGirlName}】的独立对话战局。`);

    try {
      // 💡 向后端新开一个获取单人静态状态的接口，用来初始化侧边栏
      const response = await fetch(`/api/session_status?user_id=${targetGirlId}`);
      if (response.ok) {
        const data = await response.json();
        renderState(data);
      }
    } catch (err) {
      console.warn("拉取新会话静态状态失败，将在发送第一条消息时自动初始化面板");
    }
  });
}

// 💡 监听新建：点击“新建战局”，弹窗让你给聊天命名，并直接插入下拉框
if (addSessionBtn && sessionSelect) {
  addSessionBtn.addEventListener("click", () => {
    const girlName = prompt("请给这段聊天命名（输入女生的名字或备注）：");
    if (!girlName || !girlName.trim()) return;

    const pinyinId = "girl_" + Date.now(); // 用时间戳生成唯一的本地 session_id
    const newOption = document.createElement("option");
    newOption.value = pinyinId;
    newOption.textContent = girlName.trim();

    sessionSelect.appendChild(newOption);
    sessionSelect.value = pinyinId; // 自动切换到新创建的人

    // 触发切换逻辑
    sessionSelect.dispatchEvent(new Event("change"));
  });
}

// ============================================================
// 5. 原有全局事件监听绑定（保持不动）
// ============================================================
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

if (input) {
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
  });

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (form) form.requestSubmit();
    }
  });
}

if (resetButton) {
  resetButton.addEventListener("click", async () => {
    const currentGirlId = sessionSelect ? sessionSelect.value : "default_girl";
    try {
      setBusy(true);
      // 重置接口也要带上当前是谁，只清空她一个人的历史记录
      await fetch("/api/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: currentGirlId }),
      });
      lastResponseData = null;
      if (messages) messages.replaceChildren();
      appendBubble("assistant", "当前战局历史已清空，长期记忆还保留着。");
      if (candidatesEl) candidatesEl.replaceChildren();
    } catch (err) {
      console.error("重置会话失败:", err);
    } finally {
      setBusy(false);
    }
  });
}
