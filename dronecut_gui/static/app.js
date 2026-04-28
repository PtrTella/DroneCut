const API_BASE = 'http://localhost:8000';
let analyzedScenes = [];
let activeSceneIds = [];

const timeline = document.getElementById('timeline');
const btnAnalyze = document.getElementById('btn-analyze');
const btnExport = document.getElementById('btn-export');
const loadingOverlay = document.getElementById('loading-overlay');
const sceneCountBadge = document.getElementById('scene-count');
const statusBar = document.getElementById('status-bar');

// --- API Calls ---

async function startAnalysis() {
    const videoPaths = document.getElementById('video-paths').value.split(',').map(s => s.trim()).filter(s => s);
    const musicPath = document.getElementById('music-path').value.trim();
    const prompts = document.getElementById('positive-prompts').value.split(',').map(s => s.trim()).filter(s => s);
    const negativePrompts = document.getElementById('negative-prompts').value.split(',').map(s => s.trim()).filter(s => s);
    const speed = parseFloat(document.getElementById('base-speed').value);
    const threshold = parseFloat(document.getElementById('threshold').value);
    const maxScenes = parseInt(document.getElementById('max-scenes').value);
    const minDuration = parseFloat(document.getElementById('min-duration').value);
    const maxDurationValue = document.getElementById('max-duration').value;
    const maxDuration = maxDurationValue ? parseFloat(maxDurationValue) : null;

    if (videoPaths.length === 0) {
        alert("Inserisci almeno un video sorgente.");
        return;
    }

    showLoading("Analisi dei video in corso... Potrebbe richiedere qualche minuto.");

    try {
        const response = await fetch(`${API_BASE}/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                video_paths: videoPaths,
                music_path: musicPath || null,
                prompts: prompts,
                negative_prompts: negativePrompts,
                speed,
                threshold,
                max_scenes: maxScenes,
                min_duration: minDuration,
                max_duration: maxDuration
            })
        });

        if (!response.ok) throw new Error(await response.text());

        const data = await response.json();
        analyzedScenes = data.scenes;
        activeSceneIds = analyzedScenes.map(s => s.id);
        renderTimeline();
    } catch (err) {
        alert(`Errore durante l'analisi: ${err.message}`);
    } finally {
        hideLoading();
    }
}

async function startExport() {
    if (activeSceneIds.length === 0) return;

    showLoading("Esportazione finale in alta qualità in corso...");

    try {
        const response = await fetch(`${API_BASE}/export`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                scene_ids: activeSceneIds,
                out_dir: "gui_output"
            })
        });

        if (!response.ok) throw new Error(await response.text());

        const data = await response.json();
        alert(`Esportazione completata!\nFile: ${data.path}`);
        statusBar.textContent = `Ultimo export: ${data.path}`;
    } catch (err) {
        alert(`Errore durante l'esportazione: ${err.message}`);
    } finally {
        hideLoading();
    }
}

// --- UI Rendering ---

function renderTimeline() {
    timeline.innerHTML = '';

    if (analyzedScenes.length === 0) {
        timeline.innerHTML = `
            <div class="empty-state">
                <div class="icon">🎬</div>
                <h3>Nessuna scena trovata</h3>
                <p>Prova ad abbassare la soglia o cambiare i prompt.</p>
            </div>`;
        btnExport.disabled = true;
        sceneCountBadge.textContent = "0 Scene Trovate";
        return;
    }

    // Filter scenes based on active IDs
    const currentScenes = analyzedScenes.filter(s => activeSceneIds.includes(s.id));

    // Sort them by the order in activeSceneIds
    currentScenes.sort((a, b) => activeSceneIds.indexOf(a.id) - activeSceneIds.indexOf(b.id));

    currentScenes.forEach((scene, index) => {
        const card = document.createElement('div');
        card.className = 'scene-card';
        card.innerHTML = `
            <div class="card-preview">
                <video src="${scene.preview_url}" autoplay loop muted playsinline preload="metadata"></video>
                <button class="btn-delete" onclick="removeScene(${scene.id})">&times;</button>
            </div>
            <div class="card-info">
                <div class="card-header">
                    <span class="scene-time">${formatTime(scene.start)} - ${formatTime(scene.end)}</span>
                    <span class="scene-score">${(scene.score * 100).toFixed(0)}</span>
                </div>
                <div class="scene-meta">
                    <span>🎬 Semantica: <b>${(scene.semantic_score * 100).toFixed(0)}</b></span>
                    <span>✨ Estetica: <b>${(scene.aesthetic_score * 100).toFixed(0)}</b></span>
                    ${scene.cinematic_score > 0 ? `<span class="regia-badge">🤖 Regia: <b>${(scene.cinematic_score * 100).toFixed(0)}</b></span>` : ''}
                    <span>⚡ ${(scene.adaptive_speed).toFixed(1)}x</span>
                </div>
            </div>
        `;
        timeline.appendChild(card);
    });

    btnExport.disabled = activeSceneIds.length === 0;
    sceneCountBadge.textContent = `${activeSceneIds.length} Scene Selezionate`;
    statusBar.textContent = "Analisi completata. Trascina (prossimamente) o elimina le scene.";
}

function removeScene(id) {
    activeSceneIds = activeSceneIds.filter(sid => sid !== id);
    renderTimeline();
}

function showLoading(text) {
    document.getElementById('loading-text').textContent = text;
    loadingOverlay.classList.remove('hidden');
}

function hideLoading() {
    loadingOverlay.classList.add('hidden');
}

// --- Event Listeners ---

btnAnalyze.addEventListener('click', startAnalysis);
btnExport.addEventListener('click', startExport);

document.getElementById('btn-browse-videos').addEventListener('click', async () => {
    const response = await fetch(`${API_BASE}/pick-files`);
    const data = await response.json();
    if (data.files && data.files.length > 0) {
        document.getElementById('video-paths').value = data.files.join(', ');
    }
});

document.getElementById('btn-browse-music').addEventListener('click', async () => {
    const response = await fetch(`${API_BASE}/pick-file`);
    const data = await response.json();
    if (data.file) {
        document.getElementById('music-path').value = data.file;
    }
});

// --- Initialization ---

async function restoreSession() {
    try {
        console.log("Checking for previous session...");
        const response = await fetch(`${API_BASE}/session?out_dir=gui_output`);
        const data = await response.json();
        if (data.scenes && data.scenes.length > 0) {
            analyzedScenes = data.scenes;
            activeSceneIds = analyzedScenes.map(s => s.id);
            renderTimeline();
            statusBar.textContent = "Sessione precedente ripristinata correttamente.";
        }
    } catch (err) {
        console.error("Errore ripristino sessione:", err);
    }
}

// Start restoration on load
window.addEventListener('DOMContentLoaded', restoreSession);
