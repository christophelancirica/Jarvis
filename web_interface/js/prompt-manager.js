/**
 * prompt-manager.js - Gestionnaire des rôles/prompts
 */

class PromptManager {
    constructor() {
        this.roles = {};
        this.currentRole = 'assistant_general';
    }

    /**
     * Charge les rôles depuis le serveur
     */
    async loadRoles() {
        try {
            const response = await fetch('/api/roles'); // Doit correspondre à roles.json
            // Fallback si pas d'API dédiée, lire le JSON statique
            if (!response.ok) {
                 const staticResponse = await fetch('config/roles.json');
                 const data = await staticResponse.json();
                 this.roles = data.roles || {};
            } else {
                const data = await response.json();
                this.roles = data.roles || {};
            }

            this.populateUI();
            console.log('✅ Rôles chargés pour manager:', Object.keys(this.roles).length);
        } catch (error) {
            console.error('Erreur chargement rôles:', error);
        }
    }

    /**
     * Ouvre le gestionnaire (Tab Prompts)
     */
    openManager() {
        this.loadRoles();
        // Basculer l'onglet
        document.querySelectorAll('.settings-tab').forEach(tab => tab.classList.remove('active'));
        document.getElementById('settings-prompts').classList.add('active');
        document.getElementById('settings-prompts').style.display = 'block';

        // Cacher les autres (hack rapide pour l'intégration existante)
        document.getElementById('settings-llm').style.display = 'none';
    }

    /**
     * Remplit l'interface de gestion
     */
    populateUI() {
        const container = document.getElementById('roles-list-container');
        if (!container) return;

        container.innerHTML = '';

        Object.entries(this.roles).forEach(([id, role]) => {
            const card = this.createRoleCard(id, role);
            container.appendChild(card);
        });
    }

    createRoleCard(id, role) {
        const div = document.createElement('div');
        div.className = 'role-card';
        div.style.padding = '10px';
        div.style.marginBottom = '10px';
        div.style.backgroundColor = 'var(--bg-secondary)';
        div.style.borderRadius = '8px';
        div.style.display = 'flex';
        div.style.justifyContent = 'space-between';
        div.style.alignItems = 'center';

        div.innerHTML = `
            <div style="flex-grow: 1; margin-right: 10px;">
                <h4 style="margin: 0; color: var(--text-primary);">${role.name}</h4>
                <p style="margin: 5px 0 0; font-size: 0.8em; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 250px;">
                    ${role.description}
                </p>
            </div>
            <div style="display: flex; gap: 5px;">
                <button onclick="promptManager.editRole('${id}')" class="btn-secondary" style="padding: 5px 10px;">✏️</button>
                ${id !== 'assistant_general' ? `<button onclick="promptManager.deleteRole('${id}')" class="btn-danger" style="padding: 5px 10px;">🗑️</button>` : ''}
            </div>
        `;
        return div;
    }

    createNew() {
        this.editRole(null);
    }

    async editRole(id) {
        const role = id ? this.roles[id] : { name: '', description: '', system_prompt: '' };

        // Créer un modal simple d'édition à la volée
        const modalHtml = `
            <div id="role-editor-overlay" style="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.8);z-index:2000;display:flex;align-items:center;justify-content:center;">
                <div style="background:var(--bg-primary);padding:20px;border-radius:10px;width:90%;max-width:500px;border:1px solid var(--accent-color);">
                    <h3 style="margin-top:0;">${id ? 'Modifier' : 'Nouveau'} Rôle</h3>

                    <div class="setting-group">
                        <label>Nom:</label>
                        <input type="text" id="edit-role-name" value="${role.name}" style="width:100%;padding:8px;background:var(--bg-secondary);color:var(--text-primary);border:1px solid var(--border-color);">
                    </div>

                    <div class="setting-group">
                        <label>Description:</label>
                        <input type="text" id="edit-role-desc" value="${role.description}" style="width:100%;padding:8px;background:var(--bg-secondary);color:var(--text-primary);border:1px solid var(--border-color);">
                    </div>

                    <div class="setting-group">
                        <label>Prompt Système:</label>
                        <textarea id="edit-role-prompt" rows="6" style="width:100%;padding:8px;background:var(--bg-secondary);color:var(--text-primary);border:1px solid var(--border-color);">${role.system_prompt}</textarea>
                    </div>

                    <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:20px;">
                        <button onclick="document.getElementById('role-editor-overlay').remove()" class="btn-secondary">Annuler</button>
                        <button onclick="promptManager.saveRole('${id || ''}')" class="btn-success">Sauvegarder</button>
                    </div>
                </div>
            </div>
        `;

        const div = document.createElement('div');
        div.innerHTML = modalHtml;
        document.body.appendChild(div.firstElementChild);
    }

    async saveRole(originalId) {
        const name = document.getElementById('edit-role-name').value;
        if (!name) return alert('Le nom est requis');

        const id = originalId || 'role_' + Date.now();
        const role = {
            id: id,
            name: name,
            description: document.getElementById('edit-role-desc').value,
            system_prompt: document.getElementById('edit-role-prompt').value,
            temperature: 0.7,
            max_tokens: 1000
        };

        // Mise à jour locale
        this.roles[id] = role;

        // Sauvegarde serveur
        try {
            await fetch('/api/roles/save', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    roles: this.roles,
                    default_role: 'assistant_general'
                })
            });

            document.getElementById('role-editor-overlay').remove();
            this.populateUI();

            // Rafraîchir aussi le select principal
            if (window.loadRolesFromAPI) window.loadRolesFromAPI();

        } catch (e) {
            console.error(e);
            alert('Erreur sauvegarde: ' + e);
        }
    }

    async deleteRole(id) {
        if (!confirm('Supprimer ce rôle ?')) return;

        delete this.roles[id];

        try {
            await fetch('/api/roles/save', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    roles: this.roles,
                    default_role: 'assistant_general'
                })
            });
            this.populateUI();
            if (window.loadRolesFromAPI) window.loadRolesFromAPI();
        } catch (e) {
            console.error(e);
        }
    }
}

window.promptManager = new PromptManager();
console.log('📝 Prompt Manager initialisé');
