import uuid
from django.conf import settings


class IPGroupMiddleware:
    """
    Detects the client IP on every request, gets-or-creates an IPGroup row,
    resolves (or mints) the anonymous-uploader cookie, and attaches
    request.ip_group / request.anonymous_uploader for downstream use.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, 'IP_GROUP_ENABLED', True):
            request.ip_group = None
            request.anonymous_uploader = None
            return self.get_response(request)

        ip = self._get_client_ip(request)
        request.client_ip = ip
        new_cookie = None

        try:
            from .models import IPGroup, AnonymousUploader

            ip_group, _ = IPGroup.objects.get_or_create(
                ip_address=ip,
                defaults={'is_active': True},
            )
            request.ip_group = ip_group

            cookie_id = request.COOKIES.get('anon_id')
            if not cookie_id:
                cookie_id = uuid.uuid4().hex
                new_cookie = cookie_id

            uploader, _ = AnonymousUploader.objects.get_or_create(
                cookie_id=cookie_id,
                defaults={
                    'ip_group': ip_group,
                    'user_agent': request.META.get('HTTP_USER_AGENT', '')[:255],
                },
            )
            request.anonymous_uploader = uploader

        except Exception:
            request.ip_group = None
            request.anonymous_uploader = None

        response = self.get_response(request)

        if new_cookie:
            response.set_cookie(
                'anon_id',
                new_cookie,
                max_age=365 * 24 * 60 * 60,
                httponly=True,
                samesite='Lax',
            )

        return response

    @staticmethod
    def _get_client_ip(request):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '127.0.0.1')
