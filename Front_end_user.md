# 📄 PRD Supplement: User Selection & Identity Mapping

## 1. OBIETTIVO DELL'IMPLEMENTAZIONE
Sostituire la chiave API statica con un sistema di selezione utente dinamico. All'avvio, l'applicazione deve permettere all'utente di identificarsi scegliendo il proprio profilo, recuperando così la `X-API-KEY` corretta e i dati associati dal database.

---

## 2. WORKFLOW DI SELEZIONE UTENTE (UX)

### 2.1 Startup Sequence
1. **Verifica Sessione:** L'app controlla nel `localStorage` se esiste una chiave `active_user_session`.
2. **Schermata di Benvenuto (Login Visivo):** Se la sessione è assente, l'app mostra una griglia di profili recuperati dall'endpoint pubblico `/api/public/users`.
3. **Selezione:** L'utente clicca sulla propria foto/nome.
4. **Persistenza:** - La `X-API-KEY` viene salvata in `localStorage.setItem('auth_key', selected_user_key)`.
   - L'ID Utente viene salvato per filtrare i turni.
5. **Redirect:** L'utente viene indirizzato alla Dashboard principale.



---

## 3. SPECIFICHE TECNICHE FRONTEND

### 3.1 Componente `UserSelector.vue/jsx`
* **UI:** Una griglia responsive (2 o 3 colonne su mobile) contenente card utente.
* **Elementi Card:** * Immagine Profilo (Avatar circolare).
    * Nome Display.
* **Logica:**
    ```javascript
    async function selectUser(user) {
        localStorage.setItem('auth_key', user.api_key);
        localStorage.setItem('user_id', user.id);
        localStorage.setItem('user_name', user.name);
        window.location.href = '/dashboard';
    }
    ```

### 3.2 Intercettore API (Axios/Fetch)
Tutte le chiamate successive (Upload, Traffico, Get Shifts) devono includere dinamicamente la chiave:
```javascript
api.interceptors.request.use(config => {
    const token = localStorage.getItem('auth_key');
    if (token) {
        config.headers['X-API-KEY'] = token;
    }
    return config;
});