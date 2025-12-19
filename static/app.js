async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return { ok: res.ok, data: await res.json() };
}

async function getJSON(url) {
  const res = await fetch(url);
  return { ok: res.ok, data: await res.json() };
}

function renderList(el, items) {
  el.innerHTML = "";
  for (const p of items) {
    const li = document.createElement("li");
    li.textContent = `${p.name} — score: ${p.score} (games_won: ${p.games_won})`;
    el.appendChild(li);
  }
}

async function refreshLeaderboard() {
  const { ok, data } = await getJSON("/api/leaderboard");
  if (!ok) return;

  renderList(document.getElementById("lbName"), data.by_name);
  renderList(document.getElementById("lbScore"), data.by_score);
}

function setStatus(obj) {
  document.getElementById("status").textContent = JSON.stringify(obj, null, 2);
}

document.getElementById("startBtn").addEventListener("click", async () => {
  const p1 = document.getElementById("p1").value.trim();
  const p2 = document.getElementById("p2").value.trim();

  // Register players (safe even if they already exist)
  if (p1) await postJSON("/api/player/register", { name: p1 });
  if (p2) await postJSON("/api/player/register", { name: p2 });

  const r = await postJSON("/api/game/start", { player1: p1, player2: p2 });
  setStatus(r.data);
  await refreshLeaderboard();
});

document.getElementById("playBtn").addEventListener("click", async () => {
  const r = await postJSON("/api/game/play_round", {}); // server picks random choices by default
  setStatus(r.data);
  await refreshLeaderboard();

  // If player1 is locked, reflect that in UI (optional)
  if (r.data.locked_player1) {
    document.getElementById("p1").disabled = true;
    document.getElementById("p1Lock").textContent = "(locked: winner retention)";
    document.getElementById("p1").value = r.data.next_player1 || document.getElementById("p1").value;
  } else {
    document.getElementById("p1").disabled = false;
    document.getElementById("p1Lock").textContent = "";
  }
});

// initial load
refreshLeaderboard();
