import { Injectable } from '@nestjs/common';

@Injectable()
export class LocalOnlyModeService {
  private enabled = false;

  enable(): void {
    this.enabled = true;
  }
  disable(): void {
    this.enabled = false;
  }
  isEnabled(): boolean {
    return this.enabled;
  }
}

