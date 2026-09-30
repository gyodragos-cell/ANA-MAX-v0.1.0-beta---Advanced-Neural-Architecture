/* ══════════════════════════════════════════════
   AnaBook – app.js
══════════════════════════════════════════════ */

// ── State ────────────────────────────────────────────────────────────────────
const ME = { name: "Billy", seed: "billy" };

const USERS = [
  { id: 1,  name: "Ana Popescu",    seed: "ana",   online: true  },
  { id: 2,  name: "Ion Ionescu",    seed: "ion",   online: true  },
  { id: 3,  name: "Maria Constantin",seed:"maria", online: false },
  { id: 4,  name: "Alex Dumitrescu",seed: "alex",  online: true  },
  { id: 5,  name: "Elena Marin",    seed: "elena", online: false },
  { id: 6,  name: "Radu Gheorghe",  seed: "radu",  online: true  },
  { id: 7,  name: "Ioana Stan",     seed: "ioana", online: false },
  { id: 8,  name: "Mihai Popa",     seed: "mihai", online: true  },
];

const IMAGES = [
  "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&q=80",
  "https://images.unsplash.com/photo-1518837695005-2083093ee35b?w=800&q=80",
  "https://images.unsplash.com/photo-1519802772250-a52a9af0eacb?w=800&q=80",
  "https://images.unsplash.com/photo-1531366936337-7c912a4589a7?w=800&q=80",
  "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?w=800&q=80",
  "https://images.unsplash.com/photo-1489549132488-d00b7eee80f1?w=800&q=80",
];

let posts = [
  {
    id: 1, authorId: 1, text: "Bună dimineața tuturor! ☀️ O zi frumoasă de vară.",
    time: "acum 5 minute", likes: 12, liked: false, image: IMAGES[0],
    reactions: ["❤️","👍","😮"],
    comments: [
      { authorId: 2, text: "La fel! 🌞", time: "acum 3 min" },
      { authorId: 3, text: "Zi bună și ție! 😊", time: "acum 2 min" },
    ]
  },
  {
    id: 2, authorId: 4, text: "Am descoperit un nou loc de drumeție. Absolut magnific! 🏔️ Cine vrea să vină săptămâna viitoare?",
    time: "acum 23 minute", likes: 47, liked: false, image: IMAGES[3],
    reactions: ["❤️","👍","🔥"],
    comments: [
      { authorId: 5, text: "Eu vreau! Unde exact?", time: "acum 15 min" },
    ]
  },
  {
    id: 3, authorId: 2,
    text: "Coding la 2 noaptea... ☕ #developer #viata",
    time: "acum 1 oră", likes: 8, liked: false, image: null,
    reactions: ["😂","👍"],
    comments: []
  },
  {
    id: 4, authorId: 6, text: "Week-end reușit! 🎉 Mulțumesc tuturor celor care au participat la petrecere!",
    time: "acum 3 ore", likes: 93, liked: false, image: IMAGES[5],
    reactions: ["❤️","🎉","👍","😮"],
    comments: [
      { authorId: 1, text: "A fost super! 🙌", time: "acum 2h" },
      { authorId: 7, text: "Multumim pentru invitatie! ❤️", time: "acum 2h" },
    ]
  },
  {
    id: 5, authorId: 3,
    text: "Soarele la mare 🌊 Nu există nimic mai relaxant.",
    time: "acum 5 ore", likes: 34, liked: false, image: IMAGES[1],
    reactions: ["❤️","😮"],
    comments: []
  },
];

// ── DOM refs ─────────────────────────────────────────────────────────────────
const feedEl       = document.getElementById("feed");
const postTextEl   = document.getElementById("postText");
const publishBtn   = document.getElementById("publishBtn");
const searchInput  = document.getElementById("searchInput");
const themeToggle  = document.getElementById("themeToggle");
const friendList   = document.getElementById("friendList");
const suggestedEl  = document.getElementById("suggested");
const toastEl      = document.createElement("div");
toastEl.id = "toast"; document.body.appendChild(toastEl);

// ── Helpers ──────────────────────────────────────────────────────────────────
function avatar(seed, size = 44) {
  return `https://api.dicebear.com/8.x/avataaars/svg?seed=${seed}`;
}
function user(id) { return USERS.find(u => u.id === id) || { name: ME.name, seed: ME.seed }; }

function toast(msg) {
  toastEl.textContent = msg;
  toastEl.classList.add("show");
  setTimeout(() => toastEl.classList.remove("show"), 2400);
}

// ── Theme ────────────────────────────────────────────────────────────────────
let isDark = true;
themeToggle.addEventListener("click", () => {
  isDark = !isDark;
  document.body.classList.toggle("dark", isDark);
  document.body.classList.toggle("light", !isDark);
  themeToggle.textContent = isDark ? "🌙" : "☀️";
});

// ── Auto-resize textarea ──────────────────────────────────────────────────────
postTextEl.addEventListener("input", () => {
  postTextEl.style.height = "auto";
  postTextEl.style.height = postTextEl.scrollHeight + "px";
});

// ── Publish post ─────────────────────────────────────────────────────────────
publishBtn.addEventListener("click", () => {
  const text = postTextEl.value.trim();
  if (!text) { postTextEl.focus(); return; }

  posts.unshift({
    id: Date.now(),
    authorId: 0, // 0 = ME
    text,
    time: "acum 1 secundă",
    likes: 0, liked: false, image: null,
    reactions: [], comments: []
  });

  postTextEl.value = "";
  postTextEl.style.height = "auto";
  render();
  toast("✅ Postare publicată!");
});

// ── Render feed ──────────────────────────────────────────────────────────────
function render() {
  const q = searchInput.value.trim().toLowerCase();
  const filtered = q
    ? posts.filter(p => {
        const u = user(p.authorId);
        return p.text.toLowerCase().includes(q) || u.name.toLowerCase().includes(q);
      })
    : posts;

  if (!filtered.length) {
    feedEl.innerHTML = `<div class="no-results">🔍 Nicio postare găsită pentru "<strong>${q}</strong>"</div>`;
    return;
  }

  feedEl.innerHTML = filtered.map(postHTML).join("");
}

function postHTML(p) {
  const u   = user(p.authorId);
  const name = p.authorId === 0 ? ME.name : u.name;
  const seed = p.authorId === 0 ? ME.seed : u.seed;
  const likeClass = p.liked ? "liked" : "";
  const reactStr  = p.reactions.length
    ? `<div class="reaction-emojis">${p.reactions.slice(0,3).map(e => `<span>${e}</span>`).join("")}</div><span>${p.likes} aprecieri</span>`
    : `<span>${p.likes} aprecieri</span>`;

  const imgEl = p.image
    ? `<img class="post-img" src="${p.image}" alt="postare" loading="lazy" />`
    : "";

  const commentsHTML = p.comments.map(c => {
    const cu = user(c.authorId);
    return `
      <div class="comment">
        <div class="comment-av"><img src="${avatar(cu.seed)}" alt="${cu.name}" /></div>
        <div class="comment-bubble">
          <strong>${cu.name}</strong>${c.text}
        </div>
      </div>`;
  }).join("");

  return `
    <div class="post card" data-id="${p.id}">
      <div class="post-header">
        <div class="post-avatar"><img src="${avatar(seed)}" alt="${name}" /></div>
        <div class="post-meta">
          <div class="post-author">${name}</div>
          <div class="post-time">🌐 ${p.time}</div>
        </div>
        <button class="post-menu" title="Optiuni">···</button>
      </div>

      <div class="post-body${p.text.length < 80 && !p.image ? ' large-text' : ''}">${escHtml(p.text)}</div>
      ${imgEl}

      <div class="post-reactions">
        ${reactStr}
        <span>${p.comments.length} comentarii</span>
      </div>

      <div class="post-actions">
        <button class="post-act-btn ${likeClass}" data-action="like" data-id="${p.id}">
          ${p.liked ? "❤️" : "👍"} Apreciez
        </button>
        <button class="post-act-btn" data-action="comment" data-id="${p.id}">
          💬 Comentez
        </button>
        <button class="post-act-btn" data-action="share" data-id="${p.id}">
          🔁 Distribuie
        </button>
      </div>

      <div class="post-comments" id="comments-${p.id}">
        ${commentsHTML}
        <div class="comment-form" id="cform-${p.id}" style="display:none">
          <div class="avatar-sm" style="width:32px;height:32px">
            <img src="${avatar(ME.seed)}" alt="eu" />
          </div>
          <input class="comment-input" placeholder="Scrie un comentariu..." data-postid="${p.id}" />
          <button class="comment-send" data-postid="${p.id}">➤</button>
        </div>
      </div>
    </div>`;
}

function escHtml(t) {
  return t.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;")
          .replace(/"/g,"&quot;").replace(/\n/g,"<br>");
}

// ── Feed events (delegation) ──────────────────────────────────────────────────
feedEl.addEventListener("click", e => {
  // Like
  const likeBtn = e.target.closest("[data-action='like']");
  if (likeBtn) {
    const id = Number(likeBtn.dataset.id);
    const p  = posts.find(x => x.id === id);
    if (!p) return;
    p.liked  = !p.liked;
    p.likes += p.liked ? 1 : -1;
    if (p.liked && !p.reactions.includes("❤️")) p.reactions.unshift("❤️");
    render();
    return;
  }

  // Comment toggle
  const commentBtn = e.target.closest("[data-action='comment']");
  if (commentBtn) {
    const id   = commentBtn.dataset.id;
    const form = document.getElementById(`cform-${id}`);
    if (form) {
      const hidden = form.style.display === "none";
      form.style.display = hidden ? "flex" : "none";
      if (hidden) form.querySelector(".comment-input")?.focus();
    }
    return;
  }

  // Share
  const shareBtn = e.target.closest("[data-action='share']");
  if (shareBtn) { toast("🔁 Postare distribuită!"); return; }

  // Comment send button
  const sendBtn = e.target.closest(".comment-send");
  if (sendBtn) { submitComment(sendBtn.dataset.postid); return; }
});

feedEl.addEventListener("keydown", e => {
  if (e.key === "Enter" && e.target.classList.contains("comment-input")) {
    submitComment(e.target.dataset.postid);
  }
});

function submitComment(postId) {
  const form  = document.getElementById(`cform-${postId}`);
  const input = form?.querySelector(".comment-input");
  if (!input) return;
  const text  = input.value.trim();
  if (!text)  return;

  const p = posts.find(x => x.id === Number(postId));
  if (!p) return;

  p.comments.push({ authorId: 0, text, time: "acum" });
  input.value = "";
  render();

  // Re-show form
  const newForm = document.getElementById(`cform-${postId}`);
  if (newForm) {
    newForm.style.display = "flex";
    newForm.querySelector(".comment-input")?.focus();
  }
}

// ── Story click ──────────────────────────────────────────────────────────────
document.querySelectorAll(".story:not(.add-story)").forEach((el, i) => {
  el.addEventListener("click", () => {
    const name = el.querySelector("span").textContent;
    const seed = USERS[i]?.seed || "user";
    document.getElementById("storyContent").innerHTML = `
      <div style="text-align:center">
        <img src="${avatar(seed)}" style="width:80px;height:80px;border-radius:50%;margin:0 auto 12px;display:block" />
        <h2 style="margin-bottom:8px">${name}</h2>
        <p style="color:var(--text-sub)">Story acum 2h</p>
        <img src="${IMAGES[i % IMAGES.length]}" style="margin:16px auto 0;border-radius:12px;max-height:300px;object-fit:cover;width:100%" />
      </div>`;
    document.getElementById("storyModal").classList.remove("hidden");
  });
});

// ── Right sidebar: friends ────────────────────────────────────────────────────
function renderFriends() {
  friendList.innerHTML = USERS.slice(0, 6).map(u => `
    <div class="friend-item">
      <div class="friend-av">
        <img src="${avatar(u.seed)}" alt="${u.name}" />
        ${u.online ? '<div class="online-dot"></div>' : ""}
      </div>
      <span class="friend-name">${u.name}</span>
    </div>`).join("");
}

function renderSuggested() {
  suggestedEl.innerHTML = USERS.slice(2, 5).map(u => `
    <div class="suggested-item">
      <div class="sug-av"><img src="${avatar(u.seed)}" alt="${u.name}" /></div>
      <div class="sug-info">
        <div class="sug-name">${u.name}</div>
        <div class="sug-mutual">👥 ${Math.floor(Math.random()*8)+1} prieteni comuni</div>
      </div>
      <button class="add-btn" onclick="toast('✅ Cerere trimisă!')">+ Adaugă</button>
    </div>`).join("");
}

// ── Search ────────────────────────────────────────────────────────────────────
searchInput.addEventListener("input", render);

// ── Story modal close ─────────────────────────────────────────────────────────
function closeStory() {
  document.getElementById("storyModal").classList.add("hidden");
}

// ── Nav buttons highlight ─────────────────────────────────────────────────────
document.querySelectorAll(".nav-btn").forEach(btn => {
  btn.addEventListener("click", function() {
    document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
    this.classList.add("active");
  });
});

// ── Add media (stub) ─────────────────────────────────────────────────────────
function addMedia(type) {
  if (type === "📷") {
    toast("📷 Funcție foto/video disponibilă în curând!");
  } else if (type === "😊") {
    const emojis = ["😊","🎉","❤️","😂","😢","😡","🙏","✈️","🎂","🌟"];
    const pick = emojis[Math.floor(Math.random() * emojis.length)];
    postTextEl.value += ` ${pick}`;
    postTextEl.focus();
  } else if (type === "📍") {
    postTextEl.value += " 📍 București, România";
    postTextEl.focus();
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────
render();
renderFriends();
renderSuggested();
