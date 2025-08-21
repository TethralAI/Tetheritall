import { CanActivate, ExecutionContext } from '@nestjs/common';
export declare class WsJwtGuard implements CanActivate {
    private tokensPerIp;
    private readonly limit;
    private readonly windowMs;
    canActivate(context: ExecutionContext): boolean;
}
