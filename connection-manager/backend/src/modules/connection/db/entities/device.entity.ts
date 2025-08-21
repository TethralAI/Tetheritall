import { Column, CreateDateColumn, Entity, Index, PrimaryColumn } from 'typeorm';

@Entity({ name: 'device' })
export class DeviceEntity {
  @PrimaryColumn({ type: 'varchar', length: 128 })
  id!: string;

  @Column({ type: 'jsonb', default: () => "'[]'::jsonb" })
  capabilities!: string[];

  @Column({ type: 'varchar', length: 16, default: 'offline' })
  @Index()
  status!: 'online' | 'offline';

  @CreateDateColumn({ type: 'timestamptz' })
  createdAt!: Date;
}

