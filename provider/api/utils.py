from fastapi import APIRouter, HTTPException, Depends

from provider.api.depends import resolve_subscribe_service
from provider.schemas.models import SubscribeRequest, UnsubscribeRequest, SubscriptionResponse
from provider.services.subscription import SubscriptionService

router = APIRouter(prefix="/api/v1", tags=["subscriptions"])


@router.post(
    "/subscribe",
    response_model=SubscriptionResponse
)
async def subscribe(
    request: SubscribeRequest,
    subscription_service: SubscriptionService = Depends(resolve_subscribe_service)
) -> SubscriptionResponse:
    try:
        success = await subscription_service.subscribe_user(request)

        if success:
            return SubscriptionResponse(
                success=True,
                message="Subscription created successfully",
                subscription_id=request.user_id
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to create subscription"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/unsubscribe", response_model=SubscriptionResponse)
async def unsubscribe(
    request: UnsubscribeRequest,
    subscription_service: SubscriptionService = Depends(resolve_subscribe_service)
) -> SubscriptionResponse:
    try:
        success = await subscription_service.unsubscribe_user(request)
        if success:
            return SubscriptionResponse(
                success=True,
                message="Subscription cancelled successfully"
            )
        raise HTTPException(
            status_code=404,
            detail="Subscription not found"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
