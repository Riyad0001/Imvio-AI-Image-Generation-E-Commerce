from django.core.management.base import BaseCommand
from apps.subscription.models import Plan, Feature, PlanFeature


# create 3 different plan
class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        # create 3 different plan
        plans = [
            Plan(name="Free", price=0, vat=0, interval="month", description="Free plan", free_trial=True, free_trial_days=30),
            Plan(name="Basic", price=10, vat=0, interval="month", description="Basic plan", free_trial=True, free_trial_days=30),
            Plan(name="Premium", price=20, vat=0, interval="month", description="Premium plan", free_trial=True, free_trial_days=30),
        ]
        for plan in plans:
            plan.save()
        
        # create 3 different feature
        features = [
            Feature(key="ai_conversation", name="AI Conversation", description="AI Conversation"),
            Feature(key="pdf_download", name="PDF Download", description="PDF Download"),
            Feature(key="image_generation", name="Image Generation", description="Image Generation"),
        ]
        for feature in features:
            feature.save()
        
        # create 3 different plan feature
        plan_features = [
            PlanFeature(plan=plans[0], feature=features[0], is_enabled=True, limit_value=10),
            PlanFeature(plan=plans[1], feature=features[1], is_enabled=True, limit_value=20),
            PlanFeature(plan=plans[2], feature=features[2], is_enabled=True, limit_value=30),
        ]
        for plan_feature in plan_features:
            plan_feature.save()
        
        self.stdout.write(self.style.SUCCESS('Successfully seeded subscription'))