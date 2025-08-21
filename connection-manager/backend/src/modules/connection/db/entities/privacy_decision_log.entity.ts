import { Column, CreateDateColumn, Entity, PrimaryGeneratedColumn } from 'typeorm';

@Entity({ name: 'privacy_decision_log' })
export class PrivacyDecisionLogEntity {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ type: 'varchar', length: 128 })
  deviceId!: string;

  @Column({ type: 'boolean' })
  allowed!: boolean;

  @Column({ type: 'varchar', length: 32 })
  policyVersion!: string;

  @Column({ type: 'varchar', length: 128, nullable: true })
  reason!: string | null;

  @CreateDateColumn({ type: 'timestamptz' })
  ts!: Date;
}

