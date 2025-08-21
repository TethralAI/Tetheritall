var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
import { Injectable } from '@nestjs/common';
import jwt from 'jsonwebtoken';
let WsJwtGuard = class WsJwtGuard {
    tokensPerIp = new Map();
    limit = Number(process.env.WS_RATE_LIMIT || 20);
    windowMs = Number(process.env.WS_RATE_WINDOW_MS || 10000);
    canActivate(context) {
        const client = context.switchToWs().getClient();
        const token = client.handshake?.auth?.token || client.handshake?.headers?.authorization?.replace('Bearer ', '');
        const secret = process.env.JWT_SECRET || 'dev-secret';
        try {
            if (!token)
                return false;
            const decoded = jwt.verify(token, secret);
            const user = decoded;
            client.user = user;
            const ip = client.handshake?.address || 'unknown';
            const now = Date.now();
            const entry = this.tokensPerIp.get(ip) ?? { count: 0, windowStart: now };
            if (now - entry.windowStart > this.windowMs) {
                entry.count = 0;
                entry.windowStart = now;
            }
            entry.count++;
            this.tokensPerIp.set(ip, entry);
            if (entry.count > this.limit)
                return false;
            const scopes = Array.isArray(user?.scp) ? user.scp : typeof user?.scp === 'string' ? user.scp.split(' ') : [];
            if (!scopes.includes('conn.read'))
                return false;
            return true;
        }
        catch {
            return false;
        }
    }
};
WsJwtGuard = __decorate([
    Injectable()
], WsJwtGuard);
export { WsJwtGuard };
//# sourceMappingURL=ws.auth.js.map