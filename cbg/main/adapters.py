"""django-allauth adapters: Google SSO only for pre-existing league accounts."""

from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib import messages
from django.shortcuts import redirect


class CBGSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Allow Google sign-in only when the Google account is already linked,
    or when a logged-in user is connecting Google to their account.
    """

    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            return
        if request.user.is_authenticated:
            return
        messages.error(
            request,
            'This Google account is not linked to a league login. '
            'Sign in with your username and password first, then connect Google '
            'from Account Settings.',
        )
        raise ImmediateHttpResponse(redirect('login'))

    def is_open_for_signup(self, request, sociallogin):
        return False
