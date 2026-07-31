(() => {
  "use strict";

  const screens = {};
  document.querySelectorAll("[data-screen]").forEach((el) => {
    screens[el.dataset.screen] = el;
  });

  const els = {
    questionTitle: document.querySelector("[data-question-title]"),
    questionCategory: document.querySelector("[data-question-category]"),
    questionInstruction: document.querySelector("[data-question-instruction]"),
    options: document.querySelector("[data-options]"),
    progressFill: document.querySelector(".screen--question [data-progress-fill]"),
    progressLabel: document.querySelector(".screen--question [data-progress-label]"),
    confetti: document.querySelector("[data-confetti]"),
  };

  const state = {
    questions: [],
    index: 0,
    // answers keyed by question id -> { id, value, response_time }
    answers: {},
    questionShownAt: 0,
  };

  const BADGE_LETTERS = ["A", "B", "C", "D", "E", "F", "G"];

  function show(name) {
    Object.values(screens).forEach((s) => s.classList.remove("is-active"));
    screens[name].classList.add("is-active");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function loadSurvey() {
    try {
      const res = await fetch("/api/survey");
      const data = await res.json();
      state.questions = data.questions || [];
    } catch (err) {
      console.log("[v0] Failed to load survey:", err.message);
    }
  }

  function questionHasImages(q) {
    return (q.options || []).some((o) => o.image);
  }

  function renderQuestion() {
    const q = state.questions[state.index];
    if (!q) return;

    // Category + optional instruction (section metadata from the XML).
    els.questionCategory.textContent = q.section || "";
    els.questionCategory.hidden = !q.section;
    if (q.instruction) {
      els.questionInstruction.textContent = q.instruction;
      els.questionInstruction.hidden = false;
    } else {
      els.questionInstruction.textContent = "";
      els.questionInstruction.hidden = true;
    }

    els.questionTitle.textContent = q.text;
    els.options.innerHTML = "";

    const existing = state.answers[q.id];

    if (q.type === "text") {
      renderTextInput(q, existing);
    } else if (questionHasImages(q)) {
      renderImageOptions(q, existing);
    } else {
      renderChoiceOptions(q, existing);
    }

    state.questionShownAt = performance.now();
    updateProgress();
  }

  // ---- Image-based options (original card layout) ----
  function renderImageOptions(q, existing) {
    els.options.classList.remove("options--plain");
    els.options.classList.add("options--media");

    q.options.forEach((opt, i) => {
      const badge = BADGE_LETTERS[i] || String(i + 1);
      const card = document.createElement("button");
      card.type = "button";
      card.className = "option";
      if (existing && existing.value === opt.value) {
        card.classList.add("is-selected");
      }
      const img = opt.image
        ? `<img src="/static/img/${opt.image}" alt="${opt.label}" onerror="this.style.display='none'" />`
        : "";
      card.innerHTML = `
        <div class="option__media">
          ${img}
          <span class="option__badge">${badge}</span>
        </div>
        <div class="option__label">${opt.label}</div>
      `;
      card.addEventListener("click", () => selectOption(q, opt));
      els.options.appendChild(card);
    });
  }

  // ---- Plain choice options (Likert / single-choice without images) ----
  function renderChoiceOptions(q, existing) {
    els.options.classList.remove("options--media");
    els.options.classList.add("options--plain");

    q.options.forEach((opt, i) => {
      const badge = BADGE_LETTERS[i] || String(i + 1);
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "option option--choice";
      if (existing && existing.value === opt.value) {
        btn.classList.add("is-selected");
      }
      btn.innerHTML = `
        <span class="option__badge option__badge--inline">${badge}</span>
        <span class="option__label option__label--inline">${opt.label}</span>
      `;
      btn.addEventListener("click", () => selectOption(q, opt));
      els.options.appendChild(btn);
    });
  }

  // ---- Free text input (e.g. Age, University name) ----
  function renderTextInput(q, existing) {
    els.options.classList.remove("options--media");
    els.options.classList.add("options--plain");

    const wrap = document.createElement("div");
    wrap.className = "text-answer";
    wrap.innerHTML = `
      <input type="text" class="text-answer__input" data-text-input
             placeholder="Type your answer here..." />
      <button type="button" class="pill-btn text-answer__next" data-text-next>
        <span class="pill-btn__arrow" aria-hidden="true"></span>
        <span>NEXT</span>
      </button>
    `;
    els.options.appendChild(wrap);

    const input = wrap.querySelector("[data-text-input]");
    const nextBtn = wrap.querySelector("[data-text-next]");
    if (existing && typeof existing.value === "string") {
      input.value = existing.value;
    }
    input.focus();

    const submit = () => {
      const value = input.value.trim();
      if (!value) {
        input.focus();
        return;
      }
      recordAnswer(q, value);
      next();
    };

    nextBtn.addEventListener("click", submit);
    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.isComposing && e.keyCode !== 229) {
        e.preventDefault();
        submit();
      }
    });
  }

  function updateProgress() {
    const total = state.questions.length;
    const pct = total ? Math.round((state.index / total) * 100) : 0;
    els.progressFill.style.width = pct + "%";
    els.progressLabel.textContent = pct + "%";
  }

  function recordAnswer(question, value) {
    const elapsed = (performance.now() - state.questionShownAt) / 1000;
    const prior = state.answers[question.id];
    state.answers[question.id] = {
      id: question.id,
      value: value,
      // Preserve the fastest genuine response time if the question is re-answered.
      response_time: prior ? Math.min(prior.response_time, elapsed) : elapsed,
    };
  }

  function selectOption(question, option) {
    recordAnswer(question, option.value);

    els.options.querySelectorAll(".option").forEach((c) => c.classList.remove("is-selected"));
    els.options.querySelectorAll(".option").forEach((c) => {
      const label = c.querySelector(".option__label");
      if (label && label.textContent === option.label) {
        c.classList.add("is-selected");
      }
    });

    // Advance shortly after a choice so the selection is visible.
    setTimeout(next, 380);
  }

  function next() {
    state.index += 1;
    if (state.index >= state.questions.length) {
      finish();
    } else {
      renderQuestion();
    }
  }

  async function finish() {
    show("outro");
    launchConfetti();
    try {
      await fetch("/api/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers: Object.values(state.answers) }),
      });
    } catch (err) {
      console.log("[v0] Failed to submit answers:", err.message);
    }
  }

  function restart() {
    state.index = 0;
    state.answers = {};
    renderQuestion();
    show("question");
  }

  // ---------- Confetti ----------
  let confettiRaf = null;
  function launchConfetti() {
    const canvas = els.confetti;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;

    const colors = ["#f4f43e", "#f81ce5", "#ff5ecf", "#ffffff", "#9a7ce8"];
    const pieces = Array.from({ length: 140 }, () => ({
      x: Math.random() * canvas.width,
      y: Math.random() * -canvas.height,
      r: 4 + Math.random() * 6,
      c: colors[(Math.random() * colors.length) | 0],
      vy: 1.5 + Math.random() * 3,
      vx: -1 + Math.random() * 2,
      rot: Math.random() * Math.PI,
      vr: -0.1 + Math.random() * 0.2,
    }));

    const start = performance.now();
    if (confettiRaf) cancelAnimationFrame(confettiRaf);

    function frame(now) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      pieces.forEach((p) => {
        p.y += p.vy;
        p.x += p.vx;
        p.rot += p.vr;
        if (p.y > canvas.height) p.y = -10;
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rot);
        ctx.fillStyle = p.c;
        ctx.fillRect(-p.r / 2, -p.r / 2, p.r, p.r * 1.6);
        ctx.restore();
      });
      if (now - start < 6000) {
        confettiRaf = requestAnimationFrame(frame);
      } else {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
      }
    }
    confettiRaf = requestAnimationFrame(frame);
  }

  // ---------- Wire up buttons ----------
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-action]");
    if (!btn) return;
    const action = btn.dataset.action;
    if (action === "start") show("intro");
    else if (action === "begin") {
      renderQuestion();
      show("question");
    } else if (action === "restart") restart();
  });

  loadSurvey();
})();
