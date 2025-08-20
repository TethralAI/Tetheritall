from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

from database.api_database import get_session_factory
from database.models import DeviceTwin
from adapters.smartcar import start_charge
from tools.prices.octopus import fetch_unit_rates, compute_cheap_window


async def nightly_ev_cheap_charge(engine, product_code: str, tariff_code: str, user_threshold: float = 0.6) -> None:
    # Compute from Octopus unit rates
    rates = fetch_unit_rates(product_code, tariff_code)
    start_ts, end_ts, _ = compute_cheap_window(rates, 120)
    session = get_session_factory("sqlite:///./iot_discovery.db")()
    try:
        twins = session.query(DeviceTwin).filter(DeviceTwin.provider == "smartcar").all()
        for t in twins:
            state = json.loads(t.state or "{}")
            soc = float(((state.get("percentRemaining") or 0)))
            at_home = True  # placeholder; enrich with geofence context
            if soc < user_threshold and at_home:
                # schedule charge (immediate for demo)
                access_token = state.get("access_token", "")  # placeholder: store tokens in IntegrationCredential
                if access_token:
                    await asyncio.to_thread(start_charge, access_token, t.external_id)
    finally:
        session.close()

