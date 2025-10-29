from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.permissions_engine import RBACPermission, Action


class ProductView(APIView):
    permission_classes = [RBACPermission]
    rbac_resource = "products"
    rbac_action_list = Action.READ
    rbac_action_create = Action.CREATE

    def get(self, request):
        mock_data = [
            {"id": 1, "name": "Laptop", "price": 1000},
            {"id": 2, "name": "Phone", "price": 600},
        ]
        return Response(mock_data, status=status.HTTP_200_OK)

    def post(self, request):
        return Response({"detail": "Product created (mock)"}, status=status.HTTP_201_CREATED)


class OrderView(APIView):
    permission_classes = [RBACPermission]
    rbac_resource = "orders"
    rbac_action_list = Action.READ
    rbac_action_destroy = Action.DELETE
    rbac_owner_attr = "owner_id"

    def get(self, request):
        mock_orders = [
            {"id": 101, "product": "Laptop", "owner": request.user.email},
            {"id": 102, "product": "Phone", "owner": request.user.email},
        ]
        return Response(mock_orders, status=status.HTTP_200_OK)

    def delete(self, request, order_id=None):
        return Response({"detail": f"Order {order_id} deleted (mock)"}, status=status.HTTP_200_OK)