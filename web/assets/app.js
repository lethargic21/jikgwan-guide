(function () {
  "use strict";

  // 포스트시즌 진출팀이 확정되면 채운다. teams가 비어 있으면 배너를 숨긴다.
  // 예: { title: "2026 가을야구 진출팀 구장", note: "일정·예매는 KBO·구단 공식 발표를 확인하세요.", teams: ["LG", "한화"] }
  var POSTSEASON = { title: "", note: "", teams: [] };

  var DATA = window.GUIDE_DATA;
  if (!DATA) { renderLoadError(); return; }
  var stadiums = DATA.stadiums.slice();
  var byId = {};
  stadiums.forEach(function (s) { byId[s.id] = s; });
  var current = null;

  // ---------- 데이터를 못 불러왔을 때 ----------
  function renderLoadError() {
    var panel = document.getElementById("stadium-panel");
    if (!panel) { return; }
    var retry = document.createElement("button");
    retry.type = "button";
    retry.className = "btn-primary";
    retry.textContent = "다시 시도";
    retry.addEventListener("click", function () { location.reload(); });
    var box = document.createElement("div");
    box.className = "state-card";
    box.setAttribute("role", "alert");
    box.innerHTML = '<p class="state-label">불러오기 실패</p><h2 class="state-title">구장 정보를 불러오지 못했어요</h2>' +
      '<p class="state-text">네트워크가 잠시 불안정했을 수 있어요. 잠시 뒤 다시 시도해 주세요.</p>';
    box.appendChild(retry);
    panel.appendChild(box);
    document.querySelectorAll(".picker, .data").forEach(function (n) { n.hidden = true; });
  }

  // ---------- 측정 (GoatCounter가 붙어 있을 때만) ----------
  function track(path, title) {
    try {
      if (window.goatcounter && typeof window.goatcounter.count === "function") {
        window.goatcounter.count({ path: path, title: title || path, event: true });
      }
    } catch (e) { /* 측정 실패는 무시 */ }
  }

  // ---------- 유틸 ----------
  function el(tag, attrs, children) {
    var n = document.createElement(tag);
    if (attrs) {
      Object.keys(attrs).forEach(function (k) {
        if (k === "text") { n.textContent = attrs[k]; }
        else if (k === "html") { n.innerHTML = attrs[k]; }
        else if (k === "className") { n.className = attrs[k]; }
        else { n.setAttribute(k, attrs[k]); }
      });
    }
    (children || []).forEach(function (c) { if (c) { n.appendChild(c); } });
    return n;
  }
  function fmtDist(m) { return m < 1000 ? m + "m" : (m / 1000).toFixed(1) + "km"; }
  function fmtInt(n) { return Number(n).toLocaleString("ko-KR"); }
  function fmtPct(p) { return (p > 0 ? "+" : "") + p.toFixed(1) + "%"; }
  function fmtMan(n) { // 10700 → "1만 700명"
    var man = Math.floor(n / 10000), rest = n % 10000;
    return (man ? man + "만" + (rest ? " " + fmtInt(rest) : "") : fmtInt(rest)) + "명";
  }
  function isPS(s) { return POSTSEASON.teams.some(function (t) { return s.teams.indexOf(t) >= 0; }); }
  function mapUrl(place) {
    var parts = (place.addr || "").split(/\s+/);
    var area = parts.length > 1 ? parts[1] : (place.sigungu || "");
    return "https://map.naver.com/p/search/" + encodeURIComponent((place.title + " " + area).trim());
  }

  // ---------- 상단 요약 ----------
  function renderSummary() {
    var sm = DATA.summary;
    document.getElementById("hero-pct").textContent = fmtPct(sm.pct);
    document.getElementById("hero-source").textContent =
      "한국관광 데이터랩 이동통신 방문자 데이터 × KBO 정규시즌 " + fmtInt(sm.game_days) +
      " 경기일 분석 (" + sm.period + ", 95% 신뢰구간 " + sm.lo.toFixed(1) + "~" + sm.hi.toFixed(1) + "%)";
    if (sm.share_of_crowd) {
      document.getElementById("fact-extra").textContent = "관중 수의 약 " + sm.share_of_crowd + "%";
    }
    if (sm.extra_per_game) { document.getElementById("hero-extra").textContent = fmtMan(sm.extra_per_game); }
    if (sm.stay_share != null) { document.getElementById("fact-stay").textContent = "약 " + sm.stay_share.toFixed(1) + "%"; }
    document.getElementById("gen-date").textContent = DATA.generated;
  }

  // ---------- 포스트시즌 배너 ----------
  function renderPostseason() {
    if (!POSTSEASON.teams.length) { return; }
    var box = document.getElementById("postseason");
    document.getElementById("ps-title").textContent = POSTSEASON.title || "가을야구 진출팀 구장";
    document.getElementById("ps-note").textContent = POSTSEASON.note || "";
    var list = document.getElementById("ps-list");
    stadiums.filter(isPS).forEach(function (s) {
      var b = el("button", { type: "button", className: "chip", text: s.name });
      b.addEventListener("click", function () { select(s.id, "postseason"); scrollToPanel(); });
      list.appendChild(b);
    });
    box.hidden = false;
    stadiums.sort(function (a, b) { return (isPS(b) ? 1 : 0) - (isPS(a) ? 1 : 0); });
  }

  // ---------- 구장 탭 ----------
  function renderChips() {
    var wrap = document.getElementById("chips");
    wrap.innerHTML = "";
    stadiums.forEach(function (s) {
      var short = s.key;
      var b = el("button", {
        type: "button", role: "tab", className: "chip", id: "tab-" + s.id,
        "aria-controls": "stadium-panel", "aria-selected": "false", "data-id": s.id
      });
      b.appendChild(document.createTextNode(short));
      b.appendChild(el("small", { text: s.teams.join("·") }));
      if (isPS(s)) { b.appendChild(el("span", { className: "ps-badge", text: "가을야구" })); }
      b.addEventListener("click", function () { select(s.id, "tab"); });
      wrap.appendChild(b);
    });
    wrap.addEventListener("keydown", function (e) {
      if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") { return; }
      var ids = stadiums.map(function (s) { return s.id; });
      var i = ids.indexOf(current) + (e.key === "ArrowRight" ? 1 : -1);
      i = (i + ids.length) % ids.length;
      select(ids[i], "key");
      document.getElementById("tab-" + ids[i]).focus();
      e.preventDefault();
    });
  }

  // ---------- 장소 목록 ----------
  function placeItem(s, p, section) {
    var a = el("a", {
      className: "map-link", href: mapUrl(p), target: "_blank", rel: "noopener",
      "aria-label": p.title + " 네이버 지도에서 보기", text: "지도"
    });
    a.addEventListener("click", function () { track("map/" + s.id + "/" + section, "지도: " + s.key + " · " + p.title); });
    return el("li", { className: "place" }, [
      el("div", { className: "place-body" }, [
        el("p", { className: "place-title", text: p.title }),
        el("p", { className: "place-meta", text: p.dist != null ? p.cat + " · 구장에서 " + fmtDist(p.dist) : p.cat }),
        p.addr ? el("p", { className: "place-addr", text: p.addr }) : null
      ]),
      a
    ]);
  }
  function placeList(s, items, section) {
    if (!items.length) { return el("p", { className: "empty", text: "TourAPI에 등록된 가까운 장소가 없습니다." }); }
    return el("ol", { className: "places" }, items.map(function (p) { return placeItem(s, p, section); }));
  }
  function course(step, title, hint, body) {
    return el("section", { className: "course" }, [
      el("h3", {}, [el("span", { className: "step", text: step }), document.createTextNode(title)]),
      hint ? el("p", { className: "hint", text: hint }) : null
    ].concat(body));
  }

  // ---------- 구장 패널 ----------
  function renderPanel(s) {
    var panel = document.getElementById("stadium-panel");
    panel.setAttribute("aria-labelledby", "tab-" + s.id);
    panel.innerHTML = "";
    var e = s.effect;

    panel.appendChild(el("div", { className: "stadium-head" }, [
      el("h2", { text: s.name }),
      el("p", { className: "meta", text: s.teams.join("·") + " 홈 · " + s.sido + " " + s.sigungu }),
      el("div", { className: "scoreboard" }, [
        el("p", { className: "sb-caption", text: "HOME GAME DAY" }),
        el("p", { className: "sb-num", text: fmtPct(e.pct) }),
        el("p", { className: "sb-label", text: "홈경기날 " + s.sigungu + " 외지인 방문" })
      ]),
      el("p", { className: "stat-sub", text: "경기 1회당 약 " + fmtInt(e.extra_per_game) + "명이 더 찾아옵니다 (관중 수의 약 " + e.share_of_crowd + "%)" }),
      el("p", { className: "stat-ci", text: "95% 신뢰구간 " + e.lo.toFixed(1) + "~" + e.hi.toFixed(1) + "% · 2023.1~2026.8 홈경기 " + fmtInt(e.game_days) + "일" })
    ]));

    var courses = el("div", { className: "courses" });
    panel.appendChild(courses);

    var preBody = [];
    if (s.pre_datalab && s.pre_datalab.length) {
      var related = s.pre_datalab[0].source === "related";
      preBody.push(el("p", { className: "group-label", text: related
        ? "구장 방문자가 함께 찾은 곳 · 한국관광 데이터랩 연관관광지 순위"
        : s.sigungu + " 인기 관광지 · 한국관광 데이터랩 중심관광지 순위" }));
      preBody.push(el("ol", { className: "places" }, s.pre_datalab.map(function (p) {
        return placeItem(s, { title: p.title, cat: p.cat + " · " + p.rank + "위", addr: "", sigungu: p.sigungu }, "pre_datalab");
      })));
    }
    preBody.push(el("p", { className: "group-label", text: "구장 근처 · 한국관광공사 TourAPI 관광지·문화시설, 가까운 순" }));
    preBody.push(placeList(s, s.pre, "pre"));
    var rankHint = s.datalab_rank ? "데이터랩 기준 이 구장은 " + s.sigungu + " 인기 관광지 " + s.datalab_rank + "위 (2025.9~2026.8)" : "";
    courses.appendChild(course("플레이볼 전", "한 바퀴 둘러보기", rankHint, preBody));

    courses.appendChild(course("경기 종료 후", "늦은 한 끼", "야간경기는 밤늦게 끝납니다. 영업 여부는 출발 전 지도에서 확인하세요 · TourAPI 음식점, 가까운 순",
      [placeList(s, s.post, "post")]));

    var near = s.stay.filter(function (p) { return p.dist <= 3000; });
    var far = s.stay.filter(function (p) { return p.dist > 3000; });
    var stayBody = [];
    if (s.stay_datalab && s.stay_datalab.length) {
      var rel = s.stay_datalab[0].source === "related";
      stayBody.push(el("p", { className: "group-label", text: rel
        ? "구장 방문자가 함께 찾은 숙소 · 한국관광 데이터랩 연관관광지"
        : s.sigungu + " 인기 숙소 · 한국관광 데이터랩 중심관광지 순위" }));
      stayBody.push(el("ol", { className: "places" }, s.stay_datalab.map(function (p) {
        return placeItem(s, { title: p.title, cat: "숙박 · " + p.rank + "위", addr: "", sigungu: p.sigungu }, "stay_datalab");
      })));
    }
    if (near.length) { stayBody.push(el("p", { className: "group-label", text: "구장 3km 안 · TourAPI 숙박" })); stayBody.push(placeList(s, near, "stay")); }
    if (far.length) { stayBody.push(el("p", { className: "group-label", text: "조금 떨어진 곳 (3km 넘게) · TourAPI 숙박" })); stayBody.push(placeList(s, far, "stay")); }
    if (!stayBody.length) { stayBody.push(placeList(s, [], "stay")); }
    courses.appendChild(course("연장전: 하룻밤", "숙소 권역", "경기날 온 외지인은 대부분 그날 떠납니다. 하룻밤 머물면 다음 날 코스가 열립니다.", stayBody));
  }

  // ---------- 데이터 막대 ----------
  function renderBars() {
    var list = document.getElementById("bars");
    var rows = DATA.stadiums.slice().sort(function (a, b) { return b.effect.pct - a.effect.pct; });
    var max = Math.ceil(Math.max.apply(null, rows.map(function (s) { return s.effect.hi; })) + 1);
    list.innerHTML = "";
    rows.forEach(function (s) {
      var e = s.effect;
      var track_ = el("span", { className: "bar-track", "aria-hidden": "true" }, [
        el("span", { className: "bar-fill", style: "width:" + (100 * e.pct / max) + "%" }),
        el("span", { className: "bar-ci", style: "left:" + (100 * e.lo / max) + "%;width:" + (100 * (e.hi - e.lo) / max) + "%" })
      ]);
      var btn = el("button", { type: "button", className: "bar-btn", "aria-label": s.name + " 홈경기일 외지인 방문 " + fmtPct(e.pct) + ", 코스 보기" }, [
        el("span", { className: "bar-name", text: s.key }), track_, el("span", { className: "bar-val", text: fmtPct(e.pct) })
      ]);
      var li = el("li", { className: "bar-row", "data-id": s.id }, [btn]);
      btn.addEventListener("click", function () { select(s.id, "bar"); scrollToPanel(); });
      list.appendChild(li);
    });
  }

  // ---------- 구장별 진단표 ----------
  function renderDiagnosis() {
    var body = document.getElementById("diag-body");
    if (!body || !DATA.diagnosis) { return; }
    body.innerHTML = "";
    DATA.diagnosis.forEach(function (d) {
      var m = /^(.*?)\s*\((.*)\)$/.exec(d.quadrant) || [null, d.quadrant, ""];
      var qcls = d.quadrant.indexOf("체류↑") >= 0 ? "q-up" : (d.quadrant.indexOf("유입↑") >= 0 ? "q-priority" : "q-base");
      var name = el("button", { type: "button", className: "diag-name", "aria-label": d.stadium + " 가이드 보기" }, [
        document.createTextNode(d.stadium), el("small", { text: d.sigungu })
      ]);
      name.addEventListener("click", function () { select(d.id, "diagnosis"); scrollToPanel(); });
      function cell(label, main, sub, cls) {
        return el("td", { "data-label": label, className: cls || "" }, [
          el("span", { className: "diag-main", text: main }), sub ? el("small", { text: sub }) : null
        ]);
      }
      body.appendChild(el("tr", { "data-id": d.id }, [
        el("th", { scope: "row" }, [name]),
        cell("경기일 효과", fmtPct(d.gameday_pct), "95% CI " + d.gameday_lo.toFixed(1) + "~" + d.gameday_hi.toFixed(1)),
        cell("경기당 외지인", "약 " + fmtInt(d.extra_per_game) + "명"),
        cell("다음날 잔존", fmtPct(d.nextday_pct), d.nextday_sig ? "유의 (다음날까지 남음)" : "0과 차이 없음"),
        cell("타 시도 관중 비중", d.away_share, d.away_note, /%$/.test(d.away_share) ? "" : "is-na"),
        el("td", { "data-label": "유형" }, [el("span", { className: "qtype " + qcls, text: m[1] }), m[2] ? el("small", { text: m[2] }) : null]),
        el("td", { "data-label": "처방", className: "diag-rx", text: d.prescription })
      ]));
    });
  }

  // ---------- 선택 ----------
  function scrollToPanel() {
    var nav = document.querySelector(".picker");
    var y = document.getElementById("stadium-panel").getBoundingClientRect().top + window.scrollY - (nav ? nav.offsetHeight : 0) - 8;
    window.scrollTo({ top: y });
  }
  function select(id, source) {
    var s = byId[id];
    if (!s) { return; }
    current = id;
    document.querySelectorAll(".chip[role=tab]").forEach(function (c) {
      var on = c.getAttribute("data-id") === id;
      c.setAttribute("aria-selected", on ? "true" : "false");
      c.tabIndex = on ? 0 : -1;
      if (on) {
        var row = c.parentNode;
        row.scrollTo({ left: Math.max(0, c.offsetLeft - (row.clientWidth - c.offsetWidth) / 2) });
      }
    });
    document.querySelectorAll(".bar-row").forEach(function (r) {
      r.classList.toggle("is-current", r.getAttribute("data-id") === id);
    });
    renderPanel(s);
    if (history.replaceState) { history.replaceState(null, "", "#" + id); }
    if (source === "tab" || source === "key") { track("tab/" + id, "구장 탭: " + s.key); }
    else if (source !== "init") { track("jump/" + source + "/" + id, "이동(" + source + "): " + s.key); }
  }

  renderSummary();
  renderPostseason();
  renderChips();
  renderBars();
  renderDiagnosis();
  var fromHash = (location.hash || "").replace("#", "");
  select(byId[fromHash] ? fromHash : stadiums[0].id, "init");
  window.addEventListener("hashchange", function () {
    var id = (location.hash || "").replace("#", "");
    if (byId[id] && id !== current) { select(id, "hash"); }
  });
})();
