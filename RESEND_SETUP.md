# Configuration avec Resend (Recommandé)

Resend est un service d'email transactionnel moderne qui est **beaucoup plus fiable** que Mailo SMTP pour envoyer des emails programmatiquement.

## Avantages de Resend

✅ **Pas de blocage de sécurité** — pas de limite de tentatives
✅ **Plus fiable** — infrastructure dédiée aux emails transactionnels
✅ **API moderne** — pas de problèmes SSL/TLS complexes
✅ **Gratuit au départ** — 100 emails/jour gratuitement
✅ **Meilleur délivrabilité** — SPF/DKIM configurés automatiquement

## Étapes de configuration

### 1. Créer un compte Resend

1. Va sur https://resend.com
2. Crée un compte gratuitement
3. Confirme ton email

### 2. Générer une clé API

1. Dans le dashboard Resend, va dans **Settings** → **API Keys**
2. Crée une nouvelle clé API
3. Copie la clé (commence par `re_`)

### 3. Configurer le domaine d'envoi

**Option A: Utiliser un domaine de test (simple)**
- Resend te donne un domaine de test `onboard@resend.dev`
- Pour tester rapidement, utilise `RESEND_FROM=onboard@resend.dev`

**Option B: Ajouter ton propre domaine (recommandé)**
1. Dans Resend, va dans **Domains**
2. Ajoute ton domaine (ex: `mailo.com`)
3. Suis les instructions pour ajouter les enregistrements DNS
4. Une fois vérifié, configure `RESEND_FROM=noreply@mailo.com`

### 4. Mettre à jour ton `.env`

```env
EMAIL_BACKEND=resend
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
RESEND_FROM=noreply@mailo.com
```

**Important :** `RESEND_FROM` doit être une adresse **vérifiée** dans Resend. Pour commencer, utilise `onboard@resend.dev`.

### 5. Redémarrer le conteneur

```bash
docker-compose down
docker-compose up -d
```

## Vérifier que ça fonctionne

```bash
docker logs -f mailo-forwarder | grep -i "resend\|successfully\|forwarded"
```

Tu devrais voir :
```
📧 Backend: Resend (API-based, more reliable)
✅ Successfully forwarded via Resend: 'Subject' | From: sender@example.com
```

## FAQ

### Q: Je veux tester avec un domaine avant d'ajouter le mien ?
R: Utilise `RESEND_FROM=onboard@resend.dev` pour tester gratuitement.

### Q: Est-ce que les emails vont arriver dans les spams ?
R: Non, Resend gère automatiquement SPF/DKIM. Mais assure-toi que l'adresse d'envoi est vérifiée.

### Q: Combien coûte Resend ?
R: 
- **100 emails/jour gratuits** (sans carte de crédit)
- Puis 0,50$ pour 1000 emails (très pas cher)

### Q: Puis-je revenir à SMTP Mailo après ?
R: Oui, rechange `EMAIL_BACKEND=smtp` et redémarre.

## Dépannage

### Erreur: "RESEND_API_KEY not configured"
**Solution :** Ajoute `RESEND_API_KEY=re_xxx` dans `.env` et redémarre.

### Erreur: "RESEND_FROM not configured"
**Solution :** Ajoute `RESEND_FROM=onboard@resend.dev` dans `.env` et redémarre.

### Les emails ne s'envoient pas mais pas d'erreur
**Solution :** Vérifie que `RESEND_FROM` est une adresse **vérifiée** dans Resend.

## Support

- Docs Resend: https://resend.com/docs
- Dashboard Resend: https://dashboard.resend.com
