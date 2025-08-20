var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
import { Injectable } from '@nestjs/common';
let MinimizationService = class MinimizationService {
    apply(value, opts) {
        let v = value;
        if (opts.stripIdentifiers) {
            v = this.removeIdentifiers(v);
        }
        if (typeof v === 'object' && v !== null && typeof opts.numericBucket === 'number') {
            v = this.bucketNumbersDeep(v, opts.numericBucket);
        }
        if (typeof opts.truncatePayloadBytes === 'number') {
            v = this.truncateJson(v, opts.truncatePayloadBytes);
        }
        return v;
    }
    roundTimestamp(ts, roundMs) {
        return Math.round(ts / roundMs) * roundMs;
    }
    removeIdentifiers(data) {
        if (data === null || typeof data !== 'object')
            return data;
        const blockedKeys = new Set(['id', 'deviceId', 'serial', 'mac', 'uuid', 'imei']);
        if (Array.isArray(data))
            return data.map((d) => this.removeIdentifiers(d));
        const out = {};
        for (const [k, val] of Object.entries(data)) {
            if (blockedKeys.has(k.toLowerCase()))
                continue;
            out[k] = this.removeIdentifiers(val);
        }
        return out;
    }
    bucketNumbersDeep(data, step) {
        if (typeof data === 'number') {
            return Math.round(data / step) * step;
        }
        if (Array.isArray(data))
            return data.map((d) => this.bucketNumbersDeep(d, step));
        if (data && typeof data === 'object') {
            const out = {};
            for (const [k, v] of Object.entries(data)) {
                out[k] = this.bucketNumbersDeep(v, step);
            }
            return out;
        }
        return data;
    }
    truncateJson(data, maxBytes) {
        try {
            const str = JSON.stringify(data);
            if (Buffer.byteLength(str, 'utf8') <= maxBytes)
                return data;
            const truncated = str.slice(0, maxBytes);
            return JSON.parse(truncated + ']"'.slice(0, 0));
        }
        catch {
            return typeof data === 'string' ? data.slice(0, Math.max(0, maxBytes)) : '[truncated]';
        }
    }
};
MinimizationService = __decorate([
    Injectable()
], MinimizationService);
export { MinimizationService };
//# sourceMappingURL=minimization.service.js.map