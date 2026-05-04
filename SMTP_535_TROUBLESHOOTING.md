# Erreur SMTP 535: Currently not available(2)

## Qu'est-ce que ça signifie ?

Le code 535 avec le message "Currently not available(2)" de Mailo n'est **pas une erreur de mot de passe classique**. C'est généralement un problème du serveur ou une restriction de sécurité.

## Causes probables et solutions

### 1. **Authentification depuis une nouvelle adresse IP** (TRÈS PROBABLE)
Mailo peut bloquer les connexions SMTP depuis des IPs jamais vues auparavant pour des raisons de sécurité.

**Solution :**
- Connectez-vous à https://www.mailo.com via un navigateur depuis votre IP actuelle
- Vérifiez les alertes de sécurité dans vos paramètres Mailo
- Attendez quelques minutes avant de relancer

### 2. **Mot de passe récemment changé**
Si vous avez changé votre mot de passe Mailo récemment, les clients SMTP peuvent ne pas être à jour.

**Solution :**
- Vérifiez que `IMAP_PASS` dans votre `.env` contient le **mot de passe actuel**
- Les applications nécessitent parfois 5-10 minutes après un changement de mot de passe

### 3. **Compte bloqué ou limites atteintes**
Mailo peut temporairement bloquer un compte en cas de nombreuses tentatives échouées.

**Solution :**
- Cessez les tentatives pendant 30 minutes
- Connectez-vous à https://www.mailo.com pour vérifier l'état du compte

### 4. **Format d'identifiant incorrect**
Mailo exige parfois l'**adresse e-mail complète** comme identifiant SMTP.

**Vérification :**
```
IMAP_USER=votre-adresse-complete@netc.fr
IMAP_PASS=votre_mot_de_passe
```

Assurez-vous que l'adresse est bien votre **adresse Mailo principale**, pas un alias.

### 5. **Mailo rejette les connexions non-TLS sur port 587**
Port 587 sans TLS/STARTTLS peut être refusé.

**Solution :**
- Essayez plutôt `SMTP_PORT=465` et `SMTP_TLS_MODE=ssl`
- Ou activez `SMTP_TLS_MODE=starttls` sur port 587

## Comment diagnostiquer

### Test manuel depuis votre machine
```bash
python3 << 'EOF'
import smtplib

SMTP_SERVER = 'mail.mailo.com'
SMTP_PORT = 465
SMTP_USER = 'votre-adresse@netc.fr'
SMTP_PASS = 'votre_mot_de_passe'

try:
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
        print(f"✅ Connexion établie: {server.getresponse()}")
        server.login(SMTP_USER, SMTP_PASS)
        print("✅ Authentification réussie!")
except smtplib.SMTPAuthenticationError as e:
    print(f"❌ Erreur auth {e.smtp_code}: {e.smtp_error}")
except Exception as e:
    print(f"❌ Erreur: {e}")
EOF
```

### Vérifier les logs du conteneur
```bash
docker logs -f mailo-forwarder | grep -i "smtp\|auth"
```

## Étapes à suivre

1. **Pause de 30 minutes** : arrêtez les tentatives
2. **Vérifiez votre compte** : connectez-vous à Mailo via navigateur
3. **Testez manuellement** : utilisez le script Python ci-dessus
4. **Vérifiez les identifiants** : adresse complète et mot de passe actuel
5. **Redémarrez** : `docker-compose down && docker-compose up -d`

## Référence
- Documentation Mailo: https://www.mailo.com/mailo/fr/mailo.php
- FAQ Mailo: https://faq.mailo.com/
