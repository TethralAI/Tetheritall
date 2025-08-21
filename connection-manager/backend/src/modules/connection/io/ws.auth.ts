import { CanActivate, ExecutionContext, Injectable } from '@nestjs/common';
import jwt from 'jsonwebtoken';

@Injectable()
export class WsJwtGuard implements CanActivate {
  canActivate(context: ExecutionContext): boolean {
    const client: any = context.switchToWs().getClient();
    const token = client.handshake?.auth?.token || client.handshake?.headers?.authorization?.replace('Bearer ', '');
    const secret = process.env.JWT_SECRET || 'dev-secret';
    try {
      if (!token) return false;
      const decoded = jwt.verify(token, secret);
      (client as any).user = decoded;
      return true;
    } catch {
      return false;
    }
  }
}

