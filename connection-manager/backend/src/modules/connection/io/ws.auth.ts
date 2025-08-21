import { CanActivate, ExecutionContext, Injectable } from '@nestjs/common';
import jwt from 'jsonwebtoken';

@Injectable()
export class WsJwtGuard implements CanActivate {
  private tokensPerIp: Map<string, { count: number; windowStart: number }> = new Map();
  private readonly limit = Number(process.env.WS_RATE_LIMIT || 20);
  private readonly windowMs = Number(process.env.WS_RATE_WINDOW_MS || 10000);
  canActivate(context: ExecutionContext): boolean {
    const client: any = context.switchToWs().getClient();
    const token = client.handshake?.auth?.token || client.handshake?.headers?.authorization?.replace('Bearer ', '');
    const secret = process.env.JWT_SECRET || 'dev-secret';
    try {
      if (!token) return false;
      const decoded = jwt.verify(token, secret);
      const user = decoded as any;
      (client as any).user = user;
      // Rate limit per IP
      const ip = client.handshake?.address || 'unknown';
      const now = Date.now();
      const entry = this.tokensPerIp.get(ip) ?? { count: 0, windowStart: now };
      if (now - entry.windowStart > this.windowMs) {
        entry.count = 0;
        entry.windowStart = now;
      }
      entry.count++;
      this.tokensPerIp.set(ip, entry);
      if (entry.count > this.limit) return false;
      // Optional scope check
      const scopes: string[] = Array.isArray(user?.scp) ? user.scp : typeof user?.scp === 'string' ? user.scp.split(' ') : [];
      if (!scopes.includes('conn.read')) return false;
      return true;
    } catch {
      return false;
    }
  }
}

