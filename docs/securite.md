# Sécurité — règles, décisions et comment brancher un nouveau CRUD

Ce document est la référence interne (équipe backend) pour tout ce qui
touche à l'authentification, à l'isolation multi-tenant et aux
permissions. Le guide orienté frontend est [`docs/api-auth.md`](api-auth.md).

## 1. Isolation multi-tenant

**Règle absolue : une requête ne doit jamais pouvoir lire ni modifier une
donnée d'une autre école que la sienne.**

- Pour tout rôle sauf `SUPER_ADMIN`, l'école d'une requête est **toujours**
  `request.user.school` — jamais une valeur envoyée par le client (en-tête,
  paramètre, corps). Voir `apps.core.tenancy.get_request_school`.
- Un `SUPER_ADMIN` n'a pas d'école propre : il doit désigner l'école
  consultée via l'en-tête `X-School-Id` (UUID d'une école existante et
  active). Chaque accès réussi est journalisé (`superadmin_tenant_access`).
- Un objet d'une autre école renvoie **404**, jamais 403 : un 403
  confirmerait son existence à un attaquant qui devine des identifiants.

### Comment brancher un nouveau CRUD (élèves, classes, notes...)

```python
from rest_framework.viewsets import ModelViewSet
from apps.core.tenancy import TenantModelSerializer, TenantScopedViewSetMixin
from apps.accounts.permissions import HasFeatureAccess


class ClassroomSerializer(TenantModelSerializer):
    class Meta:
        model = Classroom
        fields = ["id", "school", "name", "level", "academic_year"]
        # `school` est déjà en lecture seule via TenantModelSerializer.


class ClassroomViewSet(TenantScopedViewSetMixin, ModelViewSet):
    queryset = Classroom.objects.all()
    serializer_class = ClassroomSerializer
    permission_classes = [IsAuthenticated, SchoolIsActive, HasFeatureAccess]
    feature = "classrooms"  # clé de apps.accounts.features.FEATURE_MATRIX
```

Ce qui est automatique avec ce mixin :

- `get_queryset()` filtre sur l'école de la requête (`for_school(...)`).
- `perform_create()` injecte cette même école, quoi que le corps envoie.
- `get_object()` (donc `retrieve`/`update`/`destroy`) renvoie 404 pour un
  objet d'une autre école, puisqu'il n'est pas dans le queryset filtré.

Si une relation doit pointer vers un autre `TenantModel` (ex. `Classroom`
pour un `Enrollment`), utilisez `TenantPrimaryKeyRelatedField` plutôt que
`PrimaryKeyRelatedField` : le queryset de ce champ est filtré sur l'école de
la requête, donc impossible de référencer un objet d'une autre école
(erreur 400 générique, pas de fuite d'existence).

Pour restreindre la visibilité **au sein** d'une école selon le rôle
(parent → ses enfants, enseignant → ses classes...), réutilisez
`apps.accounts.scoping.students_visible_to`/`classrooms_visible_to` dans
`get_queryset()` plutôt que de dupliquer cette logique.

## 2. Matrice de permissions

Source unique : `apps.accounts.features.FEATURE_MATRIX`. Niveaux : `-`
(aucun), `L` (lecture), `E` (écriture), `A` (administration) ; `A` ⊃ `E` ⊃
`L`. Reproduite ici pour référence rapide (voir le fichier pour la version
faisant foi) :

| Fonctionnalité | SUPER_ADMIN | SCHOOL_ADMIN | TEACHER | PARENT | CASHIER |
|---|---|---|---|---|---|
| `tenants` | A | - | - | - | - |
| `school_settings` | A | A | - | - | - |
| `classrooms` | A | A | L | - | - |
| `students` | A | A | L | L | - |
| `teachers` | A | A | L | - | - |
| `grades` | A | A | E | - | - |
| `report_cards` | A | A | L | L | - |
| `tuition_payments` | A | A | - | L | E |
| `teacher_salaries` | A | A | - | - | E |
| `financial_reports` | A | A | - | - | L |
| `communications` | A | A | E | L | - |

`HasFeatureAccess` applique cette matrice : une vue sans attribut `feature`
refuse l'accès à **tout le monde**, y compris un `SUPER_ADMIN` (échec
fermé — c'est un bug de la vue à corriger, jamais un accès à accorder par
défaut). Le niveau requis dépend par défaut de la méthode HTTP (lecture =
`L`, écriture = `E`) ; surchargeable par action via
`feature_required_levels`.

## 3. Authentification JWT

- Access : 10 min (`JWT_ACCESS_MINUTES`). Refresh : 8 h
  (`JWT_REFRESH_HOURS`), avec rotation à chaque usage et mise en liste
  noire de l'ancien jeton (`ROTATE_REFRESH_TOKENS`/`BLACKLIST_AFTER_ROTATION`).
  Une rotation redonne 8h : c'est ce qui implémente la règle « session
  expirée après 8h d'inactivité » du cahier des charges.
- Clé de signature (`JWT_SIGNING_KEY`) **dédiée**, distincte de
  `SECRET_KEY` : une fuite de l'une ne compromet pas l'autre. `ISSUER`/
  `AUDIENCE` vérifiés à chaque décodage.
- **Le token n'est jamais une source de vérité pour le rôle ou l'école** :
  `JWTAuthentication` recharge l'utilisateur depuis la base à chaque
  requête (claim `user_id` uniquement), et `SchoolIsActive` vérifie
  `user.school.is_active` à chaque requête. Un token encore valide pour un
  compte ou une école désactivés échoue immédiatement.
- Identifiants UUID : `USER_ID_FIELD`/`USER_ID_CLAIM` configurés ; le claim
  est toujours une chaîne (un UUID n'est pas nativement sérialisable JSON).
- Refresh posé en cookie `HttpOnly`, `Secure` (sauf dev),
  `Path=/api/auth/`, `SameSite` piloté par `AUTH_COOKIE_SAMESITE`. Protection
  CSRF de `refresh`/`logout` par vérification de l'en-tête `Origin`.
- Hachage : Argon2 (nouveaux mots de passe), BCryptSHA256 en second rang
  (pour vérifier d'anciens hash bcrypt sans forcer leur migration
  immédiate). Validateurs : longueur minimale 12, similarité avec les
  attributs du compte, mots de passe courants, entièrement numérique.

## 4. Force brute et énumération

- **django-axes** verrouille un couple (email, IP) après 5 échecs
  consécutifs, pendant 15 minutes, réinitialisé à la première connexion
  réussie. Intégré directement dans `LoginView` (pas via
  `AUTHENTICATION_BACKENDS`/vue Django classique) : voir
  `AxesProxyHandler.is_allowed`/`user_login_failed`/`user_logged_in` dans
  `apps/accounts/views.py`.
  - `AXES_DISABLE_ACCESS_LOG = True` : le journal `AccessLog` d'axes force
    la création d'une session Django à chaque connexion (pour corréler
    connexion/déconnexion par session), ce qui est à la fois inutile et
    indésirable pour une API JWT sans état. Le verrouillage lui-même
    (`AccessAttempt`) n'en dépend pas.
- **Throttling DRF** (login 5/min/IP, refresh 30/min, anonyme 20/min,
  authentifié 120/min) sur un cache **partagé** entre workers (base de
  données, voir `createcachetable` dans le README) : indispensable dès
  qu'il y a plus d'un worker gunicorn, sans quoi chaque worker aurait son
  propre compteur.
- Message de connexion **strictement identique** (`"Identifiants
  invalides."`, même code HTTP) que le compte n'existe pas, que le mot de
  passe soit faux, ou que le compte/l'école soit désactivé. Voir
  `apps.accounts.views._authenticate` : même en l'absence d'utilisateur,
  `User().set_password(password)` fait tourner le hasher pour atténuer une
  différence de temps de réponse exploitable (recette standard de
  `django.contrib.auth.backends.ModelBackend`).

## 5. Audit et journalisation

- `apps.core.audit.record_audit(request, action, ...)` écrit dans
  `core.AuditLog` (immuable : ni modification ni suppression possible,
  voir le modèle). Utilisé pour les connexions réussies, déconnexions,
  changements de mot de passe, verrouillages, accès `SUPER_ADMIN` à une
  école, bootstrap du superadmin.
- Les tentatives échouées (mauvais mot de passe, compte inconnu) vont dans
  le logger `security`, **jamais** dans `AuditLog` (on ne sait pas toujours
  à quel utilisateur réel elles correspondent) — et l'email y est
  systématiquement masqué (`apps.core.audit.mask_email`, ex.
  `j******n@example.com`).
- **Jamais** de mot de passe, jeton ou cookie dans un log ou dans
  `AuditLog.metadata`.
- Piège de `logging` à connaître : les clés `extra={...}` d'un appel de
  logger ne doivent jamais recouper les attributs réservés de
  `logging.LogRecord` (`created`, `message`, `name`, `args`...), sous peine
  de `KeyError` au moment même de journaliser l'évènement. C'est le bug
  corrigé dans `bootstrap_superadmin` (clé `created` → renommée
  `account_created`) ; `apps.core.logging.JSONFormatter` documente la
  liste complète des attributs réservés.

## 6. Durcissement général

- `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated, SchoolIsActive]` : échec
  fermé par défaut. Seules routes publiques : `health`, `login`, `refresh`.
- Gestionnaire d'exceptions DRF (`apps.core.exceptions.exception_handler`) :
  toute exception imprévue devient une 500 générique côté client, journalisée
  côté serveur avec sa trace complète.
- En-têtes : HSTS, `X-Content-Type-Options: nosniff`, `X-Frame-Options:
  DENY`, `Referrer-Policy: no-referrer`, `Permissions-Policy` restrictive,
  CSP `default-src 'none'` sur les routes `/api/*` (une API ne sert jamais
  de HTML interactif).
- Admin Django désactivé en production (`ADMIN_ENABLED`), schéma OpenAPI
  (`drf-spectacular`) monté uniquement si `DEBUG=True`.
- `config.settings.prod` **échoue au chargement** (`ImproperlyConfigured`,
  donc au tout premier `manage.py`/démarrage gunicorn) si : `DEBUG=True`,
  `CORS_ALLOWED_ORIGINS` vide ou `*`, `JWT_SIGNING_KEY` absente/trop
  courte/égale à `SECRET_KEY`, ou cookies non sécurisés sans
  `AUTH_COOKIE_ALLOW_INSECURE=True` explicite.

## 7. Ce qui reste hors périmètre (SCRUM-8)

CRUD métier, gestion des comptes par les admins (création/désactivation
d'utilisateurs via l'API), mot de passe oublié, 2FA, Row-Level Security
PostgreSQL, finance, notes. Ces tickets devront réutiliser le socle
ci-dessus (`TenantScopedViewSetMixin`, `HasFeatureAccess`, `scoping.py`)
plutôt que le redévelopper.
