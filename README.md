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
- Admin Django : http://localhost:8000/admin/

Le frontend React n'est pas encore en place (voir [`frontend/README.md`](frontend/README.md)).

## Commandes utiles

```bash
# Lancer les tests backend
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
```

## Structure du dépôt

```
ecole/
├── backend/     # API Django REST Framework
├── frontend/    # PWA React + Bootstrap (à venir)
├── docs/        # Cahier des charges, schémas, documentation
└── .github/     # Workflows CI, CODEOWNERS, template de PR
```

Voir [`docs/`](docs/) pour la documentation fonctionnelle et technique.

## Convention de branches et de commits

- Branches : `feature/SCRUM-12-description-courte`
- Commits : `SCRUM-12: message court`

Chaque PR doit référencer un ticket Jira (`SCRUM-xx`) et suivre le
[template de PR](.github/pull_request_template.md).
