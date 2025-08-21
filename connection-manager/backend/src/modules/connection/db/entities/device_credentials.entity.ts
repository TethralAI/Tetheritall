import { Column, CreateDateColumn, Entity, Index, PrimaryGeneratedColumn, UpdateDateColumn } from 'typeorm';

@Entity({ name: 'device_credentials' })
export class DeviceCredentialsEntity {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ type: 'varchar', length: 128 })
  @Index()
  deviceId!: string;

  // Encrypted payload (envelope encrypted via KMS at app layer)
  @Column({ type: 'bytea' })
  encBlob!: Buffer;

  @Column({ type: 'varchar', length: 64 })
  encAlg!: string; // e.g., 'aes-256-gcm'

  @Column({ type: 'varchar', length: 256 })
  keyRef!: string; // KMS key id / ref

  @CreateDateColumn({ type: 'timestamptz' })
  createdAt!: Date;

  @UpdateDateColumn({ type: 'timestamptz' })
  updatedAt!: Date;
}

