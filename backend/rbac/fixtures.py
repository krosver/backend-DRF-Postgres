# rbac/fixtures.py  (для начального наполнения)
from .models import Role, Resource, PermissionRule

def load():
    admin, _ = Role.objects.get_or_create(name="admin", defaults={"description": "Системный администратор"})
    manager, _ = Role.objects.get_or_create(name="manager", defaults={"description": "Менеджер"})
    user, _ = Role.objects.get_or_create(name="user", defaults={"description": "Обычный пользователь"})

    # базовые ресурсы
    res_users, _ = Resource.objects.get_or_create(code="users", defaults={"description": "Пользователи"})
    res_rbac, _ = Resource.objects.get_or_create(code="rbac.rules", defaults={"description": "Управление правилами"})
    res_orders, _ = Resource.objects.get_or_create(code="orders", defaults={"description": "Заказы (mock)"})

    # права админа на все
    for r in (res_users, res_rbac, res_orders):
        PermissionRule.objects.get_or_create(
            role=admin, resource=r,
            defaults=dict(read=True, read_all=True, create=True, update=True, update_all=True, delete=True, delete_all=True)
        )

    # менеджер: читать всех пользователей, редактировать только своих заказчиков; работать с заказами
    PermissionRule.objects.get_or_create(
        role=manager, resource=res_users,
        defaults=dict(read=True, read_all=True, create=False, update=False, update_all=False, delete=False, delete_all=False)
    )
    PermissionRule.objects.get_or_create(
        role=manager, resource=res_orders,
        defaults=dict(read=True, read_all=True, create=True, update=True, update_all=False, delete=False, delete_all=False)
    )

    # user: видеть себя, работать только со своими объектами
    PermissionRule.objects.get_or_create(
        role=user, resource=res_users,
        defaults=dict(read=True, read_all=False, create=False, update=True, update_all=False, delete=False, delete_all=False)
    )
    PermissionRule.objects.get_or_create(
        role=user, resource=res_orders,
        defaults=dict(read=True, read_all=False, create=True, update=True, update_all=False, delete=True, delete_all=False)
    )
