let allMessages = [];

const gallery = document.getElementById('gallery');
const searchInput = document.getElementById('searchInput');
const yearFilter = document.getElementById('yearFilter');
const playerModal = document.getElementById('playerModal');
const closeModal = document.getElementById('closeModal');
const playerContainer = document.getElementById('playerContainer');
const statusText = document.getElementById('statusText');

async function loadMessages() {
    try {
        const response = await fetch('/api/metadata');
        allMessages = await response.json();

        // Sort by date descending
        allMessages.sort((a, b) => b.date.localeCompare(a.date));

        populateYearFilter();
        renderGallery(allMessages);

        checkSyncStatus();
    } catch (error) {
        console.error('Error loading metadata:', error);
        statusText.innerText = '无法连接到后端服务器';
    }
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
        const response = await fetch('/api/sync', { method: 'POST' });
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
const manualModal = document.getElementById('manualModal');
const manualForm = document.getElementById('manualForm');

bioBtn.onclick = () => bioPanel.classList.toggle('collapsed');
closeBio.onclick = () => bioPanel.classList.add('collapsed');

document.getElementById('addManualBtn').onclick = () => manualModal.style.display = 'flex';
document.getElementById('closeManualModal').onclick = () => manualModal.style.display = 'none';
document.getElementById('syncBtn').onclick = triggerSync;

manualForm.onsubmit = async (e) => {
    e.preventDefault();
    const data = {
        date: document.getElementById('mDate').value,
        topic_zh: document.getElementById('mTopicZH').value,
        topic_en: document.getElementById('mTopicEN').value,
        url: document.getElementById('mUrl').value,
        scripture: document.getElementById('mScripture').value,
        type: document.getElementById('mType').value
    };

    try {
        const response = await fetch('/api/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (response.ok) {
            alert('添加成功');
            manualModal.style.display = 'none';
            loadMessages();
        } else {
            const err = await response.json();
            alert('错误: ' + err.message);
        }
    } catch (error) {
        alert('添加失败');
    }
};

function populateYearFilter() {
    const years = [...new Set(allMessages.map(m => m.date.split('-')[0]))].sort().reverse();
    yearFilter.innerHTML = '<option value="all">所有年份</option>';
    years.forEach(year => {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        yearFilter.appendChild(option);
    });
}

function renderGallery(messages) {
    gallery.innerHTML = '';
    messages.forEach(msg => {
        const card = document.createElement('div');
        card.className = 'message-card';
        const hasAudio = !!(msg.audio_url || msg.local_audio_path || (!msg.audio_url && !msg.video_url && msg.url && !msg.url.endsWith('.mp4')));
        const hasVideo = !!(msg.video_url || msg.local_video_path || (msg.url && msg.url.endsWith('.mp4')));

        card.innerHTML = `
            <div class="edit-overlay" title="编辑信息">✏️</div>
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
        `;

        card.querySelector('.edit-overlay').onclick = (e) => {
            e.stopPropagation();
            editMessage(msg);
        };
        card.onclick = () => openPlayer(msg);
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

function openPlayer(msg) {
    let isVideo = !!(msg.video_url || msg.local_video_path || (msg.url && msg.url.endsWith('.mp4')));
    let rawPath = msg.local_video_path || msg.video_url || msg.local_audio_path || msg.audio_url || msg.url;

    let mediaPath = convertGDriveLink(rawPath);

    if (mediaPath && !mediaPath.startsWith('http')) {
        mediaPath = '/' + mediaPath;
    }

    document.getElementById('modalTopicZH').innerText = msg.topic_zh;
    document.getElementById('modalTopicEN').innerText = msg.topic_en;
    document.getElementById('modalDate').innerText = `${msg.date} | ${msg.type}`;

    if (mediaPath && (mediaPath.includes('youtube.com') || mediaPath.includes('youtu.be'))) {
        let videoId = '';
        if (mediaPath.includes('v=')) videoId = mediaPath.split('v=')[1].split('&')[0];
        else if (mediaPath.includes('live/')) videoId = mediaPath.split('live/')[1].split('?')[0];
        else if (mediaPath.includes('be/')) videoId = mediaPath.split('be/')[1];

        playerContainer.innerHTML = `<iframe width="100%" height="450" src="https://www.youtube.com/embed/${videoId}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>`;
    } else {
        playerContainer.innerHTML = isVideo
            ? `<video controls src="${mediaPath}" autoplay></video>`
            : `<audio controls src="${mediaPath}" autoplay></audio>`;
    }

    playerModal.style.display = 'flex';
}

function editMessage(msg) {
    document.getElementById('mDate').value = msg.date;
    document.getElementById('mTopicZH').value = msg.topic_zh;
    document.getElementById('mTopicEN').value = msg.topic_en;
    document.getElementById('mUrl').value = msg.video_url || msg.audio_url || msg.url;
    document.getElementById('mScripture').value = msg.scripture;
    document.getElementById('mType').value = msg.type;
    manualModal.style.display = 'flex';
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
            const uploadRes = await fetch('/api/upload', { method: 'POST', body: formData });
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
        type: document.getElementById('mType').value
    };

    try {
        const response = await fetch('/api/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
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
    const year = yearFilter.value;

    const filtered = allMessages.filter(m => {
        const matchesQuery = (m.topic_zh && m.topic_zh.toLowerCase().includes(query)) ||
            (m.topic_en && m.topic_en.toLowerCase().includes(query)) ||
            (m.scripture && m.scripture.toLowerCase().includes(query)) ||
            (m.date && m.date.includes(query));
        const matchesYear = year === 'all' || m.date.startsWith(year);
        return matchesQuery && matchesYear;
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
