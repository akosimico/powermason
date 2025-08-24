from django.core import signing
from django.shortcuts import get_object_or_404
from django.core.signing import BadSignature, SignatureExpired
from authentication.models import UserProfile

DASHBOARD_SALT = "dahboard.link"

SEC = 5
ONE_HOUR = 60 * 60
ONE_DAY = ONE_HOUR * 24
ONE_WEEK = ONE_DAY * 7

DEFAULT_MAX_AGE = ONE_WEEK # 7 days

def make_dashboard_token(profile):
    payload = {
        "u": str(profile.user.id),
        "r": profile.role,
        "v": 1,
    }
    return signing.dumps(payload, salt=DASHBOARD_SALT, compress=True) # allows max_age checks on load

def parse_dashboard_token(token, max_age=DEFAULT_MAX_AGE):
    
    """
    Returns a dict: {'u': uuid_str, 'r': role_code, 'v': token_version}
    Raises BadSignature/SignatureExpired if invalid/expired.
    """
    return signing.loads(token, salt=DASHBOARD_SALT, max_age=max_age)

def _resolve_profile_from_token(token):
    payload = signing.loads(token, salt=DASHBOARD_SALT, max_age=ONE_HOUR)    # e.g. 1 hour validity
    user_id = int(payload["u"])  # make sure it’s int
    role = payload["r"]

    return UserProfile.objects.get(user__id=user_id, role=role)
