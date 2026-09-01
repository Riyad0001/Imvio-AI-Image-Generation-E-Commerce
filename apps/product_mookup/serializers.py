from rest_framework import serializers
from .models import Other_pages


# class ProductTypeSerializer(serializers.ModelSerializer):
#     image = serializers.SerializerMethodField()

#     class Meta:
#         model = ProductType
#         fields = [
#             "id",
#             "name",
#             "image"
#         ]

#     def get_image(self, obj):
#         request = self.context.get("request")
#         if obj.image: return request.build_absolute_uri(obj.image.url)
#         return None


# class SizeSerializer(serializers.ModelSerializer):

#     class Meta:
#         model = Size
#         fields = [
#             "id",
#             "name"
#         ]

class Other_pagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Other_pages
        fields = [
            "id",
            "name",
            "content",
            "types",
            "created_at",
            "updated_at"
        ]
