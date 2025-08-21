import { Column, CreateDateColumn, Entity, Index, PrimaryGeneratedColumn } from 'typeorm';

@Entity({ name: 'event' })
export class EventEntity {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ type: 'varchar', length: 128 })
  deviceId!: string;

  @Column({ type: 'varchar', length: 128 })
  capability!: string;

  @Column({ type: 'varchar', length: 32 })
  dataClass!: 'telemetry' | 'state' | 'diagnostic' | 'identifier' | 'location';

  @Column({ type: 'varchar', length: 32 })
  purpose!: 'automation' | 'troubleshooting' | 'analytics';

  @Column({ type: 'jsonb' })
  value!: unknown;

  @Column({ type: 'int8' })
  @Index()
  seq!: number;

  @Column({ type: 'varchar', length: 32 })
  policyVersion!: string;

  @CreateDateColumn({ type: 'timestamptz' })
  ts!: Date;
}

