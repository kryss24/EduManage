# École — Application de gestion d'école primaire

Application web de gestion d'école primaire : élèves, classes, enseignants, matières, notes,
moyennes, bulletins PDF.

Stack : **React + Bootstrap (PWA)** · **Django + Django REST Framework** · **PostgreSQL** ·
authentification **JWT** · déploiement prévu sur **Render**.

Suivi du projet : Jira, projet `SCRUM`.

## Démarrage rapide (< 10 min)

### Prérequis

- [Docker](https://www.docker.com/) et Docker Compose
- Git

### Lancer le projet

```bash
cp .env.example .env
docker compose up --build
```

- API : http://localhost:8000/
- Health check : http://localhost:8000/api/health/ → `{"status": "ok"}`
- Admin Django (dev uniquement, désactivé en production) : http://localhost:8000/admin/
- Schéma OpenAPI (dev uniquement, `DEBUG=True`) : http://localhost:8000/api/schema/docs/
- Authentification : voir [`docs/api-auth.md`](docs/api-auth.md) (frontend) et
  [`docs/securite.md`](docs/securite.md) (règles, décisions de sécurité).

Le frontend React n'est pas encore branché sur l'API (voir [`frontend/README.md`](frontend/README.md)).

## Commandes utiles

```bash
# Lancer les tests backend (exigent PostgreSQL ; couverture >= 90% sur accounts/core)
docker compose run --rm backend pytest

# Lancer ruff (lint + format)
docker compose run --rm backend ruff check .
docker compose run --rm backend ruff format --check .

# Créer un superutilisateur Django
docker compose run --rm backend python manage.py createsuperuser

# Ouvrir un shell Django
docker compose run --rm backend python manage.py shell

# Ouvrir un shell dans le conteneur backend
docker compose run --rm backend bash

# Purger les refresh tokens expirés/mis en liste noire (à planifier, ex. cron quotidien)
docker compose run --rm backend python manage.py flushexpiredtokens

# Créer le super administrateur de départ (SUPERADMIN_EMAIL/SUPERADMIN_PASSWORD dans .env)
docker compose run --rm backend python manage.py bootstrap_superadmin
# Réinitialiser son mot de passe (ne le modifie jamais sans ce flag) :
docker compose run --rm backend python manage.py bootstrap_superadmin --reset-password
```

### Authentification JWT

Variables à définir dans `.env` (voir `.env.example` pour les valeurs
d'exemple et [`docs/securite.md`](docs/securite.md) pour le détail) :
`JWT_SIGNING_KEY` (dédiée, distincte de `SECRET_KEY`, ≥ 32 caractères en
production), `JWT_ACCESS_MINUTES`, `JWT_REFRESH_HOURS`, `JWT_ISSUER`,
`JWT_AUDIENCE`, `AUTH_COOKIE_SAMESITE`, `AUTH_COOKIE_SECURE`,
`NUM_PROXIES`, `SUPERADMIN_EMAIL`/`SUPERADMIN_PASSWORD`/
`SUPERADMIN_NOM`/`SUPERADMIN_PRENOM`.

En production, `bootstrap_superadmin` **n'est pas lancée automatiquement**
au démarrage (à la différence du développement, voir `docker-compose.yml`) :
lancez-la manuellement une fois après le premier déploiement, puis retirez
`SUPERADMIN_PASSWORD` de l'environnement de l'hébergeur.

### Cache partagé (throttling)

Le throttling DRF (protection contre la force brute et les abus) utilise un
cache en base de données, partagé entre tous les workers gunicorn (une
instance de cache mémoire par worker ne serait pas partagée). La table est
créée automatiquement au démarrage en développement
(`docker-compose.yml`) ; en production, lancez une fois :

```bash
python manage.py createcachetable
```

### Topologie de déploiement et cookies (important)

Le cahier des charges prévoit le frontend sur **Vercel** et l'API sur
**Render/Railway**, donc deux domaines différents. Un cookie cross-site
(`SameSite=None`) est bloqué par défaut par Safari et d'autres navigateurs,
ce qui casserait le rafraîchissement de session.

**Solution recommandée** : faire passer `/api/*` par le **même domaine**
que le frontend, via une réécriture (`rewrites` de Vercel vers l'URL
Render/Railway de l'API), ou des sous-domaines d'un même domaine racine
(`app.monsite.com` / `api.monsite.com` avec `AUTH_COOKIE_DOMAIN=.monsite.com`).
Avec cette topologie, utilisez `AUTH_COOKIE_SAMESITE=Lax` (ou `Strict`).

`AUTH_COOKIE_SAMESITE=None` (avec `AUTH_COOKIE_SECURE=True` obligatoire)
reste documenté comme option de dernier recours pour une topologie
réellement cross-site, mais n'est pas recommandé.

### Réinitialiser la base de données locale

Nécessaire après avoir récupéré SCRUM-7 si votre base avait déjà été
migrée avec le modèle utilisateur par défaut de Django (`auth.User`) :
le modèle personnalisé (`accounts.User`, `AUTH_USER_MODEL`) doit exister
avant la toute première migration.

```bash
docker compose down -v
docker compose up --build
```

### Données de démonstration

```bash
# Définir SEED_USER_PASSWORD dans .env (voir .env.example) avant de lancer :
docker compose run --rm backend python manage.py seed_demo_data

# Supprimer uniquement les données de démo (écoles "[DEMO] ...") :
docker compose run --rm backend python manage.py seed_demo_data --reset
```

Crée deux écoles `[DEMO] ...` avec années scolaires, classes, enseignants,
élèves, parents et notes, afin de pouvoir tester l'isolation entre
tenants. Idempotent (relancer la commande ne crée pas de doublons) et
refuse de s'exécuter avec `DEBUG=False` sauf `--force`.

## Structure du dépôt

```
ecole/
├── backend/     # API Django REST Framework
├── frontend/    # PWA React + Bootstrap (à venir)
├── docs/        # Cahier des charges, schémas, documentation
└── .github/     # Workflows CI, CODEOWNERS, template de PR
```

Voir [`docs/`](docs/) pour la documentation fonctionnelle et technique,
dont [`docs/modele-donnees.md`](docs/modele-donnees.md) (modèles,
schéma, décisions).

## Convention de branches et de commits

- Branches : `feature/SCRUM-12-description-courte`
- Commits : `SCRUM-12: message court`

Chaque PR doit référencer un ticket Jira (`SCRUM-xx`) et suivre le
[template de PR](.github/pull_request_template.md).
