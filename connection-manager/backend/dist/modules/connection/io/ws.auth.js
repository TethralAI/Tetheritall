var __decorate = (this && this.__decorate) || function (decorators, target, key, desc) {
    var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
    if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
    else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
    return c > 3 && r && Object.defineProperty(target, key, r), r;
};
import { Injectable } from '@nestjs/common';
import jwt from 'jsonwebtoken';
let WsJwtGuard = class WsJwtGuard {
    canActivate(context) {
        const client = context.switchToWs().getClient();
        const token = client.handshake?.auth?.token || client.handshake?.headers?.authorization?.replace('Bearer ', '');
        const secret = process.env.JWT_SECRET || 'dev-secret';
        try {
            if (!token)
                return false;
            const decoded = jwt.verify(token, secret);
            client.user = decoded;
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