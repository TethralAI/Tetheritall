var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
var __metadata = (this && this.__metadata) || function (k, v) {
    if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(k, v);
};
var MqttService_1;
import { Injectable, Logger } from '@nestjs/common';
import mqtt from 'mqtt';
import { EventBus } from '../observe/event-bus.js';
let MqttService = MqttService_1 = class MqttService {
    bus;
    logger = new Logger(MqttService_1.name);
    client = null;
    constructor(bus) {
        this.bus = bus;
    }
    onModuleInit() {
        const url = process.env.MQTT_URL;
        if (!url)
            return;
        this.client = mqtt.connect(url, { clientId: `connmgr-${Math.random().toString(36).slice(2)}` });
        this.client.on('connect', () => this.logger.log('MQTT connected'));
        this.client.on('message', (topic, payload) => {
            this.logger.debug(`MQTT ${topic} ${payload.toString()}`);
        });
    }
};
MqttService = MqttService_1 = __decorate([
    Injectable(),
    __metadata("design:paramtypes", [EventBus])
], MqttService);
export { MqttService };
//# sourceMappingURL=mqtt.client.js.map