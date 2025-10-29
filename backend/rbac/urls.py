# rbac/urls.py
from rest_framework.routers import DefaultRouter
from .views import RoleViewSet, ResourceViewSet, PermissionRuleViewSet, UserRoleViewSet

router = DefaultRouter()
router.register(r"roles", RoleViewSet, basename="rbac-roles")
router.register(r"resources", ResourceViewSet, basename="rbac-resources")
router.register(r"rules", PermissionRuleViewSet, basename="rbac-rules")
router.register(r"user-roles", UserRoleViewSet, basename="rbac-user-roles")

urlpatterns = router.urls
