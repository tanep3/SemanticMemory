/**
 * Neural Dive - SemanticMemory Dashboard
 * app.js - API通信 + DOM操作
 */

// ===========================================
// Configuration
// ===========================================
const API_BASE = '/api';
const PAGE_SIZE = 20;

// ===========================================
// State
// ===========================================
let currentOffset = 0;
let currentMemory = null;
let isSearchMode = false;

// ===========================================
// DOM Elements
// ===========================================
const elements = {
    memoryCards: document.getElementById('memory-cards'),
    loading: document.getElementById('loading'),
    noResults: document.getElementById('no-results'),
    loadMoreBtn: document.getElementById('load-more-btn'),
    loadMoreContainer: document.getElementById('load-more-container'),
    searchInput: document.getElementById('search-input'),
    keywordSearchBtn: document.getElementById('keyword-search-btn'),
    vectorSearchBtn: document.getElementById('vector-search-btn'),
    clearSearchBtn: document.getElementById('clear-search-btn'),
    cleanupBtn: document.getElementById('cleanup-btn'),

    // Modal
    detailModal: document.getElementById('detail-modal'),
    closeModalBtn: document.getElementById('close-modal-btn'),
    editMainText: document.getElementById('edit-main-text'),
    editSubText: document.getElementById('edit-sub-text'),
    editSummary: document.getElementById('edit-summary'),
    editId: document.getElementById('edit-id'),
    editCreated: document.getElementById('edit-created'),
    editUpdated: document.getElementById('edit-updated'),
    regenerateSummaryBtn: document.getElementById('regenerate-summary-btn'),
    deleteMemoryBtn: document.getElementById('delete-memory-btn'),
    saveMemoryBtn: document.getElementById('save-memory-btn'),

    // Confirm Dialog
    confirmDialog: document.getElementById('confirm-dialog'),
    confirmTitle: document.getElementById('confirm-title'),
    confirmMessage: document.getElementById('confirm-message'),
    confirmCancelBtn: document.getElementById('confirm-cancel-btn'),
    confirmOkBtn: document.getElementById('confirm-ok-btn'),

    // Toast
    toast: document.getElementById('toast'),
    toastMessage: document.getElementById('toast-message')
};

// ===========================================
// API Functions
// ===========================================
async function fetchRecent(limit = PAGE_SIZE, offset = 0) {
    const res = await fetch(`${API_BASE}/get_recent_db?limit=${limit}&offset=${offset}`);
    if (!res.ok) throw new Error('Failed to fetch');
    return res.json();
}

async function searchKeyword(query) {
    const res = await fetch(`${API_BASE}/search_db?q=${encodeURIComponent(query)}&limit=50`);
    if (!res.ok) throw new Error('Failed to search');
    return res.json();
}

async function searchVector(query) {
    const res = await fetch(`${API_BASE}/search_vector`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, limit: 50 })
    });
    if (!res.ok) throw new Error('Failed to search');
    return res.json();
}

async function updateMemory(id, mainText, subText, summaryText) {
    const body = { id };
    if (mainText !== undefined) body.main_text = mainText;
    if (subText !== undefined) body.sub_text = subText;
    if (summaryText !== undefined) body.summary_text = summaryText;

    const res = await fetch(`${API_BASE}/update_memory`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    if (!res.ok) throw new Error('Failed to update');
    return res.json();
}

async function deleteMemory(id) {
    const res = await fetch(`${API_BASE}/delete_memory?id=${id}`, {
        method: 'DELETE'
    });
    if (!res.ok) throw new Error('Failed to delete');
    return res.json();
}

async function regenerateSummary(text) {
    const res = await fetch(`${API_BASE}/summarize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
    });
    if (!res.ok) throw new Error('Failed to summarize');
    return res.json();
}

async function cleanupAuditLogs() {
    const res = await fetch(`${API_BASE}/cleanup_audit_logs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
    });
    if (!res.ok) throw new Error('Failed to cleanup');
    return res.json();
}

// ===========================================
// UI Functions
// ===========================================
function showLoading() {
    elements.loading.classList.remove('hidden');
    elements.noResults.classList.add('hidden');
}

function hideLoading() {
    elements.loading.classList.add('hidden');
}

function showNoResults() {
    elements.noResults.classList.remove('hidden');
}

function showToast(message, isError = false) {
    elements.toastMessage.textContent = message;
    elements.toast.classList.remove('hidden', 'error');
    if (isError) elements.toast.classList.add('error');

    setTimeout(() => {
        elements.toast.classList.add('hidden');
    }, 3000);
}

function formatDate(isoString) {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleString('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function truncate(str, len = 100) {
    if (!str) return '';
    return str.length > len ? str.substring(0, len) + '...' : str;
}

function createMemoryCard(memory) {
    const card = document.createElement('div');
    card.className = 'memory-card';
    card.dataset.id = memory.id;

    card.innerHTML = `
        <div class="card-header">
            <span class="card-id">#${memory.id}</span>
            <span class="card-date">${formatDate(memory.create_time)}</span>
        </div>
        <div class="card-summary">${memory.summary_text || '(要約なし)'}</div>
        <div class="card-snippet">${truncate(memory.main_text, 80)}</div>
        <div class="card-actions">
            <button class="card-delete-btn" title="削除">🗑️</button>
        </div>
    `;

    // Card click -> open modal
    card.addEventListener('click', (e) => {
        if (e.target.classList.contains('card-delete-btn')) {
            e.stopPropagation();
            confirmDelete(memory);
        } else {
            openDetailModal(memory);
        }
    });

    return card;
}

function renderMemories(memories, append = false) {
    if (!append) {
        elements.memoryCards.innerHTML = '';
    }

    if (memories.length === 0 && !append) {
        showNoResults();
        elements.loadMoreContainer.classList.add('hidden');
        return;
    }

    memories.forEach(memory => {
        elements.memoryCards.appendChild(createMemoryCard(memory));
    });

    // Show/hide load more button
    if (memories.length < PAGE_SIZE || isSearchMode) {
        elements.loadMoreContainer.classList.add('hidden');
    } else {
        elements.loadMoreContainer.classList.remove('hidden');
    }
}

// ===========================================
// Modal Functions
// ===========================================
function openDetailModal(memory) {
    currentMemory = memory;

    elements.editMainText.value = memory.main_text || '';
    elements.editSubText.value = memory.sub_text || '';
    elements.editSummary.value = memory.summary_text || '';
    elements.editId.textContent = `ID: ${memory.id}`;
    elements.editCreated.textContent = `作成: ${formatDate(memory.create_time)}`;
    elements.editUpdated.textContent = `更新: ${formatDate(memory.update_time)}`;

    elements.detailModal.classList.remove('hidden');
}

function closeDetailModal() {
    elements.detailModal.classList.add('hidden');
    currentMemory = null;
}

function showConfirmDialog(title, message) {
    return new Promise((resolve) => {
        elements.confirmTitle.textContent = title;
        elements.confirmMessage.textContent = message;
        elements.confirmDialog.classList.remove('hidden');

        const cleanup = () => {
            elements.confirmDialog.classList.add('hidden');
            elements.confirmOkBtn.removeEventListener('click', onOk);
            elements.confirmCancelBtn.removeEventListener('click', onCancel);
        };

        const onOk = () => {
            cleanup();
            resolve(true);
        };

        const onCancel = () => {
            cleanup();
            resolve(false);
        };

        elements.confirmOkBtn.addEventListener('click', onOk);
        elements.confirmCancelBtn.addEventListener('click', onCancel);
    });
}

// ===========================================
// Actions
// ===========================================
async function loadRecent() {
    showLoading();
    try {
        const memories = await fetchRecent(PAGE_SIZE, currentOffset);
        renderMemories(memories, currentOffset > 0);
    } catch (e) {
        showToast('データの読み込みに失敗しました', true);
    } finally {
        hideLoading();
    }
}

async function loadMore() {
    currentOffset += PAGE_SIZE;
    showLoading();
    try {
        const memories = await fetchRecent(PAGE_SIZE, currentOffset);
        renderMemories(memories, true);
    } catch (e) {
        showToast('データの読み込みに失敗しました', true);
    } finally {
        hideLoading();
    }
}

async function doKeywordSearch() {
    const query = elements.searchInput.value.trim();
    if (!query) return;

    isSearchMode = true;
    currentOffset = 0;
    showLoading();

    try {
        const memories = await searchKeyword(query);
        renderMemories(memories);
    } catch (e) {
        showToast('検索に失敗しました', true);
    } finally {
        hideLoading();
    }
}

async function doVectorSearch() {
    const query = elements.searchInput.value.trim();
    if (!query) return;

    isSearchMode = true;
    currentOffset = 0;
    showLoading();

    try {
        const results = await searchVector(query);

        // Vector検索結果からSQLiteの詳細を取得
        const memories = [];
        for (const r of results) {
            try {
                // SQLiteから詳細取得を試みる
                const res = await fetch(`${API_BASE}/get_by_id_db?id=${r.id}`);
                if (res.ok) {
                    const detail = await res.json();
                    detail._vectorScore = r.score; // スコアを追加
                    memories.push(detail);
                } else {
                    // SQLiteにない = 孤児ベクトル
                    memories.push({
                        id: parseInt(r.id),
                        main_text: r.document,
                        summary_text: `⚠️ 孤児ベクトル (Score: ${r.score.toFixed(3)})`,
                        create_time: null,
                        _isOrphan: true,
                        _vectorScore: r.score
                    });
                }
            } catch {
                // エラー時も孤児として扱う
                memories.push({
                    id: parseInt(r.id),
                    main_text: r.document,
                    summary_text: `⚠️ 孤児ベクトル (Score: ${r.score.toFixed(3)})`,
                    create_time: null,
                    _isOrphan: true,
                    _vectorScore: r.score
                });
            }
        }
        renderMemories(memories);
    } catch (e) {
        showToast('意味検索に失敗しました', true);
    } finally {
        hideLoading();
    }
}


function clearSearch() {
    elements.searchInput.value = '';
    isSearchMode = false;
    currentOffset = 0;
    loadRecent();
}

async function saveCurrentMemory() {
    if (!currentMemory) return;

    const mainText = elements.editMainText.value;
    const subText = elements.editSubText.value;
    const summaryText = elements.editSummary.value;

    // Check what changed
    const mainChanged = mainText !== currentMemory.main_text;
    const subChanged = subText !== currentMemory.sub_text;
    const summaryChanged = summaryText !== currentMemory.summary_text;

    if (!mainChanged && !subChanged && !summaryChanged) {
        showToast('変更がありません');
        return;
    }

    try {
        const result = await updateMemory(
            currentMemory.id,
            mainChanged ? mainText : undefined,
            subChanged ? subText : undefined,
            summaryChanged && !mainChanged ? summaryText : undefined
        );

        showToast('保存しました' + (result.summary_regenerated ? ' (サマリー再生成)' : ''));
        closeDetailModal();

        // Refresh list
        isSearchMode = false;
        currentOffset = 0;
        loadRecent();
    } catch (e) {
        showToast('保存に失敗しました', true);
    }
}

async function confirmDelete(memory) {
    const isOrphan = memory._isOrphan;
    const confirmed = await showConfirmDialog(
        isOrphan ? '孤児ベクトルの削除' : '記憶の削除',
        isOrphan
            ? `ID: ${memory.id} の孤児ベクトルを削除しますか？\n\n（ChromaDBから直接削除されます）`
            : `ID: ${memory.id} の記憶を削除しますか？\n\nこの操作は取り消せません。`
    );

    if (confirmed) {
        try {
            if (isOrphan) {
                // 孤児ベクトルはChromaDBから直接削除
                const res = await fetch(`${API_BASE}/delete_data_vector?id=${memory.id}`, {
                    method: 'DELETE'
                });
                if (!res.ok) throw new Error('Failed to delete');
            } else {
                // 通常の記憶は統合削除
                await deleteMemory(memory.id);
            }
            showToast('削除しました');

            // Close modal if open
            if (currentMemory && currentMemory.id === memory.id) {
                closeDetailModal();
            }

            // Refresh list
            isSearchMode = false;
            currentOffset = 0;
            loadRecent();
        } catch (e) {
            showToast('削除に失敗しました', true);
        }
    }
}

async function doRegenerateSummary() {
    if (!currentMemory) return;

    const mainText = elements.editMainText.value;
    if (!mainText.trim()) {
        showToast('本文が空です', true);
        return;
    }

    try {
        const result = await regenerateSummary(mainText);

        // Show preview in confirm dialog
        const confirmed = await showConfirmDialog(
            '要約プレビュー',
            `新しい要約:\n\n${result.summary}\n\nこの要約を適用しますか？`
        );

        if (confirmed) {
            elements.editSummary.value = result.summary;
            showToast('要約を適用しました（保存ボタンで保存してください）');
        }
    } catch (e) {
        showToast('要約生成に失敗しました', true);
    }
}

async function doCleanup() {
    const confirmed = await showConfirmDialog(
        'マイグレーション確認',
        '監査ログを全て削除します。\n\nこの操作は取り消せません。続行しますか？'
    );

    if (confirmed) {
        try {
            const result = await cleanupAuditLogs();
            showToast(`${result.deleted_count} 件の監査ログを削除しました`);
        } catch (e) {
            showToast('マイグレーションに失敗しました', true);
        }
    }
}

// ===========================================
// Event Listeners
// ===========================================
elements.loadMoreBtn.addEventListener('click', loadMore);
elements.keywordSearchBtn.addEventListener('click', doKeywordSearch);
elements.vectorSearchBtn.addEventListener('click', doVectorSearch);
elements.clearSearchBtn.addEventListener('click', clearSearch);
elements.cleanupBtn.addEventListener('click', doCleanup);

elements.closeModalBtn.addEventListener('click', closeDetailModal);
elements.detailModal.querySelector('.modal-overlay').addEventListener('click', closeDetailModal);
elements.saveMemoryBtn.addEventListener('click', saveCurrentMemory);
elements.deleteMemoryBtn.addEventListener('click', () => {
    if (currentMemory) confirmDelete(currentMemory);
});
elements.regenerateSummaryBtn.addEventListener('click', doRegenerateSummary);

// Confirm dialog overlay click
elements.confirmDialog.querySelector('.modal-overlay').addEventListener('click', () => {
    elements.confirmCancelBtn.click();
});

// Enter key to search
elements.searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        doKeywordSearch();
    }
});

// ===========================================
// Initialize
// ===========================================
document.addEventListener('DOMContentLoaded', () => {
    loadRecent();
});
