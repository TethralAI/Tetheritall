import { Column, CreateDateColumn, Entity, Index, PrimaryColumn } from 'typeorm';

@Entity({ name: 'device_shadow' })
export class DeviceShadowEntity {
  @PrimaryColumn({ type: 'varchar', length: 128 })
  deviceId!: string;

  @Column({ type: 'int4', default: 0 })
  @Index()
  version!: number;

  @Column({ type: 'jsonb', default: () => "'{}'::jsonb" })
  reported!: Record<string, unknown>;

  @CreateDateColumn({ type: 'timestamptz' })
  updatedAt!: Date;
}

