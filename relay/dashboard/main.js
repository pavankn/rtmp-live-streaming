// -------------------------
// GLOBAL STATE
// -------------------------
let streams_meta = [];        // Directus metadata (from FastAPI)
let backend_status = {};      // Runtime status (from WebSocket)

const playAllBtn = document.getElementById("playAllBtn");
const stopAllBtn = document.getElementById("stopAllBtn");
const container = document.getElementById("streams");

// -------------------------
// WEBSOCKET LIVE UPDATES
// -------------------------
const ws = new WebSocket(`ws://${location.host}/ws`);

ws.onmessage = (event) => {
  console.log("WebSocket message received: " + event.data);
  backend_status = JSON.parse(event.data);
  loadStreams();           // Re-render UI with new status
};

ws.onerror = (e) => console.error("WebSocket error:", e);
ws.onclose  = () => console.warn("WebSocket closed");

// -------------------------
// LOAD METADATA FROM FASTAPI
// -------------------------
async function loadStreams() {
  const res = await fetch("/api/streams", { method: "POST" });
  streams_meta = await res.json();
  renderStreams();           // Rearm UI
}


// -------------------------
// MERGE + RENDER STREAM CARDS
// -------------------------
function renderStreams() {
  container.innerHTML = "";

  streams_meta.forEach(stream => {
    const key = stream.stream_key;

    // ✅ merge runtime status from backend
    const status = backend_status[key]?.status || "stopped";
    stream.status = status;

    const card = createCard(stream);
    container.appendChild(card);
  });
}

function createCard(stream) {
  const card = document.createElement("div");
  card.className = "channel-card";

  const isOnline = stream.status === "playing" ? "online" : "offline";

  card.innerHTML = `
    <div class="avatar-wrapper">
      <img src="${stream.avatar}" class="avatar" />
      <span class="status-indicator ${isOnline}"></span>
    </div>

    <h3>${stream.language}</h3>

    <div class="controls">
      <div class="column">
        <img src="assets/music_on.png" class="icon music-on" data-id="${stream.id}">
        <img src="assets/play.png" class="icon play ${isOnline === 'online' ? 'disabled' : ''}" data-id="${stream.id}">
        <img src="assets/upload.png" class="icon upload">
      </div>

      <div class="column">
        <img src="assets/music_off.png" class="icon music-off" data-id="${stream.id}">
        <img src="assets/stop.png" class="icon stop ${isOnline === 'online' ? '' : 'disabled'}" data-id="${stream.id}">
        <img src="assets/upload.png" class="icon upload">
      </div>
    </div>
  `;

  // ✅ attach listeners *here*
  const playBtn = card.querySelector(".play");
  const stopBtn = card.querySelector(".stop");

  console.log("Setting initial button states for stream:", stream.stream_key);

  playBtn.addEventListener("click", async () => {
    const id = stream.stream_key;

    // Await for the result before disabling buttons
    const result = await startStream(id);

    if (result.ok) {
      // ✅ NOW disable Play, enable Stop
      playBtn.classList.add("disabled");
      stopBtn.classList.remove("disabled");
      updateStatusIndicator(card, true);
    } else {
      console.error("Failed to start:", result.error);
      // ✅ DO NOT disable anything
      alert("Stream failed to start: " + result.error);
    }
  });

  stopBtn.addEventListener("click", async () => {
    const id = stream.stream_key;

    // Await for the result before disabling buttons
    const result = await stopStream(id);

    if (result.ok) {
      // ✅ NOW disable Stop, enable Play
      stopBtn.classList.add("disabled");
      playBtn.classList.remove("disabled");
      updateStatusIndicator(card, false);
    } else {
      console.error("Failed to stop:", result.error);
      // ✅ DO NOT disable anything
      alert("Stream failed to stop: " + result.error);
  }});

  return card;
}

function updateStatusIndicator(card, isOnline) {
  const indicator = card.querySelector(".status-indicator");
  indicator.classList.remove("online", "offline");
  indicator.classList.add(isOnline ? "online" : "offline");
}


async function startStream(streamId) {
  console.log("Starting stream:", streamId);
  try {
    const res = await fetch(`/start/${streamId}`, {
      method: "POST"
    });

    const data = await res.json();
    console.log("Started:", data);
    return data;

  } catch (err) {
    console.error("Start error:", err);
  }
}

async function stopStream(streamId) {
  console.log("Stopping stream:", streamId);
  try {
    const res = await fetch(`/stop/${streamId}`, {
      method: "POST"
    });

    const data = await res.json();
    console.log("Started:", data);
    return data;

  } catch (err) {
    console.error("Stop error:", err);
  }
}

// ✅ Play All
playAllBtn.addEventListener("click", async () => {
  console.log("Play All clicked");
  playAllBtn.disabled = true;
  stopAllBtn.disabled = false;
  await fetch(`/start_all`, { method: "POST" });
});

// ✅ Stop All
stopAllBtn.addEventListener("click", async () => {
  console.log("Stop All clicked");
  playAllBtn.disabled = false;
  stopAllBtn.disabled = true;
  await fetch(`/stop_all`, { method: "POST" });
});