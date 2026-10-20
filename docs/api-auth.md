# API d'authentification — guide frontend

Ce document décrit `/api/auth/*` pour l'équipe frontend. Il ne couvre pas
les futurs CRUD métier (élèves, classes...), qui suivront le même socle
d'autorisation (voir [`docs/securite.md`](securite.md)).

## Vue d'ensemble

- **Base URL** : `/api/auth/`
- **Access token** : renvoyé dans le corps JSON de `login`/`refresh`, à
  garder **en mémoire** côté client (jamais dans `localStorage`,
  `sessionStorage` ou un cookie non-`HttpOnly`). Il est perdu au rechargement
  de la page : rappeler `POST /api/auth/refresh/` au démarrage de
  l'application pour retrouver une session active.
- **Refresh token** : jamais exposé en JSON. Posé en cookie `HttpOnly`
  (`edumanage_refresh`) par `login`/`refresh`, avec `Path=/api/auth/` :
  le navigateur ne l'envoie qu'aux appels vers ce préfixe.
- **En-tête `Authorization`** : `Authorization: Bearer <access_token>` sur
  toutes les routes protégées.
- **`credentials: "include"`** (fetch) ou `withCredentials: true` (axios)
  sont nécessaires sur tous les appels à `/api/auth/*` pour que le cookie de
  refresh soit envoyé/reçu.

## Endpoints

### `POST /api/auth/login/`

Requête :

```json
{ "email": "admin@ecole-demo.test", "password": "••••••••••••" }
```

Réponse `200` (et pose le cookie `edumanage_refresh`) :

```json
{
  "access": "eyJhbGciOi...",
  "user": {
    "id": "7e6a08b5-7f97-47fa-bbae-aa3f964aac64",
    "email": "admin@ecole-demo.test",
    "first_name": "École",
    "last_name": "Administrateur d'école",
    "role": "SCHOOL_ADMIN"
  },
  "school": {
    "id": "f54bd3c0-f39c-4b70-8a8c-ca439358ee31",
    "name": "École Les Palmiers",
    "currency": "XAF",
    "timezone": "Africa/Douala"
  },
  "permissions": {
    "tenants": "-",
    "school_settings": "A",
    "classrooms": "A",
    "students": "A",
    "teachers": "A",
    "grades": "A",
    "report_cards": "A",
    "tuition_payments": "A",
    "teacher_salaries": "A",
    "financial_reports": "A",
    "communications": "A"
  }
}
```

- `school` est `null` pour un `SUPER_ADMIN` (aucune école de rattachement).
- `permissions` est le dictionnaire `{fonctionnalité: niveau}` du rôle de
  l'utilisateur (`-`/`L`/`E`/`A`, voir [`docs/securite.md`](securite.md)) :
  utilisez-le pour afficher/masquer les sections de l'interface, en plus des
  réponses 403 du serveur (qui restent la seule source de vérité réelle).
- **`401`** : `{"detail": "Identifiants invalides."}` — identique que le
  compte n'existe pas, que le mot de passe soit faux, que le compte ou
  l'école soit désactivé. Ne jamais tenter de distinguer ces cas côté UI.
- **`429`** : verrouillage (5 échecs sur 15 minutes pour ce couple
  identifiant/IP) ou throttling (5 tentatives/minute par IP). Même message
  générique ; affichez un message neutre type « trop de tentatives,
  réessayez plus tard ».

### `POST /api/auth/refresh/`

Aucun corps. Lit le cookie `edumanage_refresh`, renvoie un nouvel `access`
et repose un nouveau cookie (rotation : l'ancien refresh devient invalide).

```json
{ "access": "eyJhbGciOi..." }
```

- **`401`** : pas de cookie, cookie expiré/invalide/déjà utilisé, ou
  compte/école désactivé entre-temps → renvoyer l'utilisateur à l'écran de
  connexion.
- **`403`** : en-tête `Origin` absent ou non autorisé (voir plus bas).
- Appelez cet endpoint **proactivement** avant l'expiration de l'access
  (10 min par défaut) pour une session fluide, et systématiquement au
  chargement de l'application (voir « Access token » ci-dessus).

### `POST /api/auth/logout/`

Nécessite un access token valide (`Authorization: Bearer ...`). Met le
refresh en liste noire et supprime le cookie. Réponse `204`.

### `GET /api/auth/me/`

Nécessite un access token valide. Même forme de réponse que `login`, sans
`access`. Utile pour réhydrater l'état de session après un `refresh` réussi.

### `POST /api/auth/change-password/`

```json
{ "old_password": "••••••••••••", "new_password": "••••••••••••••" }
```

Réponse `204`. Invalide **tous** les refresh tokens de l'utilisateur
(déconnexion de tous les appareils) : après un changement de mot de passe,
l'application doit rediriger vers l'écran de connexion.

`400` si l'ancien mot de passe est incorrect ou si le nouveau ne respecte
pas les règles (longueur minimale 12, pas trop proche des informations du
compte, pas un mot de passe courant, pas entièrement numérique).

## En-tête `Origin` (protection CSRF des endpoints à cookie)

`refresh` et `logout` lisent un cookie : sans protection supplémentaire, un
site tiers pourrait forcer le navigateur à les appeler. Ces deux routes
exigent donc un en-tête `Origin` figurant dans `CORS_ALLOWED_ORIGINS` côté
serveur, sinon `403`.

- Un navigateur envoie `Origin` automatiquement sur les requêtes
  cross-origin : rien à faire côté frontend si vous appelez l'API depuis le
  navigateur.
- **Un client comme Postman/Insomnia doit envoyer l'en-tête `Origin` à la
  main** (ex. `Origin: http://localhost:3000`), sinon ces deux routes
  renverront systématiquement `403`.

## En-tête `X-School-Id` (réservé aux super administrateurs)

Un `SUPER_ADMIN` n'a pas d'école de rattachement : toute route à portée
d'école exige l'en-tête `X-School-Id: <uuid>` pour préciser l'école
consultée. Les autres rôles n'ont pas à (et ne peuvent pas) l'utiliser :
il est silencieusement ignoré pour eux, leur école reste toujours celle de
leur compte.

- Absent pour un `SUPER_ADMIN` → `400`.
- UUID inconnu ou école désactivée → `400`.
- Chaque usage réussi est journalisé côté serveur (audit).

## Codes d'erreur

| Code  | Signification |
|-------|----------------|
| `400` | Requête malformée, ou `X-School-Id` manquant/invalide pour un `SUPER_ADMIN`. |
| `401` | Non authentifié, ou authentifié avec un token invalide/expiré. |
| `403` | Authentifié mais sans le droit requis, ou `Origin` non autorisé sur `refresh`/`logout`. |
| `404` | Objet inexistant **ou** appartenant à une autre école (jamais de 403 dans ce second cas, pour ne pas révéler son existence). |
| `429` | Verrouillage du compte ou throttling. |

## Démarrage de session côté frontend (résumé)

1. Au chargement de l'application : `POST /api/auth/refresh/`.
   - `200` → stocker `access` en mémoire, appeler `GET /api/auth/me/` pour
     l'état utilisateur (ou réutiliser celui déjà renvoyé si vous l'avez
     mis en cache côté client pour cette session).
   - `401` → afficher l'écran de connexion.
2. Sur chaque appel API protégé : poser `Authorization: Bearer <access>`.
3. Sur une réponse `401` d'un appel protégé (access expiré) : tenter un
   `refresh`, puis rejouer l'appel une fois ; si le `refresh` échoue aussi,
   déconnecter.
