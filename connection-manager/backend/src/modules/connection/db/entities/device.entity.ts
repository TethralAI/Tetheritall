import { Column, CreateDateColumn, Entity, Index, PrimaryColumn } from 'typeorm';

@Entity({ name: 'device' })
export class DeviceEntity {
  @PrimaryColumn({ type: 'string' as any })
  id!: string;

  @Column({ type: 'jsonb', default: () => "'[]'::jsonb" })
  capabilities!: string[];

  @Column({ type: 'string' as any, default: 'offline' })
  @Index()
  status!: 'online' | 'offline';

  @CreateDateColumn({ type: 'timestamptz' })
  createdAt!: Date;
}

