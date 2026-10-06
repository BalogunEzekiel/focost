def current_subscription(user_id):
    from app.subscriptions.service import SubscriptionService
    return SubscriptionService.current(user_id)
