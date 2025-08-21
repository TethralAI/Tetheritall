import { Column, CreateDateColumn, Entity, Index, PrimaryGeneratedColumn, UpdateDateColumn } from 'typeorm';

@Entity({ name: 'command_log' })
export class CommandLogEntity {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ type: 'varchar', length: 128 })
  deviceId!: string;

  @Column({ type: 'varchar', length: 128 })
  capability!: string;

  @Column({ type: 'jsonb' })
  params!: unknown;

  @Column({ type: 'varchar', length: 16 })
  priority!: 'emergency' | 'routine' | 'background';

  @Column({ type: 'bigint', nullable: true })
  deadline!: number | null;

  @Column({ type: 'varchar', length: 128 })
  @Index()
  idempotencyKey!: string;

  @Column({ type: 'varchar', length: 16 })
  @Index()
  status!: 'accepted' | 'delivering' | 'applied' | 'failed' | 'expired';

  @Column({ type: 'text', nullable: true })
  error!: string | null;

  @CreateDateColumn({ type: 'timestamptz' })
  createdAt!: Date;

  @UpdateDateColumn({ type: 'timestamptz' })
  updatedAt!: Date;
}

