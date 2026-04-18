let allMessages = [];
let allFolders = [];
let isAdmin = false;

function getAdminPassword() {
    return localStorage.getItem('adminPassword') || '';
}

const gallery = document.getElementById('gallery');
const searchInput = document.getElementById('searchInput');
const yearFilter = document.getElementById('yearFilter');
const playerModal = document.getElementById('playerModal');
const manualModal = document.getElementById('manualModal');
const loginModal = document.getElementById('loginModal');
const adminPasswordInput = document.getElementById('adminPassword');
const loginBtn = document.getElementById('loginBtn');
const doLoginBtn = document.getElementById('doLoginBtn');
const loginStatus = document.getElementById('loginStatus');
const closeLoginModal = document.getElementById('closeLoginModal');
const closeModal = document.getElementById('closeModal');
const playerContainer = document.getElementById('playerContainer');
const statusText = document.getElementById('statusText');

async function loadMessages() {
    try {
        const [metaRes, folderRes] = await Promise.all([
            fetch('/api/metadata'),
            fetch('/api/folders')
        ]);
        allMessages = await metaRes.json();
        allFolders = await folderRes.json();

        // Sort by date descending
        allMessages.sort((a, b) => b.date.localeCompare(a.date));

        populateFolderFilter();
        renderGallery(allMessages);

        checkSyncStatus();
    } catch (error) {
        console.error('Error loading metadata:', error);
        statusText.innerText = '无法连接到后端服务器';
    }
}

loginBtn.onclick = () => {
    if (isAdmin) {
        // Logout
        isAdmin = false;
        localStorage.removeItem('adminPassword');
        loginBtn.innerHTML = '<i class="fa-solid fa-lock"></i>';
        loginBtn.title = "管理员登录";
        updateAdminUI();
        renderGallery(allMessages); // Refresh to hide edit buttons
    } else {
        loginModal.style.display = 'block';
        adminPasswordInput.value = '';
        loginStatus.innerText = '';
    }
};

doLoginBtn.onclick = async () => {
    const password = adminPasswordInput.value;
    // Test password by fetching metadata (or we could have a dedicated /api/login)
    // Actually, just set it and let subsequent requests fail if wrong
    isAdmin = true;
    localStorage.setItem('adminPassword', password);
    loginModal.style.display = 'none';
    loginBtn.innerHTML = '<i class="fa-solid fa-lock-open"></i>';
    loginBtn.title = "退出登录";
    updateAdminUI();
    renderGallery(allMessages);
};

closeLoginModal.onclick = () => loginModal.style.display = 'none';

function updateAdminUI() {
    const adminElements = document.querySelectorAll('.admin-only');
    adminElements.forEach(el => el.style.display = isAdmin ? 'inline-block' : 'none');
}

// Check initial login state
if (getAdminPassword()) {
    isAdmin = true;
    loginBtn.innerHTML = '<i class="fa-solid fa-lock-open"></i>';
    loginBtn.title = "退出登录";
    updateAdminUI();
}

async function checkSyncStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        const syncBtn = document.getElementById('syncBtn');

        if (data.is_syncing) {
            syncBtn.disabled = true;
            syncBtn.classList.add('spinning');
            syncBtn.title = '正在同步中...';
        } else {
            syncBtn.disabled = false;
            syncBtn.classList.remove('spinning');
            syncBtn.title = `立即检查并同步最新信息 (当前已加载 ${allMessages.length} 条信息)`;
        }
    } catch (e) { }
}

async function triggerSync() {
    try {
        const response = await fetch('/api/sync', {
            method: 'POST',
            headers: {
                'X-Admin-Password': getAdminPassword()
            }
        });
        if (response.ok) {
            checkSyncStatus();
        }
    } catch (error) {
        alert('触发同步失败');
    }
}

const bioPanel = document.getElementById('bioPanel');
const bioBtn = document.getElementById('bioBtn');
const closeBio = document.getElementById('closeBio');
// (already declared at top)
// (already declared at top)

bioBtn.onclick = () => bioPanel.classList.toggle('collapsed');
closeBio.onclick = () => bioPanel.classList.add('collapsed');

document.getElementById('addManualBtn').onclick = () => manualModal.style.display = 'flex';
document.getElementById('closeManualModal').onclick = () => manualModal.style.display = 'none';
document.getElementById('syncBtn').onclick = triggerSync;


function populateFolderFilter() {
    yearFilter.innerHTML = '<option value="all">所有分类</option>';
    allFolders.forEach(folder => {
        const option = document.createElement('option');
        option.value = folder;
        option.textContent = folder;
        yearFilter.appendChild(option);
    });
}

function renderGallery(messages) {
    gallery.innerHTML = '';
    messages.forEach((msg, index) => {
        const card = document.createElement('div');
        card.className = 'message-card';
        card.id = `msg-${index}`;
        const hasAudio = !!(msg.audio_url || msg.local_audio_path || (msg.local_path && !msg.local_path.endsWith('.mp4')));
        const hasVideo = !!(msg.video_url || msg.local_video_path || (msg.local_path && msg.local_path.endsWith('.mp4')) || (msg.url && msg.url.endsWith('.mp4')));

        card.innerHTML = `
        <div class="edit-overlay admin-only" title="编辑信息" style="${isAdmin ? '' : 'display:none'}">✏️</div>
            <div class="message-date">${msg.date}</div>
            <div class="message-topic-zh">${msg.topic_zh || '无中文标题'}</div>
            <div class="message-topic-en">${msg.topic_en || ''}</div>
            <div class="message-meta">
                <div class="scripture">${msg.scripture}</div>
                <div class="media-badges">
                    ${hasAudio ? '<span class="play-badge" title="收听音频"><i class="fa-solid fa-microphone"></i></span>' : ''}
                    ${hasVideo ? '<span class="play-badge video" title="观看视频"><i class="fa-brands fa-youtube"></i></span>' : ''}
                </div>
            </div>
            ${msg.tags ? `
            <div class="message-tags">
                ${msg.tags.split(',').map(tag => `<span class="tag-badge">${tag.trim()}</span>`).join('')}
            </div>` : ''}
            ${msg.remarks ? `<div class="message-remarks"><i class="fa-solid fa-note-sticky"></i> ${msg.remarks}</div>` : ''}
            
            <div class="impressions-section">
                <div class="impressions-title">
                    <span>听众感想 (${(msg.impressions || []).length})</span>
                </div>
                <ul class="impressions-list">
                    ${(msg.impressions || []).map(imp => `<li class="impression-item">${imp}</li>`).join('')}
                    ${(msg.impressions || []).length === 0 ? '<li class="impression-item" style="border:none; color:var(--text-muted); opacity:0.6;">暂无感想</li>' : ''}
                </ul>
                <div class="impression-input-group">
                    <input type="text" class="impression-input" placeholder="输入你的感想..." id="imp-input-${index}">
                    <button class="btn-impression" onclick="event.stopPropagation(); submitImpression(${index})">提交</button>
                </div>
            </div>
            <div class="card-player-container" id="player-container-${index}"></div>
        `;

        card.querySelector('.edit-overlay').onclick = (e) => {
            e.stopPropagation();
            editMessage(msg);
        };

        // Handle specific badge clicks
        const audioBadge = card.querySelector('.play-badge:not(.video)');
        const videoBadge = card.querySelector('.play-badge.video');

        if (audioBadge) {
            audioBadge.onclick = (e) => {
                e.stopPropagation();
                openPlayer(msg, index, 'audio');
            };
        }

        if (videoBadge) {
            videoBadge.onclick = (e) => {
                e.stopPropagation();
                openPlayer(msg, index, 'video');
            };
        }

        // Card click defaults to audio (if available) or auto
        card.onclick = () => openPlayer(msg, index, 'card');
        gallery.appendChild(card);
    });
}

function convertGDriveLink(url) {
    if (!url) return url;
    if (url.includes('drive.google.com')) {
        let fileId = '';
        if (url.includes('id=')) fileId = url.split('id=')[1].split('&')[0];
        else if (url.includes('/d/')) fileId = url.split('/d/')[1].split('/')[0];

        if (fileId) return `https://drive.google.com/uc?export=download&id=${fileId}`;
    }
    return url;
}

function openPlayer(msg, index, mode = 'auto') {
    let isYouTube = !!(msg.url && (msg.url.includes('youtube.com') || msg.url.includes('youtu.be')));
    if (!isYouTube && msg.video_url) {
        isYouTube = msg.video_url.includes('youtube.com') || msg.video_url.includes('youtu.be');
    }

    let mediaPath = '';

    if (mode === 'audio') {
        mediaPath = msg.local_audio_path || msg.audio_url || (msg.local_path && !msg.local_path.endsWith('.mp4') ? msg.local_path : null);
    } else if (mode === 'video') {
        mediaPath = msg.local_video_path || msg.video_url || (msg.local_path && msg.local_path.endsWith('.mp4') ? msg.local_path : null);
    } else {
        // card click or auto mode
        // If it has audio, use it first (integrated player). Otherwise use video (modal).
        const hasAudio = !!(msg.audio_url || msg.local_audio_path || (msg.local_path && !msg.local_path.endsWith('.mp4')));
        if (hasAudio) {
            mediaPath = msg.local_audio_path || msg.audio_url || (msg.local_path && !msg.local_path.endsWith('.mp4') ? msg.local_path : null);
            mode = 'audio';
        } else {
            mediaPath = msg.local_video_path || msg.video_url || (msg.local_path && msg.local_path.endsWith('.mp4') ? msg.local_path : null) || msg.url;
            mode = 'video';
        }
    }

    if (!mediaPath) return;

    mediaPath = convertGDriveLink(mediaPath);

    if (mediaPath && !mediaPath.startsWith('http')) {
        mediaPath = '/' + mediaPath.replace(/\\/g, '/');
    }

    // Stop and hide ALL other in-card players
    document.querySelectorAll('.card-player-container').forEach(container => {
        if (container.id !== `player-container-${index}`) {
            container.innerHTML = '';
            container.classList.remove('active');
        }
    });

    const currentIsYouTube = !!(mediaPath && (mediaPath.includes('youtube.com') || mediaPath.includes('youtu.be')));

    if (mode === 'video' || currentIsYouTube) {
        // Use Modal for Video or YouTube
        document.getElementById('modalTopicZH').innerText = msg.topic_zh;
        document.getElementById('modalTopicEN').innerText = msg.topic_en;
        document.getElementById('modalDate').innerText = `${msg.date} | ${msg.type}`;

        if (currentIsYouTube) {
            let videoId = '';
            const url = mediaPath;
            if (url.includes('v=')) videoId = url.split('v=')[1].split('&')[0];
            else if (url.includes('live/')) videoId = url.split('live/')[1].split('?')[0];
            else if (url.includes('be/')) videoId = url.split('be/')[1];

            playerContainer.innerHTML = `<iframe width="100%" height="450" src="https://www.youtube.com/embed/${videoId}?autoplay=1" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>`;
        } else {
            playerContainer.innerHTML = `<video id="modalVideo" controls src="${mediaPath}" autoplay></video>`;
            const video = document.getElementById('modalVideo');
            if (video) video.play().catch(e => console.log("Video auto-play blocked:", e));
        }
        playerModal.style.display = 'flex';
    } else {
        // Toggle/Use Integrated In-Card Player for Audio
        const targetContainer = document.getElementById(`player-container-${index}`);
        if (targetContainer.classList.contains('active')) {
            // Already active, just close it
            targetContainer.innerHTML = '';
            targetContainer.classList.remove('active');
        } else {
            targetContainer.innerHTML = `<audio id="audio-${index}" controls src="${mediaPath}" autoplay style="width: 100%;"></audio>`;
            targetContainer.classList.add('active');
            const audio = document.getElementById(`audio-${index}`);
            if (audio) audio.play().catch(e => console.log("Audio auto-play blocked:", e));
        }
    }
}

function editMessage(msg) {
    document.getElementById('mDate').value = msg.date;
    document.getElementById('mTopicZH').value = msg.topic_zh;
    document.getElementById('mTopicEN').value = msg.topic_en;
    document.getElementById('mUrl').value = msg.video_url || msg.audio_url || msg.url;
    document.getElementById('mScripture').value = msg.scripture;
    document.getElementById('mType').value = msg.type;
    document.getElementById('mTags').value = msg.tags || '';
    document.getElementById('mRemarks').value = msg.remarks || '';
    manualModal.style.display = 'flex';
}

async function submitImpression(index) {
    const msg = allMessages[index];
    const input = document.getElementById(`imp-input-${index}`);
    const text = input.value.trim();
    if (!text) return;

    try {
        const response = await fetch('/api/add_impression', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                date: msg.date,
                topic_zh: msg.topic_zh,
                text: text
            })
        });
        if (response.ok) {
            input.value = '';
            loadMessages(); // Reload to show new impression
        } else {
            alert('提交失败');
        }
    } catch (error) {
        alert('提交出错');
    }
}

// Add File Upload Logic to app.js
const filePickBtn = document.getElementById('filePickBtn');
const mFile = document.getElementById('mFile');
const fileStatus = document.getElementById('fileStatus');

filePickBtn.onclick = () => mFile.click();
mFile.onchange = () => {
    fileStatus.innerText = mFile.files[0] ? `已选择: ${mFile.files[0].name}` : '未选择文件';
};

manualForm.onsubmit = async (e) => {
    e.preventDefault();
    let localPath = null;

    if (mFile.files[0]) {
        console.log('Uploading file...');
        const formData = new FormData();
        formData.append('file', mFile.files[0]);
        const subfolder = document.getElementById('mSubfolder').value.trim();
        if (subfolder) formData.append('subfolder', subfolder);

        try {
            const uploadRes = await fetch('/api/upload', {
                method: 'POST',
                headers: {
                    'X-Admin-Password': getAdminPassword()
                },
                body: formData
            });
            const uploadData = await uploadRes.json();
            if (uploadData.status === 'success') {
                localPath = uploadData.relative_path;
            } else {
                alert('上传文件失败: ' + uploadData.message);
                return;
            }
        } catch (err) {
            alert('上传过程出错');
            return;
        }
    }

    const data = {
        date: document.getElementById('mDate').value,
        topic_zh: document.getElementById('mTopicZH').value,
        topic_en: document.getElementById('mTopicEN').value,
        url: document.getElementById('mUrl').value || (mFile.files[0] ? mFile.files[0].name : ""),
        audio_url: null,
        video_url: null,
        local_audio_path: localPath && !localPath.endsWith('.mp4') ? localPath : null,
        local_video_path: localPath && localPath.endsWith('.mp4') ? localPath : null,
        scripture: document.getElementById('mScripture').value,
        type: document.getElementById('mType').value,
        tags: document.getElementById('mTags').value,
        remarks: document.getElementById('mRemarks').value
    };

    try {
        const response = await fetch('/api/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Admin-Password': getAdminPassword()
            },
            body: JSON.stringify(data)
        });
        if (response.ok) {
            alert('添加成功');
            manualModal.style.display = 'none';
            manualForm.reset();
            fileStatus.innerText = '未选择文件';
            loadMessages();
        } else {
            const err = await response.json();
            alert('错误: ' + err.message);
        }
    } catch (error) {
        alert('添加失败');
    }
};

function closePlayer() {
    playerContainer.innerHTML = '';
    playerModal.style.display = 'none';
}

function filterMessages() {
    const query = searchInput.value.toLowerCase();
    const folder = yearFilter.value; // Reuse existing dropdown element for folders

    const filtered = allMessages.filter(m => {
        const matchesQuery = (m.topic_zh && m.topic_zh.toLowerCase().includes(query)) ||
            (m.topic_en && m.topic_en.toLowerCase().includes(query)) ||
            (m.scripture && m.scripture.toLowerCase().includes(query)) ||
            (m.tags && m.tags.toLowerCase().includes(query)) ||
            (m.remarks && m.remarks.toLowerCase().includes(query)) ||
            (m.impressions && m.impressions.some(imp => imp.toLowerCase().includes(query))) ||
            (m.date && m.date.includes(query));

        let matchesFolder = folder === 'all';
        if (!matchesFolder) {
            const paths = [m.local_path, m.local_audio_path, m.local_video_path];
            matchesFolder = paths.some(p => p && p.includes(`media/${folder}/`));

            // Fallback: If folder looks like a 4-digit year, match by date as well
            if (!matchesFolder && /^\d{4}$/.test(folder)) {
                matchesFolder = m.date && m.date.startsWith(folder);
            }
        }

        return matchesQuery && matchesFolder;
    });

    renderGallery(filtered);
}

searchInput.addEventListener('input', filterMessages);
yearFilter.addEventListener('change', filterMessages);
closeModal.onclick = closePlayer;
window.onclick = (event) => {
    if (event.target == playerModal) closePlayer();
    if (event.target == manualModal) manualModal.style.display = 'none';
};

// Initial load
loadMessages();

// Refresh status every 5 seconds
setInterval(checkSyncStatus, 5000);
