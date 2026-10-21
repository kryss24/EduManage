"""En-têtes de sécurité non couverts par `django.middleware.security`."""


class SecurityHeadersMiddleware:
    """Ajoute `Permissions-Policy` et un `Content-Security-Policy` restrictif.

    Cette API ne sert jamais de HTML interactif à un navigateur (hormis
    l'admin Django et le schéma OpenAPI en dev) : la CSP peut donc être
    maximalement restrictive, et les en-têtes d'autorisation de capteurs
    (caméra, micro, géolocalisation...) désactivés sans impact.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # L'admin Django et le schéma OpenAPI (dev uniquement) ont besoin de
        # leurs propres styles/scripts : seules les routes API reçoivent la
        # CSP maximaliste (elles ne servent jamais de HTML interactif).
        if request.path.startswith("/api/"):
            response.setdefault(
                "Content-Security-Policy",
                "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
            )
        response.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
        )
        return response
