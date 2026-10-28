# API du calendrier scolaire et de la structure des classes (`/api/academics/`)

Documentation de référence pour les développeurs frontend consommant les endpoints de l'application Academics (ticket **SCRUM-10**).

---

## 1. Vue d'ensemble et principes généraux

- **Préfixe des routes** : `/api/academics/`
- **Authentification** : Requise (`Authorization: Bearer <access_token>`).
- **Isolation multi-tenant** : Les données sont automatiquement filtrées sur l'école de l'utilisateur connecté (`request.user.school`). Pour un `SUPER_ADMIN`, l'école active doit être spécifiée via l'en-tête `X-School-Id: <uuid>`. Tout objet appartenant à une autre école renvoie un code **404**.
- **Pagination** : Standard sur tous les endpoints de liste (`count`, `next`, `previous`, `results`).
  - Paramètres de requête : `?page=1&page_size=20` (plafonnée à un maximum de `100`).
- **Tris et filtres** : Strictement limités à des listes blanches. Tout champ de tri non autorisé renvoie une erreur `400`.
- **Format des erreurs** :
  - `400 Bad Request` : Erreur de validation par champ, ex. `{"name": ["Ce nom est déjà utilisé."]}`.
  - `401 Unauthorized` : Jeton manquant, expiré ou invalide.
  - `403 Forbidden` : Accès refusé par la matrice des permissions.
  - `404 Not Found` : Ressource inexistante ou appartenant à une autre école.
  - `409 Conflict` : Conflit métier (ex. suppression protégée, modification d'une ressource liée à une année archivée).

---

## 2. Matrice des droits par rôle

Tous les endpoints de ce module exigent la fonctionnalité `classrooms`.

| Rôle | Niveau de droit | Opérations autorisées |
|---|---|---|
| `SUPER_ADMIN` | Administration (**A**) | Lecture, Écriture, Suppression, Actions métier (`activate`, `archive`, `generate-sequences`) |
| `SCHOOL_ADMIN` | Administration (**A**) | Lecture, Écriture, Suppression, Actions métier (`activate`, `archive`, `generate-sequences`) |
| `TEACHER` | Lecture (**L**) | Lecture de toutes les années, séquences, niveaux et du contexte. **Lecture uniquement de ses propres classes** (auxquelles il est affecté). Écriture et suppression interdites (403). |
| `PARENT` | Aucun (**-**) | Accès interdit (403) |
| `CASHIER` | Aucun (**-**) | Accès interdit (403) |

> [!NOTE]
> **Remarque pour le futur** : Le caissier et le parent n'ont actuellement aucun accès aux années scolaires et classes dans la matrice de permissions `classrooms`. Ce point sera réévalué lors du développement des modules de facturation/scolarité (finance) et de l'espace parent.

---

## 3. Chargement initial recommandé : Contexte scolaire

### `GET /api/academics/context/`
Permet au frontend de charger en un seul appel l'état actif de l'établissement dès l'ouverture de l'application.

- **Droit minimal** : Lecture (**L**) — accessible à `TEACHER`, `SCHOOL_ADMIN`, `SUPER_ADMIN`.
- **Réponse 200 OK** :
```json
{
  "active_year": {
    "id": "e7b0a3c2-4f11-477b-8919-623c21a1f592",
    "label": "2025-2026",
    "start_date": "2025-09-01",
    "end_date": "2026-06-30",
    "is_active": true,
    "is_archived": false,
    "created_at": "2025-08-15T09:00:00Z",
    "updated_at": "2025-08-15T09:00:00Z"
  },
  "sequences": [
    {
      "id": "1b5d386d-318e-4a6f-b258-f58c7e974e64",
      "academic_year": "e7b0a3c2-4f11-477b-8919-623c21a1f592",
      "number": 1,
      "trimester": 1,
      "start_date": "2025-09-01",
      "end_date": "2025-10-17"
    },
    {
      "id": "2c6e497e-429f-5b7a-c369-a69d8f085f75",
      "academic_year": "e7b0a3c2-4f11-477b-8919-623c21a1f592",
      "number": 2,
      "trimester": 1,
      "start_date": "2025-10-20",
      "end_date": "2025-11-28"
    }
  ],
  "current_sequence": {
    "id": "1b5d386d-318e-4a6f-b258-f58c7e974e64",
    "academic_year": "e7b0a3c2-4f11-477b-8919-623c21a1f592",
    "number": 1,
    "trimester": 1,
    "start_date": "2025-09-01",
    "end_date": "2025-10-17"
  },
  "levels": [
    {"id": "c1f7a111-...", "name": "SIL", "order": 1},
    {"id": "c2f7a222-...", "name": "CP", "order": 2}
  ]
}
```
- **Règles métier** :
  - `active_year` vaut `null` si aucune année scolaire n'est actuellement activée dans l'école.
  - `current_sequence` vaut `null` si aucune séquence de l'année active ne couvre la date du jour (calculée dans le fuseau horaire de l'école `school.timezone`, par ex. en période de congés/vacances).

---

## 4. Années scolaires (`/api/academics/years/`)

### Endpoints
| Méthode | Route | Description | Droit |
|---|---|---|---|
| `GET` | `/api/academics/years/` | Liste des années scolaires | L |
| `POST` | `/api/academics/years/` | Création d'une année scolaire | E |
| `GET` | `/api/academics/years/{id}/` | Détail d'une année scolaire | L |
| `PATCH` | `/api/academics/years/{id}/` | Modification d'une année scolaire | E |
| `DELETE` | `/api/academics/years/{id}/` | Suppression d'une année | A |
| `POST` | `/api/academics/years/{id}/activate/` | Activation de l'année | A |
| `POST` | `/api/academics/years/{id}/archive/` | Archivage de l'année | A |
| `POST` | `/api/academics/years/{id}/generate-sequences/` | Génération en lot des 6 séquences | A |

### Champs du modèle
- `id` (UUID, lecture seule)
- `label` (string, max 50 car., obligatoire) : Libellé unique par école, insensible à la casse (ex. `"2025-2026"`).
- `start_date` (date `YYYY-MM-DD`, obligatoire)
- `end_date` (date `YYYY-MM-DD`, obligatoire) : Doit être postérieure à `start_date`. Ne doit pas chevaucher une autre année de la même école.
- `is_active` (booléen, lecture seule) : Modifiable uniquement via `/activate/`.
- `is_archived` (booléen, lecture seule) : Modifiable uniquement via `/archive/`.
- `created_at`, `updated_at` (lecture seule)

### Filtres et recherche
- `?is_active=true|false`
- `?is_archived=true|false`
- `?search=2025` (recherche sur `label`)
- `?ordering=start_date` ou `?ordering=-label` (liste blanche : `start_date`, `label`)

### Actions métier

#### 1. Activer une année (`POST /years/{id}/activate/`)
- Rend l'année active (`is_active = true`) et désactive de façon atomique l'ancienne année active de l'établissement.
- **Erreurs** :
  - `409 Conflict` si l'année est archivée.

#### 2. Archiver une année (`POST /years/{id}/archive/`)
- Marque l'année comme archivée (`is_archived = true`).
- **Erreurs** :
  - `409 Conflict` si l'année est encore active : message `"Impossible d'archiver l'année scolaire active. Veuillez activer d'abord une autre année scolaire."`.
- **Règle Année Archivée** : Une fois archivée, l'année devient en **lecture seule stricte**. Toute tentative de modification (`PATCH`), suppression (`DELETE`), ajout de séquence ou de classe renvoie `409 Conflict` avec `{"code": "year_archived"}`.

#### 3. Génération des séquences (`POST /years/{id}/generate-sequences/`)
Crée les 6 séquences de l'année scolaire en une transaction atomique.
- **Corps de la requête** : Liste JSON d'exactement 6 périodes chronologiques :
```json
[
  {"start_date": "2025-09-01", "end_date": "2025-10-17"},
  {"start_date": "2025-10-20", "end_date": "2025-11-28"},
  {"start_date": "2025-12-01", "end_date": "2026-01-23"},
  {"start_date": "2026-01-26", "end_date": "2026-03-06"},
  {"start_date": "2026-03-09", "end_date": "2026-04-24"},
  {"start_date": "2026-04-27", "end_date": "2026-06-12"}
]
```
- **Réponse 201 Created** : Liste des 6 séquences créées avec `trimester` calculé.
- **Erreurs** :
  - `400 Bad Request` si la liste ne compte pas exactement 6 éléments ou si une plage est invalide (le message d'erreur mentionne le numéro de séquence en cause).
  - `409 Conflict` si l'année possède déjà des séquences ou si elle est archivée.

#### 4. Suppression (`DELETE /years/{id}/`)
- **Erreurs** :
  - `409 Conflict` (`year_has_dependencies`) si des classes ou séquences sont rattachées à l'année.

---

## 5. Séquences scolaires (`/api/academics/sequences/`)

### Endpoints
| Méthode | Route | Description | Droit |
|---|---|---|---|
| `GET` | `/api/academics/sequences/` | Liste des séquences | L |
| `POST` | `/api/academics/sequences/` | Création d'une séquence | E |
| `GET` | `/api/academics/sequences/{id}/` | Détail d'une séquence | L |
| `PATCH` | `/api/academics/sequences/{id}/` | Modification d'une séquence | E |
| `DELETE` | `/api/academics/sequences/{id}/` | Suppression d'une séquence | A |

### Champs du modèle
- `id` (UUID, lecture seule)
- `academic_year` (UUID, obligatoire à la création, **immuable** ensuite)
- `number` (entier 1 à 6, obligatoire) : Unique par année scolaire.
- `trimester` (entier 1 à 3, lecture seule) : Calculé automatiquement selon la formule `(number + 1) // 2`.
  - Séquences 1 et 2 -> Trimestre 1
  - Séquences 3 et 4 -> Trimestre 2
  - Séquences 5 et 6 -> Trimestre 3
- `start_date` (date, obligatoire)
- `end_date` (date, obligatoire) : Postérieure à `start_date`, comprise dans l'année scolaire, sans chevauchement, et strictement cohérente avec l'ordre chronologique des autres séquences de l'année.

### Filtres et tri
- `?academic_year=<uuid>`
- `?number=1`
- `?ordering=number` ou `?ordering=start_date` (liste blanche : `number`, `start_date`)

### Suppression (`DELETE /sequences/{id}/`)
- `409 Conflict` (`sequence_has_grades`) si des notes sont enregistrées sur cette séquence.

---

## 6. Niveaux (`/api/academics/levels/`)

### Endpoints
| Méthode | Route | Description | Droit |
|---|---|---|---|
| `GET` | `/api/academics/levels/` | Liste des niveaux | L |
| `POST` | `/api/academics/levels/` | Création d'un niveau | E |
| `GET` | `/api/academics/levels/{id}/` | Détail d'un niveau | L |
| `PATCH` | `/api/academics/levels/{id}/` | Modification d'un niveau | E |
| `DELETE` | `/api/academics/levels/{id}/` | Suppression d'un niveau | A |

### Champs du modèle
- `id` (UUID, lecture seule)
- `name` (string, max 50 car., obligatoire) : Unique par école, insensible à la casse (ex. `"SIL"`, `"CP"`).
- `order` (entier positif, optionnel à la création) : Unique par école. S'il n'est pas fourni, le système attribue automatiquement `max(order) + 1`.

### Filtres et tri
- `?ordering=order` ou `?ordering=name` (liste blanche : `order`, `name`)

### Suppression (`DELETE /levels/{id}/`)
- `409 Conflict` (`level_has_classrooms`) si des classes sont rattachées à ce niveau.

---

## 7. Classes (`/api/academics/classrooms/`)

### Endpoints
| Méthode | Route | Description | Droit |
|---|---|---|---|
| `GET` | `/api/academics/classrooms/` | Liste des classes | L |
| `POST` | `/api/academics/classrooms/` | Création d'une classe | E |
| `GET` | `/api/academics/classrooms/{id}/` | Détail d'une classe | L |
| `PATCH` | `/api/academics/classrooms/{id}/` | Modification d'une classe | E |
| `DELETE` | `/api/academics/classrooms/{id}/` | Suppression d'une classe | A |

### Champs du modèle
- `id` (UUID, lecture seule)
- `academic_year` (UUID, obligatoire à la création, **immuable** ensuite)
- `level` (UUID, obligatoire, modifiable)
- `name` (string, max 100 car., obligatoire) : Unique par année scolaire, insensible à la casse (ex. `"SIL A"`).
- `academic_year_label` (string, lecture seule)
- `level_name` (string, lecture seule)
- `students_count` (entier, lecture seule) : Nombre d'inscriptions d'élèves enregistrées dans cette classe.

### Visibilité selon le rôle
- **`SCHOOL_ADMIN` & `SUPER_ADMIN`** : Voient toutes les classes de l'école.
- **`TEACHER`** : Voit **uniquement** les classes auxquelles il est explicitement affecté. L'accès à une autre classe renvoie **404**.
- **`PARENT` & `CASHIER`** : Accès refusé (**403**).

### Filtres et tri
- `?academic_year=<uuid>`
- `?level=<uuid>`
- `?search=SIL` (recherche sur `name`)
- `?ordering=name` ou `?ordering=level__order` (liste blanche : `name`, `level__order`)

### Suppression (`DELETE /classrooms/{id}/`)
- `409 Conflict` (`classroom_has_dependencies`) si la classe possède des inscriptions, des matières, des affectations d'enseignants ou des notes.

---

## 8. Codes d'erreurs et exemples

### Erreur 400 (Validation de champ)
```json
{
  "name": [
    "Une classe portant ce nom existe déjà pour cette année scolaire."
  ]
}
```

### Erreur 400 (Tri non autorisé)
```json
{
  "ordering": "Le champ de tri 'hacked' n'est pas autorisé."
}
```

### Erreur 409 (Année archivée)
```json
{
  "detail": "Cette année scolaire est archivée et ne peut plus être modifiée.",
  "code": "year_archived"
}
```

### Erreur 409 (Suppression protégée avec dépendances)
```json
{
  "detail": "Impossible de supprimer cette classe car des ressources en dépendent (inscriptions, matières, affectations ou notes).",
  "code": "classroom_has_dependencies"
}
```
