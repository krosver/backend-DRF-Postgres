from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import Optional, Tuple
from django.contrib.auth.models import AnonymousUser
from django.utils.functional import cached_property
from rbac.models import Role, Resource, PermissionRule, UserRole
from rest_framework.permissions import BasePermission

class Action(str, Enum):
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"

class Scope(str, Enum):
    OWN = "own"
    ANY = "any"

@dataclass(frozen=True)
class Decision:
    allowed: bool
    scope: Optional[Scope] = None

def _is_authenticated_user(user) -> bool:
    return not isinstance(user, AnonymousUser) and bool(getattr(user, "is_authenticated", False))

def _perm_field(action: Action, scope: Scope | None) -> str:
    if action == Action.CREATE:
        return "create"
    base = {Action.READ: "read", Action.UPDATE: "update", Action.DELETE: "delete"}[action]
    return base if scope == Scope.OWN else f"{base}_all"

@lru_cache(maxsize=512)
def _resource_id_by_code(code: str) -> Optional[int]:
    try:
        return Resource.objects.only("id").get(code=code).id
    except Resource.DoesNotExist:
        return None

@lru_cache(maxsize=1024)
def _role_ids_for_user(user_id: int) -> Tuple[int, ...]:
    ids = UserRole.objects.filter(user_id=user_id).values_list("role_id", flat=True).order_by()
    return tuple(ids)

@lru_cache(maxsize=4096)
def _rules_matrix(role_ids: Tuple[int, ...], resource_id: int) -> dict:
    flags = {
        "read": False,
        "read_all": False,
        "create": False,
        "update": False,
        "update_all": False,
        "delete": False,
        "delete_all": False,
    }
    if not role_ids:
        return flags
    qs = PermissionRule.objects.filter(role_id__in=role_ids, resource_id=resource_id)
    for rp in qs.only(*flags.keys()):
        for k in flags.keys():
            flags[k] = flags[k] or bool(getattr(rp, k))
    return flags

class AccessEvaluator:
    def __init__(self, user):
        self.user = user

    @cached_property
    def _role_ids(self) -> Tuple[int, ...]:
        if not _is_authenticated_user(self.user):
            return tuple()
        return _role_ids_for_user(self.user.id)

    def evaluate(self, resource_code: str, action: Action, *, owner_id: Optional[int] = None) -> Decision:
        if not _is_authenticated_user(self.user):
            return Decision(False, None)
        resource_id = _resource_id_by_code(resource_code)
        if resource_id is None:
            return Decision(False, None)
        if getattr(self.user, "is_superuser", False):
            scope = Scope.ANY if action != Action.CREATE else None
            return Decision(True, scope)
        rules = _rules_matrix(self._role_ids, resource_id)
        if action == Action.CREATE:
            ok = rules.get("create", False)
            return Decision(bool(ok), None)
        any_field = _perm_field(action, Scope.ANY)
        if rules.get(any_field, False):
            return Decision(True, Scope.ANY)
        own_field = _perm_field(action, Scope.OWN)
        if rules.get(own_field, False) and owner_id is not None:
            if int(owner_id) == int(getattr(self.user, "id")):
                return Decision(True, Scope.OWN)
        return Decision(False, None)

def evaluate_access(user, resource_code: str, action: str | Action, *, owner_id: Optional[int] = None) -> Decision:
    act = action if isinstance(action, Action) else Action(action)
    return AccessEvaluator(user).evaluate(resource_code, act, owner_id=owner_id)

class RBACPermission(BasePermission):
    message = "Forbidden"

    def has_permission(self, request, view) -> bool:
        res = getattr(view, "rbac_resource", None)
        if not res:
            return True
        action = _map_view_action(view, request)
        if action is None:
            return True
        decision = evaluate_access(request.user, res, action)
        return decision.allowed

    def has_object_permission(self, request, view, obj) -> bool:
        res = getattr(view, "rbac_resource", None)
        if not res:
            return True
        action = _map_view_action(view, request)
        if action is None:
            return True
        owner_id = _extract_owner_id(obj, getattr(view, "rbac_owner_attr", "owner_id"))
        decision = evaluate_access(request.user, res, action, owner_id=owner_id)
        return decision.allowed

def _map_view_action(view, request) -> Optional[Action]:
    action_name = getattr(getattr(view, "action", None), "lower", lambda: None)()
    if action_name:
        attr = f"rbac_action_{action_name}"
        if hasattr(view, attr):
            return getattr(view, attr)
        default_by_action = {
            "list": Action.READ,
            "retrieve": Action.READ,
            "create": Action.CREATE,
            "update": Action.UPDATE,
            "partial_update": Action.UPDATE,
            "destroy": Action.DELETE,
        }
        return default_by_action.get(action_name)
    method = request.method.upper()
    default_by_method = {
        "GET": Action.READ,
        "POST": Action.CREATE,
        "PUT": Action.UPDATE,
        "PATCH": Action.UPDATE,
        "DELETE": Action.DELETE,
    }
    return default_by_method.get(method)

def _extract_owner_id(obj, owner_attr: str) -> Optional[int]:
    try:
        parts = owner_attr.split(".")
        val = obj
        for p in parts:
            val = getattr(val, p)
        return int(val) if val is not None else None
    except Exception:
        return None
