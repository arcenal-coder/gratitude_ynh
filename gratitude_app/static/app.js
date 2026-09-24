"use strict";

const state = { me: null, entities: [], page: "home", dialog: null };
const app = document.querySelector("#app");

const api = async (path, options = {}) => {
  const response = await fetch(`api/v1${path}`, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "Une erreur est survenue.");
  return payload.data;
};

const escape = (value) => String(value ?? "").replace(/[&<>"]/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[char]);
const date = (value) => value ? new Intl.DateTimeFormat("fr-FR", { dateStyle: "medium" }).format(new Date(value)) : "";
const toast = (message, error = false) => { document.querySelector(".toast")?.remove(); document.body.insertAdjacentHTML("beforeend", `<div class="toast ${error ? "error" : ""}" role="status">${escape(message)}</div>`); setTimeout(() => document.querySelector(".toast")?.remove(), 4200); };

const messageCard = (message) => `<article class="message"><span class="tag ${message.status === "pending" ? "pending" : ""}">${message.status === "pending" ? "En attente" : "Merci"}</span><p>${escape(message.body)}</p><div class="meta">Pour ${escape(message.recipients)} · ${message.author ? `par ${escape(message.author)}` : "auteur anonyme"} · ${date(message.created_at)}</div></article>`;
const empty = (text) => `<div class="empty">${escape(text)}</div>`;

function shell(content) {
  const admin = state.me.role === "admin" || state.me.role === "moderator";
  const links = [["home", "⌂", "Accueil"], ["send", "✦", "Envoyer"], ["wall", "▤", "Mon mur"], ["community", "◎", "Mur commun"], ["challenges", "🏆", "Challenges"]];
  if (admin) links.push(["admin", "⚙", "Administration"]);
  app.innerHTML = `<div class="shell"><header class="topbar"><div class="brand"><span class="brand-mark">♥</span>Gratitude</div><div class="user">${escape(state.me.display_name)} · ${state.me.role === "admin" ? "administration" : "espace membre"}</div></header><div class="layout"><nav class="nav">${links.map(([id, icon, label]) => `<button class="${state.page === id ? "active" : ""}" data-page="${id}">${icon}<span>${label}</span></button>`).join("")}</nav><main class="main">${content}</main></div></div>`;
  document.querySelectorAll("[data-page]").forEach(button => button.addEventListener("click", () => navigate(button.dataset.page)));
}

async function navigate(page) {
  state.page = page;
  try {
    if (page === "home") return renderHome();
    if (page === "send") return renderSend();
    if (page === "wall") return renderWall();
    if (page === "community") return renderCommunity();
    if (page === "challenges") return renderChallenges();
    if (page === "admin") return renderAdmin();
  } catch (error) { toast(error.message, true); }
}

async function renderHome() {
  const data = await api("/dashboard");
  const visibleMessages = data.messages.length ? data.messages.map(messageCard).join("") : empty("Votre mur attend son premier merci.");
  shell(`<section class="hero"><div><p class="eyebrow">Votre espace de reconnaissance</p><h1>Bonjour ${escape(state.me.display_name)}.</h1><p>Un mot sincère peut illuminer une journée entière.</p></div><button class="button primary" data-send>Envoyer un merci</button></section><section class="grid"><article class="card stat"><strong>${data.messages.length}</strong><span>mercis dans votre espace</span></article><article class="card stat"><strong>${data.challenges.filter(item => item.status === "open").length}</strong><span>challenges ouverts</span></article>${state.me.role !== "member" ? `<article class="card stat"><strong>${data.pending_count}</strong><span>messages à modérer</span></article>` : ""}<article class="card wide"><h2>Vos derniers mercis</h2>${visibleMessages}<button class="button secondary" data-page="wall">Voir mon mur</button></article><article class="card side"><h2>À la une</h2>${data.challenges.length ? data.challenges.map(challenge => `<div class="challenge"><div><h3>${escape(challenge.title)}</h3><div class="meta">${escape(challenge.theme)} · jusqu'au ${date(challenge.closes_at)}</div></div><button class="button secondary" data-page="challenges">Voir</button></div>`).join("") : empty("Le prochain challenge apparaîtra ici.")}</article></section>`);
  document.querySelector("[data-send]")?.addEventListener("click", () => navigate("send"));
}

async function renderSend() {
  state.entities = await api("/entities");
  const options = state.entities.map(entity => `<option value="${entity.id}">${escape(entity.name)} · ${escape(kind(entity.kind))}</option>`).join("");
  shell(`<section class="hero"><div><p class="eyebrow">Écrire un merci</p><h1>Faire reconnaître ce qui compte.</h1><p>Précisez le geste ou la qualité qui vous a marqué.</p></div></section><section class="grid"><article class="card wide"><form class="form" id="message-form"><label class="field">Destinataire<select name="recipient_id" required><option value="">Choisir une personne, équipe ou service</option>${options}</select></label><label class="field">Votre message<textarea name="body" minlength="3" maxlength="1200" required placeholder="Merci pour… Votre disponibilité a permis de…"></textarea></label><label class="field">Force reconnue (facultatif)<input name="strength" maxlength="80" placeholder="Ex. entraide, sécurité, fiabilité"></label><label class="check"><input name="is_anonymous" type="checkbox"> Envoyer anonymement</label><label class="check"><input name="visibility" type="checkbox"> Proposer ce merci au mur commun après validation</label><div class="hint">Les mercis sont soumis à validation avant d'être remis. L'identité d'un auteur anonyme reste accessible uniquement en cas d'abus.</div><div class="form-actions"><button class="button primary" type="submit">Envoyer pour validation</button><button class="button secondary" type="button" data-page="home">Annuler</button></div></form></article><aside class="card side"><h2>Un merci qui fait du bien</h2><p>Parlez d'un fait concret, de son effet et de la qualité que vous avez appréciée.</p><p class="meta">Exemple : « Merci pour ta vigilance sur le chantier : elle a permis à toute l'équipe de travailler sereinement. »</p></aside></section>`);
  document.querySelector("#message-form").addEventListener("submit", submitMessage);
}

async function submitMessage(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    await api("/messages", { method: "POST", body: JSON.stringify({ recipient_ids: [Number(form.get("recipient_id"))], body: form.get("body"), strength: form.get("strength") || null, is_anonymous: form.get("is_anonymous") === "on", visibility: form.get("visibility") === "on" ? "common" : "private" }) });
    toast("Merci enregistré et transmis à la modération."); navigate("wall");
  } catch (error) { toast(error.message, true); }
}

async function renderWall() {
  const messages = await api("/messages");
  shell(`<section class="hero"><div><p class="eyebrow">Mon mur</p><h1>Les mots qui vous accompagnent.</h1><p>Vos mercis reçus et envoyés, réunis dans un espace personnel.</p></div><button class="button primary" data-page="send">Envoyer un merci</button></section><article class="card">${messages.length ? messages.map(messageCard).join("") : empty("Aucun merci pour le moment. Osez initier le premier geste.")}</article>`);
}

async function renderCommunity() {
  const messages = await api("/community");
  shell(`<section class="hero"><div><p class="eyebrow">Mur commun</p><h1>Les gestes qui nous rassemblent.</h1><p>Des mercis partagés avec l'accord de leur auteur et après validation.</p></div></section><section class="grid">${messages.length ? messages.map(message => `<article class="card side">${messageCard(message)}</article>`).join("") : `<article class="card wide">${empty("Le mur commun se construira avec les premiers mercis mis en lumière.")}</article>`}</section>`);
}

async function renderChallenges() {
  const challenges = await api("/challenges");
  shell(`<section class="hero"><div><p class="eyebrow">Challenges</p><h1>Mettre en lumière les bonnes pratiques.</h1><p>Proposez une personne, une équipe ou un service. Un vote par membre.</p></div>${state.me.role === "admin" ? `<button class="button primary" data-create-challenge>Créer un challenge</button>` : ""}</section><article class="card">${challenges.length ? challenges.map(challenge => `<div class="challenge"><div><span class="tag">${challenge.status === "closed" ? "Clôturé" : "Ouvert"}</span><h3>${escape(challenge.title)}</h3><div class="meta">${escape(challenge.theme)} · du ${date(challenge.opens_at)} au ${date(challenge.closes_at)}${challenge.winner_name ? ` · Lauréat : ${escape(challenge.winner_name)}` : ""}</div></div><button class="button secondary" data-challenge="${challenge.id}">Participer</button></div>`).join("") : empty("Aucun challenge n'est planifié.")}</article>`);
  document.querySelector("[data-create-challenge]")?.addEventListener("click", showChallengeForm);
  document.querySelectorAll("[data-challenge]").forEach(button => button.addEventListener("click", () => showChallenge(Number(button.dataset.challenge))));
}

async function showChallenge(id) {
  const [challenges, candidates] = await Promise.all([api("/challenges"), api(`/challenges/${id}/candidates`)]);
  const challenge = challenges.find(item => item.id === id);
  const choices = state.entities.length ? state.entities : await api("/entities"); state.entities = choices;
  dialog(`<div class="dialog-head"><div><p class="eyebrow">${escape(challenge.theme)}</p><h2>${escape(challenge.title)}</h2></div><button class="icon-button" data-close aria-label="Fermer">×</button></div><p class="hint">Clôture le ${date(challenge.closes_at)}. Vous pouvez proposer une candidature puis voter une seule fois.</p><div class="divider"></div>${candidates.length ? candidates.map(candidate => `<div class="candidate"><div><strong>${escape(candidate.name)}</strong><div class="meta">${candidate.votes} vote${candidate.votes > 1 ? "s" : ""}${candidate.voted_by_me ? " · votre vote" : ""}</div></div><button class="button secondary" data-vote="${candidate.id}" ${candidate.voted_by_me || challenge.status !== "open" ? "disabled" : ""}>Voter</button></div>`).join("") : empty("Aucune candidature pour l'instant.")}${challenge.status === "open" ? `<form class="form" id="nominate-form"><label class="field">Proposer au challenge<select name="entity_id" required>${choices.map(entity => `<option value="${entity.id}">${escape(entity.name)}</option>`).join("")}</select></label><button class="button primary">Proposer cette candidature</button></form>` : ""}${state.me.role !== "member" && challenge.status === "open" ? `<div class="divider"></div><button class="button danger" data-close-challenge>Clôturer et révéler le lauréat</button>` : ""}`);
  document.querySelectorAll("[data-vote]").forEach(button => button.addEventListener("click", () => vote(id, Number(button.dataset.vote))));
  document.querySelector("#nominate-form")?.addEventListener("submit", event => nominate(event, id));
  document.querySelector("[data-close-challenge]")?.addEventListener("click", () => closeChallenge(id));
}

const nominate = async (event, id) => { event.preventDefault(); try { await api(`/challenges/${id}/candidates/create`, { method: "POST", body: JSON.stringify({ entity_id: Number(new FormData(event.currentTarget).get("entity_id")) }) }); toast("Candidature enregistrée."); showChallenge(id); } catch (error) { toast(error.message, true); } };
const vote = async (id, candidateId) => { try { await api(`/challenges/${id}/votes/create`, { method: "POST", body: JSON.stringify({ candidate_id: candidateId }) }); toast("Votre vote est enregistré."); showChallenge(id); } catch (error) { toast(error.message, true); } };
const closeChallenge = async (id) => { try { await api(`/challenges/${id}/close/create`, { method: "POST", body: JSON.stringify({}) }); toast("Challenge clôturé : le lauréat est mis à l'honneur."); closeDialog(); renderChallenges(); } catch (error) { toast(error.message, true); } };

async function renderAdmin() {
  const pending = await api("/moderation");
  shell(`<section class="hero"><div><p class="eyebrow">Administration</p><h1>Veiller sur l'espace commun.</h1><p>Modérez les messages et préparez les prochaines initiatives.</p></div></section><section class="grid"><article class="card wide"><h2>File de modération</h2>${pending.length ? pending.map(message => `<div class="message"><p>${escape(message.body)}</p><div class="meta">Pour ${escape(message.recipients)} · par ${escape(message.author)} · ${date(message.created_at)}</div><div class="admin-actions"><button class="button primary" data-moderate="${message.id}" data-decision="approved">Approuver</button><button class="button danger" data-moderate="${message.id}" data-decision="rejected">Refuser</button></div></div>`).join("") : empty("La file est vide.")}</article><article class="card side"><h2>Référentiel</h2><p>Les membres connectés sont automatiquement disponibles comme destinataires.</p><button class="button secondary" data-add-entity>Ajouter une équipe, un service ou un partenaire</button></article></section>`);
  document.querySelectorAll("[data-moderate]").forEach(button => button.addEventListener("click", () => moderate(Number(button.dataset.moderate), button.dataset.decision)));
  document.querySelector("[data-add-entity]")?.addEventListener("click", showEntityForm);
}

async function moderate(id, decision) { const reason = decision === "rejected" ? window.prompt("Motif interne du refus (obligatoire) :") : null; if (decision === "rejected" && !reason) return; try { await api(`/messages/${id}/moderation`, { method: "POST", body: JSON.stringify({ decision, reason }) }); toast(decision === "approved" ? "Merci approuvé." : "Merci refusé."); renderAdmin(); } catch (error) { toast(error.message, true); } }
function dialog(content) { document.querySelector(".dialog")?.remove(); document.body.insertAdjacentHTML("beforeend", `<div class="dialog"><section class="dialog-panel" role="dialog" aria-modal="true">${content}</section></div>`); document.querySelector("[data-close]")?.addEventListener("click", closeDialog); }
function closeDialog() { document.querySelector(".dialog")?.remove(); }
function showEntityForm() { dialog(`<div class="dialog-head"><h2>Ajouter au référentiel</h2><button class="icon-button" data-close>×</button></div><form class="form" id="entity-form"><label class="field">Nom<input name="name" required maxlength="120"></label><label class="field">Type<select name="kind"><option value="team">Équipe</option><option value="service">Service</option><option value="client">Client</option><option value="contractor">Sous-traitant</option></select></label><button class="button primary">Ajouter</button></form>`); document.querySelector("#entity-form").addEventListener("submit", async event => { event.preventDefault(); const form = new FormData(event.currentTarget); try { await api("/entities", { method: "POST", body: JSON.stringify({ name: form.get("name"), kind: form.get("kind") }) }); toast("Entité ajoutée."); closeDialog(); renderAdmin(); } catch (error) { toast(error.message, true); } }); }
function showChallengeForm() { dialog(`<div class="dialog-head"><h2>Créer un challenge</h2><button class="icon-button" data-close>×</button></div><form class="form" id="challenge-form"><label class="field">Titre<input name="title" required maxlength="120" placeholder="Challenge amabilité"></label><label class="field">Thème<input name="theme" required maxlength="120" placeholder="Amabilité"></label><label class="field">Ouverture<input name="opens_at" type="date" required></label><label class="field">Clôture<input name="closes_at" type="date" required></label><button class="button primary">Créer le challenge</button></form>`); document.querySelector("#challenge-form").addEventListener("submit", async event => { event.preventDefault(); const form = new FormData(event.currentTarget); try { await api("/challenges", { method: "POST", body: JSON.stringify(Object.fromEntries(form)) }); toast("Challenge créé."); closeDialog(); renderChallenges(); } catch (error) { toast(error.message, true); } }); }
function kind(value) { return ({ person: "personne", team: "équipe", service: "service", client: "client", contractor: "sous-traitant" })[value] || value; }

async function boot() { try { state.me = await api("/me"); await renderHome(); } catch (error) { app.innerHTML = `<main class="app-loading">Impossible d'ouvrir Gratitude : ${escape(error.message)}</main>`; } }
boot();
