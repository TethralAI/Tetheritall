"""
Business Model and Monetization System

This module provides comprehensive business model management, subscription tiers,
pricing strategies, and value proposition tracking for the consumer-ready orchestration platform.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
from pathlib import Path

from .models import *

logger = logging.getLogger(__name__)


class SubscriptionTier(Enum):
    """Subscription tiers."""
    FREE = "free"
    PREMIUM = "premium"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class BillingCycle(Enum):
    """Billing cycles."""
    MONTHLY = "monthly"
    YEARLY = "yearly"
    QUARTERLY = "quarterly"


class PaymentStatus(Enum):
    """Payment status."""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


@dataclass
class PricingPlan:
    """Pricing plan definition."""
    plan_id: str
    tier: SubscriptionTier
    name: str
    description: str
    monthly_price: float
    yearly_price: float
    features: List[str] = field(default_factory=list)
    device_limits: Dict[str, int] = field(default_factory=dict)
    automation_limits: Dict[str, int] = field(default_factory=dict)
    support_level: str = "basic"
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Subscription:
    """User subscription."""
    subscription_id: str
    user_id: str
    tier: SubscriptionTier
    plan_id: str
    billing_cycle: BillingCycle
    start_date: datetime = field(default_factory=datetime.utcnow)
    end_date: Optional[datetime] = None
    auto_renew: bool = True
    status: str = "active"
    payment_method: Optional[str] = None
    last_payment_date: Optional[datetime] = None
    next_payment_date: Optional[datetime] = None
    amount_paid: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Payment:
    """Payment record."""
    payment_id: str
    subscription_id: str
    user_id: str
    amount: float
    currency: str = "USD"
    payment_method: str = "credit_card"
    status: PaymentStatus = PaymentStatus.PENDING
    transaction_id: Optional[str] = None
    payment_date: datetime = field(default_factory=datetime.utcnow)
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValueMetric:
    """Value proposition metric."""
    metric_id: str
    user_id: str
    metric_type: str
    value: float
    unit: str
    period: str
    calculated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CustomerInsight:
    """Customer insight and analytics."""
    insight_id: str
    user_id: str
    insight_type: str
    title: str
    description: str
    value: float
    recommendation: str
    generated_at: datetime = field(default_factory=datetime.utcnow)
    action_taken: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class PricingManager:
    """Manages pricing plans and strategies."""
    
    def __init__(self):
        self.pricing_plans: Dict[str, PricingPlan] = {}
        self._initialize_pricing_plans()
    
    def _initialize_pricing_plans(self):
        """Initialize default pricing plans."""
        plans = [
            PricingPlan(
                plan_id="free_plan",
                tier=SubscriptionTier.FREE,
                name="Free",
                description="Basic smart home automation for everyone",
                monthly_price=0.0,
                yearly_price=0.0,
                features=[
                    "Basic automation (up to 5)",
                    "Device control",
                    "Mobile app access",
                    "Email support"
                ],
                device_limits={"total_devices": 10, "automations": 5},
                automation_limits={"daily_automations": 50},
                support_level="community"
            ),
            PricingPlan(
                plan_id="premium_plan",
                tier=SubscriptionTier.PREMIUM,
                name="Premium",
                description="Advanced automation and features for power users",
                monthly_price=9.99,
                yearly_price=99.99,
                features=[
                    "Advanced automation (unlimited)",
                    "Voice control",
                    "Energy optimization",
                    "Priority support",
                    "Advanced analytics",
                    "Custom scenes"
                ],
                device_limits={"total_devices": 50, "automations": -1},  # -1 means unlimited
                automation_limits={"daily_automations": 500},
                support_level="priority"
            ),
            PricingPlan(
                plan_id="professional_plan",
                tier=SubscriptionTier.PROFESSIONAL,
                name="Professional",
                description="Complete smart home solution with professional installation",
                monthly_price=24.99,
                yearly_price=249.99,
                features=[
                    "Everything in Premium",
                    "Professional installation",
                    "Custom integration",
                    "Dedicated support",
                    "Advanced security",
                    "Multi-location support"
                ],
                device_limits={"total_devices": 200, "automations": -1},
                automation_limits={"daily_automations": 2000},
                support_level="dedicated"
            ),
            PricingPlan(
                plan_id="enterprise_plan",
                tier=SubscriptionTier.ENTERPRISE,
                name="Enterprise",
                description="Enterprise-grade solution for large deployments",
                monthly_price=99.99,
                yearly_price=999.99,
                features=[
                    "Everything in Professional",
                    "Custom development",
                    "API access",
                    "White-label options",
                    "Advanced reporting",
                    "SLA guarantees"
                ],
                device_limits={"total_devices": -1, "automations": -1},
                automation_limits={"daily_automations": -1},
                support_level="enterprise"
            )
        ]
        
        for plan in plans:
            self.pricing_plans[plan.plan_id] = plan
    
    async def get_pricing_plans(self, active_only: bool = True) -> List[PricingPlan]:
        """Get available pricing plans."""
        plans = list(self.pricing_plans.values())
        if active_only:
            plans = [plan for plan in plans if plan.active]
        return plans
    
    async def get_plan_by_tier(self, tier: SubscriptionTier) -> Optional[PricingPlan]:
        """Get pricing plan by subscription tier."""
        for plan in self.pricing_plans.values():
            if plan.tier == tier and plan.active:
                return plan
        return None
    
    async def calculate_price(self, plan_id: str, billing_cycle: BillingCycle) -> float:
        """Calculate price for a plan and billing cycle."""
        if plan_id not in self.pricing_plans:
            return 0.0
        
        plan = self.pricing_plans[plan_id]
        
        if billing_cycle == BillingCycle.MONTHLY:
            return plan.monthly_price
        elif billing_cycle == BillingCycle.YEARLY:
            return plan.yearly_price
        elif billing_cycle == BillingCycle.QUARTERLY:
            return plan.monthly_price * 3 * 0.9  # 10% discount for quarterly
        else:
            return plan.monthly_price
    
    async def compare_plans(self, plan_ids: List[str]) -> Dict[str, Any]:
        """Compare multiple pricing plans."""
        comparison = {
            "plans": [],
            "features_comparison": {},
            "pricing_comparison": {}
        }
        
        all_features = set()
        
        for plan_id in plan_ids:
            if plan_id in self.pricing_plans:
                plan = self.pricing_plans[plan_id]
                comparison["plans"].append({
                    "plan_id": plan.plan_id,
                    "name": plan.name,
                    "tier": plan.tier.value,
                    "monthly_price": plan.monthly_price,
                    "yearly_price": plan.yearly_price,
                    "features": plan.features,
                    "device_limits": plan.device_limits,
                    "support_level": plan.support_level
                })
                all_features.update(plan.features)
        
        # Create feature comparison matrix
        for feature in sorted(all_features):
            comparison["features_comparison"][feature] = {}
            for plan_data in comparison["plans"]:
                comparison["features_comparison"][feature][plan_data["plan_id"]] = feature in plan_data["features"]
        
        return comparison


class SubscriptionManager:
    """Manages user subscriptions and billing."""
    
    def __init__(self):
        self.subscriptions: Dict[str, Subscription] = {}
        self.payments: List[Payment] = []
        self.pricing_manager = PricingManager()
    
    async def create_subscription(self, user_id: str, tier: SubscriptionTier,
                                billing_cycle: BillingCycle, payment_method: str = "credit_card") -> Subscription:
        """Create a new subscription for a user."""
        plan = await self.pricing_manager.get_plan_by_tier(tier)
        if not plan:
            raise ValueError(f"No active plan found for tier {tier}")
        
        # Calculate subscription dates
        start_date = datetime.utcnow()
        if billing_cycle == BillingCycle.MONTHLY:
            end_date = start_date + timedelta(days=30)
            next_payment_date = start_date + timedelta(days=30)
        elif billing_cycle == BillingCycle.YEARLY:
            end_date = start_date + timedelta(days=365)
            next_payment_date = start_date + timedelta(days=365)
        elif billing_cycle == BillingCycle.QUARTERLY:
            end_date = start_date + timedelta(days=90)
            next_payment_date = start_date + timedelta(days=90)
        else:
            end_date = start_date + timedelta(days=30)
            next_payment_date = start_date + timedelta(days=30)
        
        subscription = Subscription(
            subscription_id=str(uuid.uuid4()),
            user_id=user_id,
            tier=tier,
            plan_id=plan.plan_id,
            billing_cycle=billing_cycle,
            start_date=start_date,
            end_date=end_date,
            payment_method=payment_method,
            next_payment_date=next_payment_date
        )
        
        self.subscriptions[subscription.subscription_id] = subscription
        
        # Create initial payment
        amount = await self.pricing_manager.calculate_price(plan.plan_id, billing_cycle)
        await self.create_payment(subscription.subscription_id, user_id, amount, payment_method)
        
        return subscription
    
    async def get_user_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get active subscription for a user."""
        for subscription in self.subscriptions.values():
            if subscription.user_id == user_id and subscription.status == "active":
                return subscription
        return None
    
    async def upgrade_subscription(self, user_id: str, new_tier: SubscriptionTier) -> Optional[Subscription]:
        """Upgrade user subscription to a higher tier."""
        current_subscription = await self.get_user_subscription(user_id)
        if not current_subscription:
            return None
        
        # Create new subscription
        new_subscription = await self.create_subscription(
            user_id, new_tier, current_subscription.billing_cycle, current_subscription.payment_method
        )
        
        # Cancel old subscription
        current_subscription.status = "cancelled"
        current_subscription.end_date = datetime.utcnow()
        
        return new_subscription
    
    async def cancel_subscription(self, user_id: str) -> bool:
        """Cancel user subscription."""
        subscription = await self.get_user_subscription(user_id)
        if not subscription:
            return False
        
        subscription.status = "cancelled"
        subscription.end_date = datetime.utcnow()
        subscription.auto_renew = False
        
        return True
    
    async def create_payment(self, subscription_id: str, user_id: str, amount: float,
                           payment_method: str) -> Payment:
        """Create a payment record."""
        payment = Payment(
            payment_id=str(uuid.uuid4()),
            subscription_id=subscription_id,
            user_id=user_id,
            amount=amount,
            payment_method=payment_method,
            description=f"Subscription payment for {subscription_id}"
        )
        
        self.payments.append(payment)
        return payment
    
    async def process_payment(self, payment_id: str, transaction_id: str) -> bool:
        """Process a payment."""
        payment = next((p for p in self.payments if p.payment_id == payment_id), None)
        if not payment:
            return False
        
        payment.status = PaymentStatus.PAID
        payment.transaction_id = transaction_id
        payment.payment_date = datetime.utcnow()
        
        # Update subscription
        subscription = self.subscriptions.get(payment.subscription_id)
        if subscription:
            subscription.last_payment_date = datetime.utcnow()
            subscription.amount_paid += payment.amount
        
        return True
    
    async def get_subscription_analytics(self) -> Dict[str, Any]:
        """Get subscription analytics."""
        total_subscriptions = len(self.subscriptions)
        active_subscriptions = len([s for s in self.subscriptions.values() if s.status == "active"])
        
        tier_distribution = {}
        for subscription in self.subscriptions.values():
            tier = subscription.tier.value
            tier_distribution[tier] = tier_distribution.get(tier, 0) + 1
        
        total_revenue = sum(payment.amount for payment in self.payments if payment.status == PaymentStatus.PAID)
        
        return {
            "total_subscriptions": total_subscriptions,
            "active_subscriptions": active_subscriptions,
            "churn_rate": ((total_subscriptions - active_subscriptions) / total_subscriptions * 100) if total_subscriptions > 0 else 0,
            "tier_distribution": tier_distribution,
            "total_revenue": total_revenue,
            "monthly_recurring_revenue": self._calculate_mrr()
        }
    
    def _calculate_mrr(self) -> float:
        """Calculate Monthly Recurring Revenue."""
        mrr = 0.0
        for subscription in self.subscriptions.values():
            if subscription.status == "active":
                plan = self.pricing_manager.pricing_plans.get(subscription.plan_id)
                if plan:
                    if subscription.billing_cycle == BillingCycle.MONTHLY:
                        mrr += plan.monthly_price
                    elif subscription.billing_cycle == BillingCycle.YEARLY:
                        mrr += plan.yearly_price / 12
                    elif subscription.billing_cycle == BillingCycle.QUARTERLY:
                        mrr += (plan.monthly_price * 3 * 0.9) / 3
        return mrr


class ValuePropositionTracker:
    """Tracks and measures value propositions for users."""
    
    def __init__(self):
        self.value_metrics: List[ValueMetric] = []
        self.customer_insights: List[CustomerInsight] = []
    
    async def track_energy_savings(self, user_id: str, savings_kwh: float, period: str = "monthly") -> str:
        """Track energy savings for a user."""
        metric = ValueMetric(
            metric_id=str(uuid.uuid4()),
            user_id=user_id,
            metric_type="energy_savings",
            value=savings_kwh,
            unit="kWh",
            period=period
        )
        
        self.value_metrics.append(metric)
        return metric.metric_id
    
    async def track_time_savings(self, user_id: str, time_saved_minutes: float, period: str = "monthly") -> str:
        """Track time savings for a user."""
        metric = ValueMetric(
            metric_id=str(uuid.uuid4()),
            user_id=user_id,
            metric_type="time_savings",
            value=time_saved_minutes,
            unit="minutes",
            period=period
        )
        
        self.value_metrics.append(metric)
        return metric.metric_id
    
    async def track_automation_efficiency(self, user_id: str, efficiency_score: float, period: str = "monthly") -> str:
        """Track automation efficiency for a user."""
        metric = ValueMetric(
            metric_id=str(uuid.uuid4()),
            user_id=user_id,
            metric_type="automation_efficiency",
            value=efficiency_score,
            unit="score",
            period=period
        )
        
        self.value_metrics.append(metric)
        return metric.metric_id
    
    async def generate_customer_insight(self, user_id: str, insight_type: str, 
                                      title: str, description: str, value: float,
                                      recommendation: str) -> str:
        """Generate a customer insight."""
        insight = CustomerInsight(
            insight_id=str(uuid.uuid4()),
            user_id=user_id,
            insight_type=insight_type,
            title=title,
            description=description,
            value=value,
            recommendation=recommendation
        )
        
        self.customer_insights.append(insight)
        return insight.insight_id
    
    async def get_user_value_summary(self, user_id: str) -> Dict[str, Any]:
        """Get value summary for a user."""
        user_metrics = [m for m in self.value_metrics if m.user_id == user_id]
        user_insights = [i for i in self.customer_insights if i.user_id == user_id]
        
        # Calculate total value
        energy_savings = sum(m.value for m in user_metrics if m.metric_type == "energy_savings")
        time_savings = sum(m.value for m in user_metrics if m.metric_type == "time_savings")
        efficiency_score = sum(m.value for m in user_metrics if m.metric_type == "automation_efficiency") / len([m for m in user_metrics if m.metric_type == "automation_efficiency"]) if any(m.metric_type == "automation_efficiency" for m in user_metrics) else 0
        
        # Calculate monetary value (placeholder calculations)
        energy_value = energy_savings * 0.12  # $0.12 per kWh
        time_value = time_savings / 60 * 25  # $25 per hour
        
        return {
            "user_id": user_id,
            "energy_savings": {
                "kwh": energy_savings,
                "value_usd": energy_value
            },
            "time_savings": {
                "minutes": time_savings,
                "value_usd": time_value
            },
            "automation_efficiency": efficiency_score,
            "total_value_usd": energy_value + time_value,
            "insights_count": len(user_insights),
            "recent_insights": [
                {
                    "title": insight.title,
                    "description": insight.description,
                    "value": insight.value,
                    "recommendation": insight.recommendation
                }
                for insight in user_insights[-5:]  # Last 5 insights
            ]
        }
    
    async def get_value_analytics(self) -> Dict[str, Any]:
        """Get overall value analytics."""
        total_users = len(set(m.user_id for m in self.value_metrics))
        total_energy_savings = sum(m.value for m in self.value_metrics if m.metric_type == "energy_savings")
        total_time_savings = sum(m.value for m in self.value_metrics if m.metric_type == "time_savings")
        
        return {
            "total_users": total_users,
            "total_energy_savings_kwh": total_energy_savings,
            "total_time_savings_minutes": total_time_savings,
            "average_energy_savings_per_user": total_energy_savings / total_users if total_users > 0 else 0,
            "average_time_savings_per_user": total_time_savings / total_users if total_users > 0 else 0,
            "total_value_generated_usd": (total_energy_savings * 0.12) + (total_time_savings / 60 * 25)
        }


class BusinessModelSystem:
    """Main business model and monetization system."""
    
    def __init__(self):
        self.pricing_manager = PricingManager()
        self.subscription_manager = SubscriptionManager()
        self.value_tracker = ValuePropositionTracker()
        self._running = False
    
    async def start(self):
        """Start the business model system."""
        if self._running:
            return
        
        logger.info("Starting Business Model System...")
        
        # Initialize business components
        await self._initialize_business_components()
        
        self._running = True
        logger.info("Business Model System started successfully")
    
    async def stop(self):
        """Stop the business model system."""
        if not self._running:
            return
        
        logger.info("Stopping Business Model System...")
        self._running = False
        logger.info("Business Model System stopped")
    
    async def get_pricing_plans(self) -> List[PricingPlan]:
        """Get available pricing plans."""
        return await self.pricing_manager.get_pricing_plans()
    
    async def create_user_subscription(self, user_id: str, tier: SubscriptionTier,
                                     billing_cycle: BillingCycle) -> Subscription:
        """Create a subscription for a user."""
        return await self.subscription_manager.create_subscription(user_id, tier, billing_cycle)
    
    async def get_user_subscription(self, user_id: str) -> Optional[Subscription]:
        """Get user's active subscription."""
        return await self.subscription_manager.get_user_subscription(user_id)
    
    async def upgrade_user_subscription(self, user_id: str, new_tier: SubscriptionTier) -> Optional[Subscription]:
        """Upgrade user subscription."""
        return await self.subscription_manager.upgrade_subscription(user_id, new_tier)
    
    async def track_user_value(self, user_id: str, value_type: str, value: float, period: str = "monthly") -> str:
        """Track value generated for a user."""
        if value_type == "energy_savings":
            return await self.value_tracker.track_energy_savings(user_id, value, period)
        elif value_type == "time_savings":
            return await self.value_tracker.track_time_savings(user_id, value, period)
        elif value_type == "automation_efficiency":
            return await self.value_tracker.track_automation_efficiency(user_id, value, period)
        else:
            raise ValueError(f"Unknown value type: {value_type}")
    
    async def generate_user_insight(self, user_id: str, insight_type: str, title: str,
                                  description: str, value: float, recommendation: str) -> str:
        """Generate insight for a user."""
        return await self.value_tracker.generate_customer_insight(
            user_id, insight_type, title, description, value, recommendation
        )
    
    async def get_user_value_summary(self, user_id: str) -> Dict[str, Any]:
        """Get value summary for a user."""
        return await self.value_tracker.get_user_value_summary(user_id)
    
    async def get_business_analytics(self) -> Dict[str, Any]:
        """Get comprehensive business analytics."""
        return {
            "subscriptions": await self.subscription_manager.get_subscription_analytics(),
            "value_proposition": await self.value_tracker.get_value_analytics(),
            "pricing": {
                "total_plans": len(await self.pricing_manager.get_pricing_plans()),
                "active_plans": len(await self.pricing_manager.get_pricing_plans(active_only=True))
            }
        }
    
    async def _initialize_business_components(self):
        """Initialize business components."""
        logger.info("Initializing business components...")
        
        # Set up subscription monitoring
        # Set up value tracking
        # Set up pricing analytics
        
        logger.info("Business components initialized")


# Global business model system instance
business_model_system = BusinessModelSystem()

async def get_business_model_system() -> BusinessModelSystem:
    """Get the global business model system instance."""
    return business_model_system
