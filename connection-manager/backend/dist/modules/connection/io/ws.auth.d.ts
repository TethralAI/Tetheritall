import { CanActivate, ExecutionContext } from '@nestjs/common';
export declare class WsJwtGuard implements CanActivate {
    canActivate(context: ExecutionContext): boolean;
}
