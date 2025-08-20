import { Body, Controller, Get, Param, Post } from '@nestjs/common';
import { v4 as uuidv4 } from 'uuid';

type CommissionStartDto = { ssid?: string; psk?: string; metadata?: Record<string, unknown> };

@Controller('/v1/connection/commission')
export class CommissioningController {
  private sessions = new Map<string, { id: string; status: 'pending' | 'success' | 'failed'; createdAt: number }>();

  @Post('/start')
  start(@Body() _body: CommissionStartDto) {
    const id = uuidv4();
    this.sessions.set(id, { id, status: 'pending', createdAt: Date.now() });
    return { id };
  }

  @Get('/:id/status')
  status(@Param('id') id: string) {
    const s = this.sessions.get(id);
    if (!s) return { id, status: 'failed' };
    // Simulate success quickly
    if (Date.now() - s.createdAt > 100) s.status = 'success';
    return { id, status: s.status };
  }
}

