import { Injectable, Logger, OnModuleInit } from '@nestjs/common';
import mqtt, { MqttClient } from 'mqtt';
import { EventBus } from '../observe/event-bus.js';

@Injectable()
export class MqttService implements OnModuleInit {
  private readonly logger = new Logger(MqttService.name);
  private client: MqttClient | null = null;

  constructor(private readonly bus: EventBus) {}

  onModuleInit(): void {
    const url = process.env.MQTT_URL;
    if (!url) return;
    this.client = mqtt.connect(url, { clientId: `connmgr-${Math.random().toString(36).slice(2)}` });
    this.client.on('connect', () => this.logger.log('MQTT connected'));
    this.client.on('message', (topic, payload) => {
      // TODO: parse topic and emit to ingest pipeline
      this.logger.debug(`MQTT ${topic} ${payload.toString()}`);
    });
  }
}

