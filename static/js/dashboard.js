document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('accessToken');
    const path = window.location.pathname;
    const api = {
        getWallets: async () => { const res = await fetch('/api/wallets', { headers: { 'Authorization': `Bearer ${token}` } }); if (res.status === 401) logout(); if (!res.ok) throw new Error('Failed to fetch wallets'); return await res.json(); },
        addWallet: async (data) => { const res = await fetch('/api/wallets', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }, body: JSON.stringify(data) }); if (res.status === 401) logout(); return res; },
        deleteWallet: async (id) => { const res = await fetch(`/api/wallets/${id}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } }); if (res.status === 401) logout(); return res.ok; },
        updateWallet: async (id, data) => { const res = await fetch(`/api/wallets/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` }, body: JSON.stringify(data) }); if (res.status === 401) logout(); return res; }
    };
    const ui = {
        walletList: document.getElementById('wallet-list'),
        renderWallets: (wallets) => {
            if (!ui.walletList) return;
            ui.walletList.innerHTML = '';
            wallets.forEach(wallet => {
                const row = document.createElement('tr');
                row.innerHTML = `<td>${wallet.name}</td><td>${wallet.address}</td><td>${wallet.bot_token}</td><td>${wallet.chat_id}</td><td><button class="edit-btn" data-id="${wallet.id}">수정</button><button class="delete-btn" data-id="${wallet.id}">삭제</button></td>`;
                ui.walletList.appendChild(row);
            });
        }
    };
    const form = {
        title: document.getElementById('form-title'), form: document.getElementById('add-wallet-form'), walletId: document.getElementById('wallet-id'), name: document.getElementById('name'),
        address: document.getElementById('address'), bot_token: document.getElementById('bot_token'), chat_id: document.getElementById('chat_id'), notification_url: document.getElementById('notification_url'),
        notification_api_key: document.getElementById('notification_api_key'), submitBtn: document.getElementById('form-submit-btn'), errorMsg: document.getElementById('form-error'),
        reset: function() { this.form.reset(); this.walletId.value = ''; this.errorMsg.textContent = ''; }
    };
    const setFormMode = (mode, wallet = {}) => {
        form.reset();
        if (mode === 'edit') {
            form.title.textContent = '지갑 정보 수정'; form.submitBtn.textContent = '수정 완료'; form.walletId.value = wallet.id; form.name.value = wallet.name;
            form.address.value = wallet.address; form.bot_token.value = wallet.bot_token; form.chat_id.value = wallet.chat_id; form.notification_url.value = wallet.notification_url || '';
            form.notification_api_key.value = wallet.notification_api_key || '';
        } else { form.title.textContent = '새 지갑 추가'; form.submitBtn.textContent = '추가하기'; }
    };
    const logout = () => { localStorage.removeItem('accessToken'); window.location.href = '/admin/login'; };
    if (path.includes('/admin') && !path.includes('/login')) {
        if (!token) { logout(); return; }
        let walletsCache = [];
        const refreshWallets = () => { api.getWallets().then(wallets => { walletsCache = wallets; ui.renderWallets(wallets); }).catch(console.error); };
        refreshWallets();
        document.getElementById('logout-btn')?.addEventListener('click', logout);
        form.form?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const walletId = form.walletId.value;
            const formData = {
                name: form.name.value, address: form.address.value, bot_token: form.bot_token.value, chat_id: form.chat_id.value,
                notification_url: form.notification_url.value, notification_api_key: form.notification_api_key.value,
            };
            const res = walletId ? await api.updateWallet(walletId, formData) : await api.addWallet(formData);
            if (res.ok) { setFormMode('add'); refreshWallets(); }
            else { const errData = await res.json(); form.errorMsg.textContent = errData.msg || '작업에 실패했습니다.'; }
        });
        ui.walletList?.addEventListener('click', (e) => {
            const target = e.target; const id = target.dataset.id;
            if (target.classList.contains('edit-btn')) { const walletToEdit = walletsCache.find(w => w.id == id); if (walletToEdit) { setFormMode('edit', walletToEdit); window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }); } }
            if (target.classList.contains('delete-btn')) { if (confirm('정말로 이 지갑을 삭제하시겠습니까?')) { api.deleteWallet(id).then(success => { if (success) { refreshWallets(); } else { alert('삭제에 실패했습니다.'); } }); } }
        });
    }
    if (path.includes('/login')) {
        document.getElementById('login-form')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value; const password = document.getElementById('password').value;
            const errorMsg = document.getElementById('error-message');
            try {
                const response = await fetch('/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
                if (!response.ok) throw new Error('아이디 또는 비밀번호가 잘못되었습니다.');
                const data = await response.json();
                localStorage.setItem('accessToken', data.access_token);
                window.location.href = '/admin';
            } catch (error) { errorMsg.textContent = error.message; }
        });
    }
});
