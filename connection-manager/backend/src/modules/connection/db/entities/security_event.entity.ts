import { Column, CreateDateColumn, Entity, Index, PrimaryGeneratedColumn } from 'typeorm';

@Entity({ name: 'security_event' })
export class SecurityEventEntity {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ type: 'varchar', length: 128 })
  deviceId!: string;

  @Column({ type: 'varchar', length: 64 })
  type!: string; // breakdown, intrusion_suspected, etc.

  @Column({ type: 'jsonb', nullable: true })
  detail!: unknown;

  @CreateDateColumn({ type: 'timestamptz' })
  ts!: Date;
}

