"""Vues d'authentification JWT.

Le refresh token ne quitte jamais le corps JSON des réponses : il est posé
en cookie `HttpOnly` par `set_refresh_cookie`. `login`/`refresh` sont les
seules routes publiques de ce module (hors `health`) ; `refresh`/`logout`
exigent un en-tête `Origin` de confiance (protection CSRF des endpoints à
cookie, ces derniers n'étant pas protégés par le jeton CSRF habituel
puisqu'ils sont appelés par un client API, pas par un formulaire HTML).
"""

from axes.handlers.proxy import AxesProxyHandler
from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.accounts.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    build_auth_payload,
)
from apps.accounts.token_utils import blacklist_all_outstanding_tokens, register_outstanding_token
from apps.core.audit import log_security_event, mask_email, record_audit

GENERIC_LOGIN_ERROR = {"detail": "Identifiants invalides."}
GENERIC_AUTH_ERROR = {"detail": "Authentification invalide."}


def _check_trusted_origin(request):
    """Lève 403 si `Origin` est absent ou n'est pas une origine autorisée.

    Un client comme Postman doit envoyer l'en-tête `Origin` à la main : voir
    `docs/api-auth.md`.
    """
    origin = request.headers.get("Origin")
    if not origin or origin not in settings.CORS_ALLOWED_ORIGINS:
        raise PermissionDenied("Origine non autorisée pour cet endpoint.")


def _set_refresh_cookie(response, refresh_token_str):
    response.set_cookie(
        settings.AUTH_COOKIE_NAME,
        refresh_token_str,
        max_age=settings.JWT_REFRESH_HOURS * 60 * 60,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        path=settings.AUTH_COOKIE_PATH,
        domain=settings.AUTH_COOKIE_DOMAIN,
    )


def _delete_refresh_cookie(response):
    response.delete_cookie(
        settings.AUTH_COOKIE_NAME,
        path=settings.AUTH_COOKIE_PATH,
        domain=settings.AUTH_COOKIE_DOMAIN,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )


def _school_is_usable(user) -> bool:
    """`True` si l'école de `user` ne bloque pas la connexion (toujours vrai
    pour un SUPER_ADMIN, qui n'a pas d'école)."""
    if user.role == User.Role.SUPER_ADMIN:
        return True
    return user.school_id is not None and user.school.is_active


def _authenticate(email: str, password: str):
    """Vérifie les identifiants. Retourne `None` pour toute raison d'échec,
    sans jamais distinguer compte inconnu / mauvais mot de passe / compte ou
    école désactivés (énumération impossible)."""
    try:
        user = User.objects.select_related("school").get(email__iexact=email)
    except User.DoesNotExist:
        # Fait tourner le hasher de mot de passe même sans utilisateur pour
        # atténuer la différence de temps de réponse (recette standard de
        # `django.contrib.auth.backends.ModelBackend`).
        User().set_password(password)
        return None
    if not user.check_password(password):
        return None
    if not user.is_active:
        return None
    if not _school_is_usable(user):
        return None
    return user


def _user_from_token_payload(refresh: RefreshToken):
    user_id = refresh.payload.get(jwt_settings.USER_ID_CLAIM)
    try:
        return User.objects.select_related("school").get(pk=user_id)
    except (User.DoesNotExist, ValueError, TypeError, DjangoValidationError):
        return None


class LoginView(APIView):
    """`POST /api/auth/login/` : email + mot de passe → access token + cookie."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip()
        password = serializer.validated_data["password"]
        credentials = {"email": email}

        if not AxesProxyHandler.is_allowed(request, credentials):
            log_security_event("login_locked", request, email=mask_email(email))
            record_audit(
                request,
                action="account_locked",
                entity_type="User",
                metadata={"email": mask_email(email)},
            )
            return Response(GENERIC_LOGIN_ERROR, status=429)

        user = _authenticate(email, password)
        if user is None:
            AxesProxyHandler.user_login_failed(
                sender=self.__class__, credentials=credentials, request=request
            )
            log_security_event("login_failed", request, email=mask_email(email))
            return Response(GENERIC_LOGIN_ERROR, status=401)

        AxesProxyHandler.user_logged_in(sender=self.__class__, request=request, user=user)
        record_audit(request, action="login_success", entity_type="User", entity_id=str(user.id))

        refresh = RefreshToken.for_user(user)
        data = build_auth_payload(user)
        data["access"] = str(refresh.access_token)

        response = Response(data, status=200)
        _set_refresh_cookie(response, str(refresh))
        return response


class RefreshView(APIView):
    """`POST /api/auth/refresh/` : lit le refresh du cookie, le fait tourner."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_scope = "refresh"

    def post(self, request):
        _check_trusted_origin(request)

        raw_refresh = request.COOKIES.get(settings.AUTH_COOKIE_NAME)
        if not raw_refresh:
            return Response(GENERIC_AUTH_ERROR, status=401)

        try:
            refresh = RefreshToken(raw_refresh)
        except TokenError:
            return Response(GENERIC_AUTH_ERROR, status=401)

        user = _user_from_token_payload(refresh)
        if user is None or not user.is_active or not _school_is_usable(user):
            return Response(GENERIC_AUTH_ERROR, status=401)

        access = refresh.access_token

        # Rotation : l'ancien jti est mis en liste noire, le jeton est muté
        # en un nouveau jti/exp/iat puis réenregistré comme actif (voir
        # `register_outstanding_token` : nécessaire tant que la version
        # installée de simplejwt n'a pas `Token.outstand()`).
        refresh.blacklist()
        refresh.set_jti()
        refresh.set_exp()
        refresh.set_iat()
        register_outstanding_token(refresh, user)

        response = Response({"access": str(access)}, status=200)
        _set_refresh_cookie(response, str(refresh))
        return response


class LogoutView(APIView):
    """`POST /api/auth/logout/` : met le refresh en liste noire, supprime le cookie.

    Exige un access token valide (comme toute autre route protégée, hors
    liste blanche health/login/refresh) en plus de l'en-tête `Origin` de
    confiance : la déconnexion ne doit pas devenir un moyen non authentifié
    de faire tourner des écritures en base.
    """

    def post(self, request):
        _check_trusted_origin(request)

        raw_refresh = request.COOKIES.get(settings.AUTH_COOKIE_NAME)
        if raw_refresh:
            try:
                RefreshToken(raw_refresh).blacklist()
            except TokenError:
                pass  # déjà invalide/expiré : rien à mettre en liste noire

        response = Response(status=204)
        _delete_refresh_cookie(response)
        record_audit(request, action="logout", entity_type="User", entity_id=str(request.user.id))
        return response


class MeView(APIView):
    """`GET /api/auth/me/` : même contenu que `login`, sans jeton."""

    def get(self, request):
        return Response(build_auth_payload(request.user))


class ChangePasswordView(APIView):
    """`POST /api/auth/change-password/` : invalide tous les refresh existants."""

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        blacklist_all_outstanding_tokens(user)

        record_audit(
            request, action="password_changed", entity_type="User", entity_id=str(user.id)
        )

        response = Response(status=204)
        _delete_refresh_cookie(response)
        return response
