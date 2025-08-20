"""
SQLAlchemy ORM models for IoT API Discovery
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)
    model = Column(String(255), nullable=False, index=True)
    manufacturer = Column(String(255), nullable=False, index=True)
    firmware_version = Column(String(255), nullable=True)
    last_scanned = Column(DateTime, default=None, nullable=True)

    api_endpoints = relationship("ApiEndpoint", back_populates="device", cascade="all, delete-orphan")
    scan_results = relationship("ScanResult", back_populates="device", cascade="all, delete-orphan")
    auth_methods = relationship("AuthenticationMethod", back_populates="device", cascade="all, delete-orphan")


class ApiEndpoint(Base):
    __tablename__ = "api_endpoints"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    url = Column(Text, nullable=False)
    method = Column(String(16), default="GET", nullable=False)
    auth_required = Column(Boolean, default=False, nullable=False)
    success_rate = Column(Float, default=0.0, nullable=False)

    device = relationship("Device", back_populates="api_endpoints")


class ScanResult(Base):
    __tablename__ = "scan_results"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    agent_type = Column(String(64), nullable=False)
    raw_data = Column(Text, nullable=False)

    device = relationship("Device", back_populates="scan_results")


class AuthenticationMethod(Base):
    __tablename__ = "authentication_methods"

    id = Column(Integer, primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    auth_type = Column(String(64), nullable=False)
    credentials = Column(Text, nullable=True)
    success_rate = Column(Float, default=0.0, nullable=False)

    device = relationship("Device", back_populates="auth_methods")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String(64), primary_key=True)
    manufacturer = Column(String(255), nullable=False)
    model = Column(String(255), nullable=True)
    priority = Column(Integer, default=10, nullable=False)
    state = Column(String(32), default="queued", nullable=False)
    payload = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    paused = Column(Boolean, default=False, nullable=False)
    canceled = Column(Boolean, default=False, nullable=False)


class IntegrationCredential(Base):
    __tablename__ = "integration_credentials"

    id = Column(Integer, primary_key=True)
    provider = Column(String(64), nullable=False, index=True)  # e.g., smartthings, tuya
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    extra = Column(Text, nullable=True)  # JSON string for additional fields


class AutomationRuleModel(Base):
    __tablename__ = "automation_rules"

    id = Column(String(128), primary_key=True)
    enabled = Column(Boolean, default=True, nullable=False)
    trigger = Column(Text, nullable=False)  # JSON
    conditions = Column(Text, nullable=True)  # JSON
    actions = Column(Text, nullable=False)  # JSON
    schedule_interval_seconds = Column(Integer, nullable=True)  # optional periodic schedule

