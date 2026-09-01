from apps.sub.services.order_service import OrderService


class OrderAgent:
    @staticmethod
    def create_order(user, validated_data):
        return OrderService.create_order(user=user, validated_data=validated_data)
