import { Column, CreateDateColumn, Entity, Index, PrimaryGeneratedColumn, UpdateDateColumn } from 'typeorm';

@Entity({ name: 'security_quarantine' })
export class SecurityQuarantineEntity {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ type: 'varchar', length: 128 })
  @Index()
  deviceId!: string;

  @Column({ type: 'varchar', length: 16 })
  mode!: 'read_only' | 'block';

  @Column({ type: 'int4', nullable: true })
  ttlSec!: number | null;

  @CreateDateColumn({ type: 'timestamptz' })
  appliedAt!: Date;

  @UpdateDateColumn({ type: 'timestamptz' })
  updatedAt!: Date;
}

